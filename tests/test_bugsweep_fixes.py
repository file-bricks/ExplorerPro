from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog

_app = QApplication.instance() or QApplication([])

from gui.browser.file_browser import FileBrowser
from gui.preview.preview_panel import TextPreview
from modules.sync.sync_manager import SyncWorker, SyncPair, SyncDirection
from core.file_index import FileIndex


def test_file_browser_delete_selection(tmp_path, monkeypatch):
    """FileBrowser.delete_selection löscht ausgewählte Dateien nach Bestätigung."""
    test_file = tmp_path / "delete_me.txt"
    test_file.write_text("weg damit", encoding="utf-8")

    browser = FileBrowser()
    monkeypatch.setattr(browser, "get_selected_files", lambda: [str(test_file)])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    result = browser.delete_selection()
    assert result is True
    assert not test_file.exists()


def test_file_browser_rename_selection(tmp_path, monkeypatch):
    """FileBrowser.rename_selection benennt die ausgewählte Datei um."""
    test_file = tmp_path / "old_name.txt"
    test_file.write_text("Inhalt", encoding="utf-8")

    browser = FileBrowser()
    monkeypatch.setattr(browser, "get_selected_files", lambda: [str(test_file)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("new_name.txt", True))

    result = browser.rename_selection()
    assert result is True
    assert not test_file.exists()
    assert (tmp_path / "new_name.txt").exists()


def test_file_browser_create_new_folder(tmp_path, monkeypatch):
    """FileBrowser.create_new_folder erstellt einen neuen Unterordner."""
    browser = FileBrowser()
    browser._current_path = str(tmp_path)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **kw: ("NeuerOrdner", True))

    result = browser.create_new_folder()
    assert result is True
    assert (tmp_path / "NeuerOrdner").is_dir()


def test_text_preview_syntax_highlighter(tmp_path):
    """TextPreview bindet für Python-Dateien einen Highlighter ein."""
    py_file = tmp_path / "code.py"
    py_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    preview = TextPreview()
    preview.load_file(str(py_file))

    assert "def hello():" in preview.toPlainText()
    assert preview._highlighter is not None

    # Danach txt Datei laden -> Highlighter muss sauber abgelöst werden
    txt_file = tmp_path / "plain.txt"
    txt_file.write_text("Einfacher Text", encoding="utf-8")
    preview.load_file(str(txt_file))
    assert preview._highlighter is None


def test_sync_worker_ignores_files_in_hidden_directories(tmp_path):
    """SyncWorker ignoriert bei include_hidden=False auch Dateien in versteckten Unterordnern."""
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()

    # Sichtbare Datei
    (source_dir / "visible.txt").write_text("sichtbar", encoding="utf-8")
    # Datei im .git oder .hidden Ordner
    hidden_sub = source_dir / ".hidden_dir"
    hidden_sub.mkdir()
    (hidden_sub / "secret.txt").write_text("geheim", encoding="utf-8")

    pair = SyncPair(
        id="test-1",
        name="Test",
        source=str(source_dir),
        target=str(target_dir),
        direction="source_to_target",
        include_hidden=False,
    )
    worker = SyncWorker(pair)
    files = worker._get_files(Path(source_dir))

    # Nur visible.txt darf enthalten sein
    assert Path("visible.txt") in files
    assert Path(".hidden_dir/secret.txt") not in files


def test_file_index_no_datetime_deprecation_warning(tmp_path):
    """FileIndex-Operationen werfen keine sqlite3 Datetime DeprecationWarnings."""
    db_file = tmp_path / "index.db"
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        idx = FileIndex(str(db_file))
        sample = tmp_path / "test.txt"
        sample.write_text("Hallo Index", encoding="utf-8")
        idx.index_file(str(sample))
        idx.search("Hallo")

    dep_warnings = [w for w in recorded if issubclass(w.category, DeprecationWarning) and "sqlite3" in str(w.message).lower()]
    assert len(dep_warnings) == 0
