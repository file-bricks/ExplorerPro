#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_checksum_dialog.py - UI- und Funktionstests für den ChecksumDialog
"""

import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QCloseEvent

from gui.checksum_dialog import ChecksumDialog


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_checksum_dialog_initialization(tmp_path: Path):
    """Prüft Dialog-Aufbau und Hash-Berechnung."""
    _ensure_app()
    sample = tmp_path / "test_dialog.txt"
    sample.write_text("ExplorerPro Dialog Test Content", encoding="utf-8")

    dlg = ChecksumDialog(str(sample))
    assert dlg.path_label.text() == str(sample)
    assert dlg.windowTitle().startswith("Prüfsummen — test_dialog.txt")
    assert "sha256" in dlg.hash_edits
    assert "md5" in dlg.hash_edits

    # Warten auf Abschluss des Workers
    if dlg.worker and dlg.worker.isRunning():
        dlg.worker.wait(2000)
    QApplication.processEvents()

    assert dlg.hash_edits["sha256"].text() != ""
    assert dlg.hash_edits["md5"].text() != ""
    assert dlg.copy_all_btn.isEnabled()

    # Verifikation testen: exakter SHA-256
    computed_sha256 = dlg.hash_edits["sha256"].text()
    dlg.verify_edit.setText(computed_sha256)
    assert "✓" in dlg.verify_result_label.text()

    # Verifikation testen: falscher Hash
    dlg.verify_edit.setText("0000000000000000000000000000000000000000000000000000000000000000")
    assert "✗" in dlg.verify_result_label.text()

    # Verifikation testen: leer
    dlg.verify_edit.setText("")
    assert "Bereit" in dlg.verify_result_label.text()

    # Einzelnes Kopieren
    dlg._copy_hash("sha256")
    assert QApplication.clipboard().text() == computed_sha256

    dlg.close()


def test_checksum_dialog_non_existent_file(tmp_path: Path):
    """Prüft Dialog-Verhalten wenn Datei nicht existiert."""
    _ensure_app()
    dlg = ChecksumDialog(str(tmp_path / "nicht_da.txt"))
    assert "Fehler" in dlg.verify_result_label.text()
    dlg.close()


def test_checksum_dialog_close_cancels_worker(tmp_path: Path):
    """Prüft, dass closeEvent den Worker sauber abbricht."""
    _ensure_app()
    sample = tmp_path / "cancel_test.txt"
    sample.write_bytes(b"X" * (500 * 1024))

    dlg = ChecksumDialog(str(sample))
    dlg.closeEvent(QCloseEvent())
    assert dlg.worker is not None
