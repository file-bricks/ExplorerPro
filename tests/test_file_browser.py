from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from gui.browser import file_browser as file_browser_module
from gui.browser.file_browser import FileBrowser


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_open_file_shows_warning_when_windows_has_no_association(tmp_path, monkeypatch):
    _ensure_app()

    browser = FileBrowser()
    file_path = tmp_path / "Verzeichnis.db"
    file_path.write_text("dummy", encoding="utf-8")

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(file_browser_module.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        file_browser_module.os,
        "startfile",
        Mock(side_effect=OSError(1155, "no application associated")),
        raising=False,
    )

    browser._open_file(str(file_path))

    warning.assert_called_once()
    args, kwargs = warning.call_args
    assert args[0] is browser
    assert args[1] == "Datei öffnen"
    assert str(file_path) in args[2]
    assert kwargs == {}
