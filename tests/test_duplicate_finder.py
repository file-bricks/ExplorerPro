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


def test_duplicate_scan_worker_find_from_index(tmp_path):
    """DuplicateScanWorker._find_from_index liest Duplikate aus der SQLite-Datenbank."""
    from core.file_index import FileIndex
    from modules.indexer.duplicate_finder import DuplicateScanWorker

    db_file = tmp_path / "test_index.db"
    idx = FileIndex(str(db_file))

    # Zwei identische Dateien erstellen
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    content = "Gleicher Inhalt für Hash-Berechnung"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    idx.index_file(str(f1), calculate_hash=True)
    idx.index_file(str(f2), calculate_hash=True)

    worker = DuplicateScanWorker(file_index=idx, min_size=1, use_index=True)
    found_duplicates = []
    worker.duplicates_found.connect(lambda d: found_duplicates.append(d))
    worker.run()

    assert len(found_duplicates) == 1
    assert len(found_duplicates[0]) == 1  # 1 Hash-Gruppe
    hash_val = list(found_duplicates[0].keys())[0]
    assert sorted(found_duplicates[0][hash_val]) == sorted([str(f1), str(f2)])


def test_duplicate_dialog_delete_syncs_file_index(tmp_path, monkeypatch):
    """Beim Löschen von Duplikaten wird der FileIndex synchron gehalten."""
    from core.file_index import FileIndex
    from PySide6.QtWidgets import QMessageBox

    _ensure_app()
    db_file = tmp_path / "test_index.db"
    idx = FileIndex(str(db_file))

    f1 = tmp_path / "dup1.txt"
    f2 = tmp_path / "dup2.txt"
    f1.write_text("Inhalt", encoding="utf-8")
    f2.write_text("Inhalt", encoding="utf-8")

    idx.index_file(str(f1), calculate_hash=True)
    idx.index_file(str(f2), calculate_hash=True)

    dialog = DuplicateFinderDialog(file_index=idx)
    mock_box = MagicMock()
    mock_box.StandardButton = QMessageBox.StandardButton
    mock_box.question.return_value = QMessageBox.StandardButton.Yes
    monkeypatch.setattr("modules.indexer.duplicate_finder.QMessageBox", mock_box)
    monkeypatch.setattr(dialog, "_start_scan", lambda: None)

    dialog.duplicate_groups = {"hash1": [str(f1), str(f2)]}
    dialog._on_duplicates_found(dialog.duplicate_groups)
    dialog._select_all_duplicates()  # wählt f2 aus

    dialog._delete_selected()

    assert not f2.exists()
    assert idx.get_file(str(f2)) is None
    assert f1.exists()
    assert idx.get_file(str(f1)) is not None
