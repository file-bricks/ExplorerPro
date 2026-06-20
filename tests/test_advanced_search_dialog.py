"""Regressionstests: AdvancedSearchDialog (Bug #8-4 + #8-5)."""
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


# ── Bug #8-4: closeEvent stoppt search_worker ─────────────────────────────

def test_close_event_cancels_running_search_worker():
    """closeEvent muss cancel()+wait() auf einen laufenden search_worker aufrufen."""
    _ensure_app()
    from gui.sidebar.advanced_search_dialog import AdvancedSearchDialog

    dlg = AdvancedSearchDialog()
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    dlg.search_worker = mock_worker

    dlg.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_once()
    dlg.deleteLater()


def test_close_event_skips_finished_search_worker():
    """closeEvent darf cancel()/wait() nicht aufrufen wenn Worker bereits fertig."""
    _ensure_app()
    from gui.sidebar.advanced_search_dialog import AdvancedSearchDialog

    dlg = AdvancedSearchDialog()
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    dlg.search_worker = mock_worker

    dlg.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_not_called()
    mock_worker.wait.assert_not_called()
    dlg.deleteLater()


# ── Bug #8-5: 'filename'-Spalte statt 'name' ──────────────────────────────

def test_results_table_shows_filename_not_empty():
    """_on_results_ready muss 'filename' aus dem Result-Dict lesen, nicht 'name' (Bug #8-5)."""
    _ensure_app()
    from gui.sidebar.advanced_search_dialog import AdvancedSearchDialog

    dlg = AdvancedSearchDialog()
    fake_results = [
        {"filename": "report.txt", "path": "/tmp/report.txt", "extension": ".txt",
         "size": 1024, "modified": "2026-01-15 10:00:00"},
    ]
    dlg._on_results_ready(fake_results)

    assert dlg.results_table.rowCount() == 1
    name_text = dlg.results_table.item(0, 0).text()
    assert name_text == "report.txt", f"Erwartet 'report.txt', war '{name_text}'"
    dlg.deleteLater()
