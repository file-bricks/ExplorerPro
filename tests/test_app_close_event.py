"""Regressionstest: app.py closeEvent muss index_worker stoppen (Bug #8-2)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QCloseEvent


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_close_event_stops_running_index_worker():
    """closeEvent muss cancel()+wait() auf einen laufenden index_worker aufrufen."""
    _ensure_app()

    from app import ExplorerProApp

    win = ExplorerProApp()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    win.index_worker = mock_worker

    win.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_once()
    win.deleteLater()


def test_close_event_skips_finished_index_worker():
    """closeEvent darf cancel()/wait() nicht aufrufen wenn der Worker schon fertig ist."""
    _ensure_app()

    from app import ExplorerProApp

    win = ExplorerProApp()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    win.index_worker = mock_worker

    win.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_not_called()
    mock_worker.wait.assert_not_called()
    win.deleteLater()
