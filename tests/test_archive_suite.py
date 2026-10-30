#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_archive_suite.py - Umfassende Vertragstests für die ZIP- & Archiv-Suite (TW-EP-12)
========================================================================================
Testet:
- ArchiveService: Komprimierung, Extraktion, Zip-Slip-Schutz, Inspektion, Integrität
- Archive-Dialoge: Compress-, Extract- und Viewer-Dialoge
- PreviewPanel: ArchivePreview (.zip) Integration
- FileBrowser & MainWindow Menü-Wiring
"""

from pathlib import Path
import os
import subprocess
import sys
import threading
import zipfile
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from core import archive_service
from core.archive_service import (
    ArchiveSummary,
    ZipSlipSecurityError,
    check_zip_integrity,
    create_zip_archive,
    extract_zip_archive,
    format_bytes,
    inspect_zip,
    sanitize_archive_member_path,
)
from gui.archive_dialog import (
    ArchiveCompressDialog,
    ArchiveExtractDialog,
    ArchiveExtractProgressDialog,
    ArchiveIntegrityProgressDialog,
    ArchiveViewerDialog,
)
from gui.preview.preview_panel import ArchivePreview, PreviewPanel


@pytest.fixture
def archive_app(qapp):
    """Prevent this module's transient task windows from quitting pytest's app."""
    quit_on_last_window_closed = qapp.quitOnLastWindowClosed()
    qapp.setQuitOnLastWindowClosed(False)
    yield qapp
    qapp.setQuitOnLastWindowClosed(quit_on_last_window_closed)


# ============================================================================
# 1. CORE SERVICE TESTS
# ============================================================================

def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert "KB" in format_bytes(1024 * 10)
    assert "MB" in format_bytes(1024 * 1024 * 5)
    assert "GB" in format_bytes(1024 * 1024 * 1024 * 2)


def test_create_and_inspect_zip(tmp_path: Path):
    # Dateien vorbereiten
    src_dir = tmp_path / "sample_folder"
    src_dir.mkdir()
    f1 = src_dir / "text1.txt"
    f1.write_text("Hello World! This is a test string for zip compression." * 10, encoding="utf-8")
    sub_dir = src_dir / "nested"
    sub_dir.mkdir()
    f2 = sub_dir / "nested_doc.md"
    f2.write_text("# Markdown Title\nSome nested content here.", encoding="utf-8")

    out_zip = tmp_path / "output.zip"

    # Komprimieren
    count, total_bytes = create_zip_archive([src_dir], out_zip, compression=zipfile.ZIP_DEFLATED)
    assert out_zip.exists()
    assert count >= 2
    assert total_bytes > 0

    # Prüfen / Inspizieren
    summary, entries = inspect_zip(out_zip)
    assert isinstance(summary, ArchiveSummary)
    assert summary.total_files >= 2
    assert summary.uncompressed_size > 0
    assert summary.compressed_size > 0
    assert summary.overall_ratio >= 0.0

    entry_names = [e.filename.replace("\\", "/") for e in entries]
    assert any("text1.txt" in name for name in entry_names)
    assert any("nested_doc.md" in name for name in entry_names)

    # Entry-Formatierung
    sample_entry = entries[0]
    assert isinstance(sample_entry.formatted_size, str)
    assert isinstance(sample_entry.formatted_date, str)


def test_create_zip_replace_failure_preserves_destination_and_cleans_temp(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replacement_source.txt"
    source.write_bytes(b"new archive content")
    destination = tmp_path / "existing.zip"
    original_bytes = b"pre-existing archive must survive"
    destination.write_bytes(original_bytes)
    replace_attempts = []

    def fail_replace(source_path, destination_path):
        replace_attempts.append((Path(source_path), Path(destination_path)))
        raise OSError("simulated atomic replacement failure")

    monkeypatch.setattr(archive_service.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated atomic replacement failure"):
        create_zip_archive([source], destination)

    assert destination.read_bytes() == original_bytes
    assert len(replace_attempts) == 1
    temporary_path, replaced_destination = replace_attempts[0]
    assert replaced_destination == destination.resolve()
    assert temporary_path.parent == destination.parent
    assert not temporary_path.exists()


def test_test_zip_integrity_valid_and_corrupt(tmp_path: Path):
    zip_path = tmp_path / "integrity.zip"
    f = tmp_path / "valid.txt"
    f.write_text("Integrity Check Data", encoding="utf-8")

    create_zip_archive([f], zip_path)

    # Gültiges Archiv
    is_valid, msg = check_zip_integrity(zip_path)
    assert is_valid is True
    assert msg is None

    # Korruptes Archiv erzeugen (Bytes überschreiben)
    corrupt_zip = tmp_path / "corrupt.zip"
    corrupt_data = bytearray(zip_path.read_bytes())
    # Beschädige Daten in der Mitte
    mid = len(corrupt_data) // 2
    corrupt_data[mid : mid + 10] = b"\x00\xFF\x00\xFF\x00\xFF\x00\xFF\x00\xFF"
    corrupt_zip.write_bytes(bytes(corrupt_data))

    is_valid_bad, msg_bad = check_zip_integrity(corrupt_zip)
    assert is_valid_bad is False
    assert msg_bad is not None


def test_extract_zip_archive_and_mtime(tmp_path: Path):
    # Erstelle Archiv
    f1 = tmp_path / "source.txt"
    f1.write_text("Data to extract", encoding="utf-8")
    zip_path = tmp_path / "archive_to_extract.zip"
    create_zip_archive([f1], zip_path)

    # Extrahiere
    dest_dir = tmp_path / "extracted"
    extracted_count, extracted_bytes = extract_zip_archive(zip_path, dest_dir)

    assert extracted_count == 1
    assert extracted_bytes > 0
    extracted_file = dest_dir / "source.txt"
    assert extracted_file.exists()
    assert extracted_file.read_text(encoding="utf-8") == "Data to extract"


def test_extract_selected_members(tmp_path: Path):
    f1 = tmp_path / "keep.txt"
    f1.write_text("Keep this", encoding="utf-8")
    f2 = tmp_path / "skip.txt"
    f2.write_text("Skip this", encoding="utf-8")

    zip_path = tmp_path / "selective.zip"
    create_zip_archive([f1, f2], zip_path)

    dest_dir = tmp_path / "selective_extracted"
    extracted_count, _ = extract_zip_archive(zip_path, dest_dir, members=["keep.txt"])

    assert extracted_count == 1
    assert (dest_dir / "keep.txt").exists()
    assert not (dest_dir / "skip.txt").exists()


def test_zip_slip_defense_sanitizer(tmp_path: Path):
    target = tmp_path / "safe_dir"
    target.mkdir()

    # Normaler relativer Pfad ist sicher
    safe_path = sanitize_archive_member_path("folder/sub/doc.txt", target)
    assert safe_path.resolve().is_relative_to(target.resolve())

    # Traversal mit '..' muss abgewehrt werden
    with pytest.raises(ZipSlipSecurityError):
        sanitize_archive_member_path("../../evil.txt", target)

    with pytest.raises(ZipSlipSecurityError):
        sanitize_archive_member_path("sub/../../outside.txt", target)


def test_zip_slip_defense_during_extraction(tmp_path: Path):
    """Prüft, dass manipulierte ZIP-Dateien mit Traversal-Pfaden sicher blockiert werden."""
    malicious_zip = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../../evil_payload.txt", "MALICIOUS CONTENT")

    extract_target = tmp_path / "jail"
    extract_target.mkdir()

    with pytest.raises(ZipSlipSecurityError):
        extract_zip_archive(malicious_zip, extract_target)

    # Sicherstellen, dass die schädliche Datei nicht außerhalb geschrieben wurde
    assert not (tmp_path / "evil_payload.txt").exists()


def test_cancellation_of_compression_and_extraction(tmp_path: Path):
    f1 = tmp_path / "large.txt"
    f1.write_text("Test data" * 1000, encoding="utf-8")
    out_zip = tmp_path / "cancelled.zip"

    # Abbruch sofort
    count, total_bytes = create_zip_archive(
        [f1],
        out_zip,
        is_cancelled=lambda: True
    )
    assert count == 0
    assert not out_zip.exists()


# ============================================================================
# 2. GUI DIALOG TESTS
# ============================================================================

def test_archive_compress_dialog_initialization(qapp, tmp_path: Path):
    f1 = tmp_path / "item1.txt"
    f1.write_text("item1", encoding="utf-8")
    f2 = tmp_path / "item2.txt"
    f2.write_text("item2", encoding="utf-8")

    dlg = ArchiveCompressDialog([str(f1), str(f2)], current_dir=str(tmp_path))
    assert dlg.windowTitle() != ""
    assert dlg.accessibleName() != ""
    assert dlg.accessibleDescription() != ""
    assert dlg.dest_edit.text().endswith(".zip")
    assert dlg.method_combo.count() >= 4
    dlg.close()


def test_archive_extract_dialog_initialization(qapp, tmp_path: Path):
    f1 = tmp_path / "doc.txt"
    f1.write_text("doc", encoding="utf-8")
    zip_path = tmp_path / "test_extract.zip"
    create_zip_archive([f1], zip_path)

    dlg = ArchiveExtractDialog(str(zip_path), default_target_dir=str(tmp_path))
    assert dlg.windowTitle() != ""
    assert dlg.accessibleName() != ""
    assert dlg.accessibleDescription() != ""
    assert dlg.subfolder_cb.isChecked() is True
    assert dlg.overwrite_cb.isChecked() is True
    dlg.close()


def test_archive_viewer_dialog_filtering_and_table(qapp, tmp_path: Path):
    f1 = tmp_path / "alpha.txt"
    f1.write_text("Alpha file content", encoding="utf-8")
    f2 = tmp_path / "beta.md"
    f2.write_text("Beta markdown content", encoding="utf-8")
    zip_path = tmp_path / "viewer_test.zip"
    create_zip_archive([f1, f2], zip_path)

    dlg = ArchiveViewerDialog(str(zip_path))
    assert dlg.windowTitle() != ""
    assert dlg.table.rowCount() == 2

    # Filterung testen
    dlg.filter_edit.setText("alpha")
    assert dlg.table.rowCount() == 1
    item = dlg.table.item(0, 0)
    assert "alpha.txt" in item.text()

    dlg.filter_edit.setText("non_existent_file")
    assert dlg.table.rowCount() == 0

    dlg.filter_edit.clear()
    assert dlg.table.rowCount() == 2
    dlg.close()


def _assert_archive_progress_dialog_defers_close_until_worker_stops(
    qtbot, monkeypatch, tmp_path: Path, action, expected_result
):
    from core.archive_service import ArchiveExtractWorker

    entered = threading.Event()
    release = threading.Event()

    def blocked_run(worker):
        entered.set()
        release.wait(5)

    monkeypatch.setattr(ArchiveExtractWorker, "run", blocked_run)
    archive_path = tmp_path / "blocked.zip"
    archive_path.write_bytes(b"worker is patched in this lifecycle test")
    dialog = ArchiveExtractProgressDialog(str(archive_path), str(tmp_path / "out"))
    qtbot.addWidget(dialog)
    completed = []
    dialog.finished.connect(completed.append)
    dialog.show()

    try:
        assert entered.wait(2)
        getattr(dialog, action)()
        qtbot.wait(40)
        assert dialog.isVisible()
        assert dialog.worker.isRunning()
        assert dialog.worker._is_cancelled is True
        assert completed == []

        release.set()
        assert dialog.worker.wait(2000)
        qtbot.waitUntil(lambda: completed == [int(expected_result)], timeout=3000)
        assert not dialog.isVisible()
        assert not dialog.worker.isRunning()
    finally:
        release.set()
        dialog.worker.wait(2000)
        dialog.close()


@pytest.mark.parametrize(
    "action,expected_result",
    [
        ("accept", 1),
        ("reject", 0),
        ("close", 0),
    ],
)
def test_archive_progress_dialog_close_actions(
    action, expected_result, archive_app, qtbot, monkeypatch, tmp_path
):
    _assert_archive_progress_dialog_defers_close_until_worker_stops(
        qtbot,
        monkeypatch,
        tmp_path,
        action,
        expected_result,
    )


def test_direct_archive_extraction_is_async_and_reports_failure(
    archive_app, qtbot, monkeypatch, tmp_path: Path
):
    from gui.browser.file_browser import FileBrowser

    entered = threading.Event()
    release = threading.Event()
    errors = []
    successes = []

    def blocked_failure(*args, **kwargs):
        entered.set()
        release.wait(5)
        raise OSError("simulated extraction failure")

    monkeypatch.setattr(archive_service, "extract_zip_archive", blocked_failure)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: successes.append(args[-1]))
    browser = FileBrowser()
    qtbot.addWidget(browser)
    browser._current_path = str(tmp_path)
    browser.refresh = lambda: None
    archive_path = tmp_path / "broken.zip"
    archive_path.write_bytes(b"the worker uses the patched service")

    try:
        browser._extract_archive_here(str(archive_path))
        assert entered.wait(2)
        dialog = browser._archive_task_dialogs[0]
        assert dialog.worker.isRunning()
        assert errors == []
        assert successes == []

        release.set()
        qtbot.waitUntil(
            lambda: bool(errors) and not dialog.worker.isRunning(), timeout=3000
        )
        assert "simulated extraction failure" in errors[0]
        assert successes == []
    finally:
        release.set()
        for dialog in list(browser._archive_task_dialogs):
            if hasattr(dialog, "worker") and dialog.worker.isRunning():
                dialog.worker.wait(2000)
            dialog.close()
        browser.close()


def test_direct_archive_extraction_reports_success_after_worker_stops(
    archive_app, qtbot, monkeypatch, tmp_path: Path
):
    from gui.browser.file_browser import FileBrowser

    entered = threading.Event()
    release = threading.Event()
    errors = []
    successes = []

    def blocked_success(*args, **kwargs):
        entered.set()
        release.wait(5)
        return 1, 128

    monkeypatch.setattr(archive_service, "extract_zip_archive", blocked_success)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: successes.append(args[-1]))
    browser = FileBrowser()
    qtbot.addWidget(browser)
    browser._current_path = str(tmp_path)
    browser.refresh = lambda: None
    archive_path = tmp_path / "good.zip"
    archive_path.write_bytes(b"the worker uses the patched service")

    try:
        browser._extract_archive_here(str(archive_path))
        assert entered.wait(2)
        dialog = browser._archive_task_dialogs[0]
        assert dialog.worker.isRunning()
        assert errors == []
        assert successes == []

        release.set()
        qtbot.waitUntil(
            lambda: bool(successes) and not dialog.worker.isRunning(), timeout=3000
        )
        assert "good" in successes[0]
        assert errors == []
    finally:
        release.set()
        for dialog in list(browser._archive_task_dialogs):
            if hasattr(dialog, "worker") and dialog.worker.isRunning():
                dialog.worker.wait(2000)
            dialog.close()
        browser.close()


def test_viewer_selected_extraction_is_async_and_reports_failure(
    archive_app, qtbot, monkeypatch, tmp_path: Path
):
    entered = threading.Event()
    release = threading.Event()
    errors = []
    successes = []

    def blocked_failure(*args, **kwargs):
        entered.set()
        release.wait(5)
        raise OSError("selected extraction failed")

    monkeypatch.setattr(archive_service, "extract_zip_archive", blocked_failure)
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: str(tmp_path / "selected"),
    )
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: successes.append(args[-1]))

    source = tmp_path / "member.txt"
    source.write_text("archive member", encoding="utf-8")
    archive_path = tmp_path / "selected.zip"
    create_zip_archive([source], archive_path)
    dialog = ArchiveViewerDialog(str(archive_path))
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)

    try:
        dialog._extract_selected()
        assert entered.wait(2)
        assert dialog.extract_worker.isRunning()
        assert errors == []
        assert successes == []

        release.set()
        qtbot.waitUntil(
            lambda: bool(errors) and not dialog.extract_worker.isRunning(), timeout=3000
        )
        assert "selected extraction failed" in errors[0]
        assert successes == []
    finally:
        release.set()
        if dialog.extract_worker is not None:
            dialog.extract_worker.wait(2000)
        dialog.close()


def test_file_browser_crc_check_is_async_and_reports_corruption(
    archive_app, qtbot, monkeypatch, tmp_path: Path
):
    from gui.browser.file_browser import FileBrowser

    entered = threading.Event()
    release = threading.Event()
    warnings = []
    successes = []

    def blocked_corruption(_zip_path):
        entered.set()
        release.wait(5)
        return False, "simulated CRC mismatch"

    monkeypatch.setattr(archive_service, "check_zip_integrity", blocked_corruption)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: successes.append(args[-1]))
    browser = FileBrowser()
    qtbot.addWidget(browser)
    archive_path = tmp_path / "crc.zip"
    archive_path.write_bytes(b"worker uses patched CRC service")

    try:
        browser._test_archive_integrity(str(archive_path))
        assert entered.wait(2)
        dialog = browser._archive_task_dialogs[0]
        assert isinstance(dialog, ArchiveIntegrityProgressDialog)
        assert dialog.test_worker.isRunning()
        assert warnings == []
        assert successes == []

        release.set()
        qtbot.waitUntil(
            lambda: bool(warnings) and not dialog.test_worker.isRunning(), timeout=3000
        )
        assert "simulated CRC mismatch" in warnings[0]
        assert successes == []
    finally:
        release.set()
        for dialog in list(browser._archive_task_dialogs):
            if hasattr(dialog, "test_worker") and dialog.test_worker.isRunning():
                dialog.test_worker.wait(2000)
            dialog.close()
        browser.close()


def test_file_browser_crc_check_reports_success(archive_app, qtbot, monkeypatch, tmp_path: Path):
    from gui.browser.file_browser import FileBrowser

    successes = []
    warnings = []
    monkeypatch.setattr(archive_service, "check_zip_integrity", lambda _path: (True, ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: successes.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    browser = FileBrowser()
    qtbot.addWidget(browser)
    archive_path = tmp_path / "valid.zip"
    archive_path.write_bytes(b"worker uses patched CRC service")

    browser._test_archive_integrity(str(archive_path))
    dialog = browser._archive_task_dialogs[0]
    qtbot.waitUntil(lambda: bool(successes) and not dialog.test_worker.isRunning(), timeout=3000)
    assert "valid.zip" in successes[0]
    assert warnings == []
    dialog.close()
    browser.close()


def test_archive_worker_application_quit_waits_for_thread_exit(tmp_path: Path):
    script = r'''
import sys, threading
sys.path.insert(0, "src")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from core import archive_service
from gui.archive_dialog import ArchiveExtractProgressDialog

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
entered, release = threading.Event(), threading.Event()
def blocked_extract(*args, **kwargs):
    entered.set()
    release.wait(5)
    return 0, 0
archive_service.extract_zip_archive = blocked_extract
archive_service.extract_archive = blocked_extract
dialog = ArchiveExtractProgressDialog("unused.zip", "unused-target")
dialog.show()
assert entered.wait(2)
QTimer.singleShot(0, app.quit)
QTimer.singleShot(100, release.set)
QTimer.singleShot(7000, app.exit)
app.exec()
assert not dialog.worker.isRunning()
assert release.is_set()
print("archive-quit-wait-ok")
dialog.close()
'''
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=12,
        env=environment,
    )
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "archive-quit-wait-ok" in result.stdout
    assert "QThread: Destroyed while thread is still running" not in result.stderr


# ============================================================================
# 3. PREVIEW PANEL INTEGRATION TESTS
# ============================================================================

def test_archive_preview_widget_loading(qapp, tmp_path: Path):
    f1 = tmp_path / "preview_file.py"
    f1.write_text("print('archive preview test')", encoding="utf-8")
    zip_path = tmp_path / "preview_test.zip"
    create_zip_archive([f1], zip_path)

    preview_widget = ArchivePreview()
    preview_widget.load_archive(str(zip_path))

    assert preview_widget.name_label.text() == "preview_test.zip"
    assert "1 Dateien" in preview_widget.count_label.text()
    assert preview_widget.table.rowCount() == 1
    assert "preview_file.py" in preview_widget.table.item(0, 0).text()


def test_preview_panel_routes_zip_to_archive_preview(qapp, tmp_path: Path):
    f1 = tmp_path / "sample.txt"
    f1.write_text("sample content", encoding="utf-8")
    zip_path = tmp_path / "panel_test.zip"
    create_zip_archive([f1], zip_path)

    panel = PreviewPanel()
    panel.show_preview(str(zip_path))

    # Stack-Index 7 ist die ArchivePreview
    assert panel.preview_stack.currentIndex() == 7
    assert panel.archive_preview._path == str(zip_path)


# ============================================================================
# 4. MAIN WINDOW & FILE BROWSER WIRING TESTS
# ============================================================================

def test_main_window_archive_actions_wiring(qapp, monkeypatch):
    from gui.main_window import MainWindow
    win = MainWindow()
    calls = []

    monkeypatch.setattr(win.file_browser, "_compress_selection", lambda: calls.append("compress") or True)
    monkeypatch.setattr(win.file_browser, "_extract_zip_dialog", lambda: calls.append("extract") or True)

    win._compress_archive()
    win._extract_archive()
    win.close()

    assert "compress" in calls
    assert "extract" in calls


def test_file_browser_archive_methods_exist(qapp):
    from gui.browser.file_browser import FileBrowser
    browser = FileBrowser()
    assert hasattr(browser, "_compress_selection")
    assert hasattr(browser, "_compress_current_folder")
    assert hasattr(browser, "_extract_archive")
    assert hasattr(browser, "_extract_archive_here")
    assert hasattr(browser, "_view_archive")
    assert hasattr(browser, "_test_archive_integrity")
    assert hasattr(browser, "_extract_zip_dialog")
    browser.close()
