#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_batch_rename_and_diff_dialogs.py - GUI-Tests für BatchRenameDialog und DiffDialog
"""

import os
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from gui.batch_rename_dialog import BatchRenameDialog
from gui.diff_dialog import DiffDialog


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_batch_rename_dialog_ui(tmp_path: Path):
    _ensure_app()
    f1 = tmp_path / "img_01.jpg"
    f2 = tmp_path / "img_02.jpg"
    f1.write_text("photo1", encoding="utf-8")
    f2.write_text("photo2", encoding="utf-8")

    dlg = BatchRenameDialog([str(f1), str(f2)])
    assert dlg.table.rowCount() == 2
    assert dlg.rename_btn.isEnabled() is False  # Keine Änderung bisher

    # Suchen & Ersetzen eingeben
    dlg.search_edit.setText("img")
    dlg.replace_edit.setText("vacation")
    QApplication.processEvents()

    assert dlg.table.rowCount() == 2
    assert dlg.table.item(0, 1).text() == "vacation_01.jpg"
    assert dlg.table.item(1, 1).text() == "vacation_02.jpg"
    assert dlg.rename_btn.isEnabled() is True

    # Präfix hinzufügen
    dlg.prefix_edit.setText("2026_")
    QApplication.processEvents()
    assert dlg.table.item(0, 1).text() == "2026_vacation_01.jpg"

    dlg.close()


def test_diff_dialog_ui(tmp_path: Path):
    _ensure_app()
    f1 = tmp_path / "text_a.txt"
    f2 = tmp_path / "text_b.txt"
    f1.write_text("Line One\nLine Two\n", encoding="utf-8")
    f2.write_text("Line One\nLine Two Modified\nLine Three\n", encoding="utf-8")

    dlg = DiffDialog(str(f1), str(f2))
    QApplication.processEvents()

    assert dlg.table.rowCount() > 0
    assert dlg.copy_btn.isEnabled() is True
    assert "Unterschiede" in dlg.status_label.text()

    # Diff in Zwischenablage kopieren (mit gemockter QMessageBox)
    with patch("PySide6.QtWidgets.QMessageBox.information"):
        dlg._copy_unified_diff()
    clipboard_content = QApplication.clipboard().text()
    assert "---" in clipboard_content or "Line Two" in clipboard_content

    # Gleiche Datei vergleichen
    dlg2 = DiffDialog(str(f1), str(f1))
    QApplication.processEvents()
    assert "identisch" in dlg2.status_label.text().lower()

    dlg.close()
    dlg2.close()
