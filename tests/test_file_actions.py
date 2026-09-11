#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_file_actions.py - Tests für Datei-Erstellung und Browser-Aktionen (TW-EP-10)
"""

import os
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from gui.browser.file_browser import FileBrowser


def _ensure_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_file_browser_batch_and_diff_helpers(tmp_path: Path):
    _ensure_app()
    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("aaa", encoding="utf-8")
    f2.write_text("bbb", encoding="utf-8")

    # Helper methods exist
    assert hasattr(browser, "create_new_file")
    assert hasattr(browser, "_show_batch_rename")
    assert hasattr(browser, "_show_diff")


def test_file_browser_create_new_file(tmp_path: Path):
    _ensure_app()
    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    # Mock QInputDialog to return "created_test.txt", True
    with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("created_test.txt", True)):
        res = browser.create_new_file()
        assert res is True
        created_file = tmp_path / "created_test.txt"
        assert created_file.exists()
        assert created_file.is_file()

    # Cancel case
    with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("cancelled.txt", False)):
        res = browser.create_new_file()
        assert res is False
        assert not (tmp_path / "cancelled.txt").exists()

    # Already exists case (collision warning)
    with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("created_test.txt", True)):
        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
            res = browser.create_new_file()
            assert res is False
            assert mock_warn.called
