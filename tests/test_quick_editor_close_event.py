"""
Bugfix-Test: quick_editor.py QuickEditorDialog.closeEvent() –
Bei Klick auf 'Abbrechen' darf ein laufender Prozess NICHT gekillt werden.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QEvent

_app = QApplication.instance() or QApplication([])

from modules.editor.quick_editor import QuickEditorDialog


def _make_editor():
    editor = QuickEditorDialog.__new__(QuickEditorDialog)
    editor._modified = True
    editor._process = MagicMock()
    editor._process.state.return_value = MagicMock()
    return editor


class FakeCloseEvent:
    def __init__(self):
        self._accepted = None

    def accept(self):
        self._accepted = True

    def ignore(self):
        self._accepted = False

    def isAccepted(self):
        return self._accepted is True


class TestCloseEventCancelFix:
    """Bei Cancel im Save-Dialog darf laufender Prozess nicht gekillt werden."""

    def test_process_not_killed_on_cancel(self, monkeypatch):
        editor = _make_editor()
        mock_process = MagicMock()
        editor._process = mock_process

        monkeypatch.setattr(
            "modules.editor.quick_editor.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Cancel
        )

        event = FakeCloseEvent()
        editor.closeEvent(event)

        mock_process.kill.assert_not_called(), (
            "Prozess wurde beim Cancel-Click gekillt obwohl Editor offen bleibt"
        )
        assert event.isAccepted() is False

    def test_process_killed_on_discard(self, monkeypatch):
        editor = _make_editor()
        mock_process = MagicMock()
        editor._process = mock_process

        monkeypatch.setattr(
            "modules.editor.quick_editor.QMessageBox.question",
            lambda *a, **kw: QMessageBox.StandardButton.Discard
        )

        event = FakeCloseEvent()
        editor.closeEvent(event)

        mock_process.kill.assert_called_once(), (
            "Prozess wurde beim Discard-Click NICHT gekillt"
        )
        assert event.isAccepted() is True

    def test_process_not_killed_when_unmodified(self):
        editor = _make_editor()
        editor._modified = False
        mock_process = MagicMock()
        editor._process = mock_process

        event = FakeCloseEvent()
        editor.closeEvent(event)

        mock_process.kill.assert_called_once()
        assert event.isAccepted() is True
