"""Regressionstest: ExplorerApp.closeEvent() bereinigt search_worker (Bug #8-9)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QCloseEvent

_APP = QApplication.instance() or QApplication([])


def _make_app():
    from app import ExplorerProApp
    return ExplorerProApp()


def test_close_event_stops_running_search_worker():
    """closeEvent muss cancel()+wait() auf sidebar.search_panel.search_worker aufrufen (Bug #8-9)."""
    app = _make_app()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    app.sidebar.search_panel.search_worker = mock_worker

    app.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_once()
    app.deleteLater()


def test_close_event_skips_finished_search_worker():
    """closeEvent darf cancel()/wait() nicht aufrufen wenn Worker bereits fertig."""
    app = _make_app()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    app.sidebar.search_panel.search_worker = mock_worker

    app.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_not_called()
    mock_worker.wait.assert_not_called()
    app.deleteLater()
