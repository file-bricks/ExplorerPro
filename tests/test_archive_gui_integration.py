#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_archive_gui_integration.py - Integrationstests für Archiv-GUI-Komponenten
=============================================================================
Prüft:
- ArchivePreview mit ZIP und TAR/TAR.GZ
- ArchiveExtractDialog & ArchiveViewerDialog Initialisierung und Metadatenanzeige
- _get_archive_stem Multi-Suffix-Erkennung (.tar.gz, .tgz, .tar.bz2, etc.)
- Archive-Filterung und Integritätsprüfung im ArchiveViewerDialog
"""

import os
import tarfile
import tempfile
import zipfile
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from core.archive_service import is_archive, inspect_archive
from gui.archive_dialog import ArchiveCompressDialog, ArchiveExtractDialog, ArchiveViewerDialog, _get_archive_stem
from gui.preview.preview_panel import ArchivePreview


@pytest.fixture(scope="module")
def sample_archives():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Sample ZIP
        zip_path = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("docs/readme.txt", "Hello ZIP archive!")
            zf.writestr("data/table.csv", "id,val\n1,100\n2,200\n")

        # 2. Sample TAR.GZ
        tar_gz_path = tmp_path / "package.tar.gz"
        with tarfile.open(tar_gz_path, "w:gz") as tf:
            d = tmp_path / "payload"
            d.mkdir(parents=True, exist_ok=True)
            f1 = d / "info.json"
            f1.write_text('{"version": "1.0"}', encoding="utf-8")
            f2 = d / "run.sh"
            f2.write_text('#!/bin/sh\necho "Running"', encoding="utf-8")
            tf.add(str(f1), arcname="info.json")
            tf.add(str(f2), arcname="scripts/run.sh")

        # 3. Sample Plain TAR
        plain_tar_path = tmp_path / "archive.tar"
        with tarfile.open(plain_tar_path, "w") as tf:
            f3 = d / "data.bin"
            f3.write_bytes(b"Binary Payload 1234567890")
            tf.add(str(f3), arcname="data.bin")

        yield {
            "tmpdir": tmp_path,
            "zip": zip_path,
            "tar_gz": tar_gz_path,
            "tar": plain_tar_path
        }


def test_get_archive_stem():
    assert _get_archive_stem("my_backup.zip") == "my_backup"
    assert _get_archive_stem("archive.tar.gz") == "archive"
    assert _get_archive_stem("/path/to/archive.tar.bz2") == "archive"
    assert _get_archive_stem("data.tar.xz") == "data"
    assert _get_archive_stem("tool.tgz") == "tool"
    assert _get_archive_stem("tool.tbz2") == "tool"
    assert _get_archive_stem("tool.txz") == "tool"
    assert _get_archive_stem("simple.tar") == "simple"
    assert _get_archive_stem("document.pdf") == "document"


def test_archive_preview_with_zip(sample_archives, qtbot):
    preview = ArchivePreview()
    qtbot.addWidget(preview)
    preview.load_archive(str(sample_archives["zip"]))

    assert "bundle.zip" in preview.name_label.text()
    assert preview.table.rowCount() == 2
    assert preview.explore_btn.isEnabled()
    assert preview.extract_btn.isEnabled()
    assert not preview.status_label.isVisible()


def test_archive_preview_with_tar_gz(sample_archives, qtbot):
    preview = ArchivePreview()
    qtbot.addWidget(preview)
    preview.load_archive(str(sample_archives["tar_gz"]))

    assert "package.tar.gz" in preview.name_label.text()
    assert preview.table.rowCount() >= 2
    assert preview.explore_btn.isEnabled()
    assert preview.extract_btn.isEnabled()
    assert not preview.status_label.isVisible()


def test_archive_extract_dialog_init(sample_archives, qtbot):
    dlg_zip = ArchiveExtractDialog(str(sample_archives["zip"]))
    qtbot.addWidget(dlg_zip)
    assert dlg_zip.subfolder_cb.isChecked()
    assert "'bundle'" in dlg_zip.subfolder_cb.text()

    dlg_tar = ArchiveExtractDialog(str(sample_archives["tar_gz"]))
    qtbot.addWidget(dlg_tar)
    assert dlg_tar.subfolder_cb.isChecked()
    assert "'package'" in dlg_tar.subfolder_cb.text()


def test_archive_viewer_dialog_filtering_and_integrity(sample_archives, qtbot):
    dlg = ArchiveViewerDialog(str(sample_archives["tar_gz"]))
    qtbot.addWidget(dlg)

    assert dlg.table.rowCount() >= 2

    # Filter nach 'run'
    dlg.filter_edit.setText("run")
    assert dlg.table.rowCount() == 1

    # Filter zurücksetzen
    dlg.filter_edit.setText("")
    assert dlg.table.rowCount() >= 2

    # Test-Worker starten
    dlg._test_integrity()
    assert dlg.test_worker is not None
    qtbot.waitUntil(lambda: "fehlerfrei" in dlg.integrity_label.text() or "bestanden" in dlg.integrity_label.text(), timeout=5000)


def test_archive_compress_dialog_and_creation(sample_archives, qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    tmp_path = sample_archives["tmpdir"]
    src_file = tmp_path / "sample.txt"
    src_file.write_text("Hello compression test", encoding="utf-8")

    dlg = ArchiveCompressDialog([str(src_file)], current_dir=str(tmp_path))
    qtbot.addWidget(dlg)

    assert "sample.zip" in dlg.dest_edit.text()
    assert dlg.method_combo.count() >= 4

    # Ziel auf TAR.GZ ändern
    target_tar = tmp_path / "out.tar.gz"
    dlg.dest_edit.setText(str(target_tar))

    # Komprimierung ausführen
    dlg._start_compression()
    assert dlg.worker is not None
    qtbot.waitUntil(lambda: target_tar.exists(), timeout=5000)
    assert target_tar.is_file()
    assert is_archive(target_tar)


def test_file_browser_archive_extraction_helper(sample_archives, qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    from gui.browser.file_browser import FileBrowser
    browser = FileBrowser()
    qtbot.addWidget(browser)

    tar_path = sample_archives["tar_gz"]
    extract_base = sample_archives["tmpdir"] / "browser_extracted"
    extract_base.mkdir(parents=True, exist_ok=True)
    browser._current_path = str(extract_base)

    browser._extract_archive_here(str(tar_path))
    expected_dir = extract_base / "package"
    assert expected_dir.is_dir()
    assert (expected_dir / "info.json").is_file()

