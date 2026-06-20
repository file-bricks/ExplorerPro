from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from modules.indexer.duplicate_finder import DuplicateFinderDialog


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_duplicate_finder_open_file_shows_warning_when_windows_has_no_association(
    tmp_path, monkeypatch
):
    _ensure_app()

    dialog = DuplicateFinderDialog()
    file_path = tmp_path / "Verzeichnis.db"
    file_path.write_text("dummy", encoding="utf-8")

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(
        "modules.indexer.duplicate_finder.open_path_with_system",
        Mock(side_effect=OSError(1155, "no application associated")),
    )

    dialog._open_file(str(file_path))

    warning.assert_called_once()
    args, kwargs = warning.call_args
    assert args[0] is dialog
    assert args[1] == "Datei öffnen"
    assert str(file_path) in args[2]
    assert kwargs == {}


def test_duplicate_finder_open_folder_shows_warning_when_windows_has_no_association(
    tmp_path, monkeypatch
):
    _ensure_app()

    dialog = DuplicateFinderDialog()
    file_path = tmp_path / "Verzeichnis.db"
    file_path.write_text("dummy", encoding="utf-8")
    folder_path = str(file_path.parent)

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(
        "modules.indexer.duplicate_finder.open_path_with_system",
        Mock(side_effect=OSError(1155, "no application associated")),
    )

    dialog._open_folder(str(file_path))

    warning.assert_called_once()
    args, kwargs = warning.call_args
    assert args[0] is dialog
    assert args[1] == "Ordner öffnen"
    assert folder_path in args[2]
    assert kwargs == {}


def test_close_event_cancels_running_scan_worker():
    """closeEvent muss einen laufenden scan_worker stoppen (Bug #8-1 Regression)."""
    from PySide6.QtGui import QCloseEvent

    _ensure_app()
    dialog = DuplicateFinderDialog()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    dialog.scan_worker = mock_worker

    dialog.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_called_once()
    mock_worker.wait.assert_called_once()


def test_close_event_skips_stopped_scan_worker():
    """closeEvent darf cancel/wait nicht aufrufen wenn der Worker bereits fertig ist."""
    from PySide6.QtGui import QCloseEvent

    _ensure_app()
    dialog = DuplicateFinderDialog()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = False
    dialog.scan_worker = mock_worker

    dialog.closeEvent(QCloseEvent())

    mock_worker.cancel.assert_not_called()
    mock_worker.wait.assert_not_called()
