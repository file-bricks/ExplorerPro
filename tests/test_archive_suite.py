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
import zipfile
import pytest

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
    ArchiveViewerDialog,
)
from gui.preview.preview_panel import ArchivePreview, PreviewPanel


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
