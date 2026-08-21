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

from gui.browser.file_browser import FileBrowser


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dnd_flags_enabled():
    """DnD-Flags: acceptDrops auf Tabelle UND FileBrowser muss True sein."""
    _ensure_app()
    browser = FileBrowser()
    assert browser.table.acceptDrops(), "table.acceptDrops() muss True sein"
    assert browser.acceptDrops(), "FileBrowser.acceptDrops() muss True sein"
    assert browser.table.dragEnabled(), "table.dragEnabled() muss True sein"


def test_do_file_drop_copies_file(tmp_path):
    """_do_file_drop kopiert eine Quelldatei ohne das Original zu löschen."""
    _ensure_app()
    browser = FileBrowser()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src_file = src_dir / "hello.txt"
    src_file.write_text("DnD-Test", encoding="utf-8")

    target = tmp_path / "target"
    target.mkdir()
    browser.navigate_to(str(target))

    browser._do_file_drop([str(src_file)], str(target), move=False)

    assert (target / "hello.txt").exists(), "Datei muss im Zielordner landen"
    assert src_file.exists(), "Original muss bei Copy erhalten bleiben"


def test_do_file_drop_same_dir_is_noop(tmp_path):
    """_do_file_drop überspringt lautlos wenn Quelle und Ziel identisch sind."""
    _ensure_app()
    browser = FileBrowser()

    src_file = tmp_path / "noop.txt"
    src_file.write_text("skip-test", encoding="utf-8")
    browser.navigate_to(str(tmp_path))

    # Kein Fehler, keine Duplikate
    browser._do_file_drop([str(src_file)], str(tmp_path), move=False)
    copies = list(tmp_path.glob("noop*.txt"))
    assert len(copies) == 1, "Keine Kopie darf entstehen, wenn Quelle == Ziel"


def test_do_file_drop_uses_unique_suffix_without_overwrite(tmp_path):
    """Eine vorhandene _copy-Datei darf bei weiteren Drops nicht überschrieben werden."""
    _ensure_app()
    browser = FileBrowser()

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src_file = src_dir / "report.txt"
    src_file.write_text("neuer Inhalt", encoding="utf-8")

    target = tmp_path / "target"
    target.mkdir()
    (target / "report.txt").write_text("Original", encoding="utf-8")
    (target / "report_copy.txt").write_text("bestehende Kopie", encoding="utf-8")

    browser._do_file_drop([str(src_file)], str(target), move=False)

    assert (target / "report_copy.txt").read_text(encoding="utf-8") == "bestehende Kopie"
    assert (target / "report_copy_2.txt").read_text(encoding="utf-8") == "neuer Inhalt"


def test_do_file_drop_rejects_directory_into_its_descendant(tmp_path, monkeypatch):
    """Ein Ordner darf nicht in sich selbst oder einen Nachfahren kopiert werden."""
    _ensure_app()
    browser = FileBrowser()
    source = tmp_path / "source"
    target = source / "child"
    target.mkdir(parents=True)

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    copytree = Mock()
    monkeypatch.setattr("gui.browser.file_browser.shutil.copytree", copytree)

    browser._do_file_drop([str(source)], str(target), move=False)

    copytree.assert_not_called()
    assert not (target / "source").exists()
    warning.assert_called_once()
    assert "eigenen Unterordner" in warning.call_args.args[2]


def test_open_file_shows_warning_when_windows_has_no_association(tmp_path, monkeypatch):
    _ensure_app()

    browser = FileBrowser()
    file_path = tmp_path / "Verzeichnis.db"
    file_path.write_text("dummy", encoding="utf-8")

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(
        "gui.browser.file_browser.open_path_with_system",
        Mock(side_effect=OSError(1155, "no application associated")),
    )

    browser._open_file(str(file_path))

    warning.assert_called_once()
    args, kwargs = warning.call_args
    assert args[0] is browser
    assert args[1] == "Datei öffnen"
    assert str(file_path) in args[2]
    assert kwargs == {}


def test_create_new_folder_creates_directory(tmp_path, monkeypatch):
    """create_new_folder erstellt Unterordner und aktualisiert die Ansicht."""
    _ensure_app()
    from PySide6.QtWidgets import QInputDialog

    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    monkeypatch.setattr(
        QInputDialog, "getText",
        lambda *args, **kwargs: ("NeuerUnterordner", True)
    )

    browser.create_new_folder()

    created = tmp_path / "NeuerUnterordner"
    assert created.exists()
    assert created.is_dir()


def test_create_new_folder_cancelled(tmp_path, monkeypatch):
    """Abbrechen des Dialogs erstellt keinen Ordner."""
    _ensure_app()
    from PySide6.QtWidgets import QInputDialog

    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    monkeypatch.setattr(
        QInputDialog, "getText",
        lambda *args, **kwargs: ("NeuerUnterordner", False)
    )

    browser.create_new_folder()
    assert not (tmp_path / "NeuerUnterordner").exists()


def test_create_new_folder_collision(tmp_path, monkeypatch):
    """Vorhandener Ordnername zeigt Warnung an."""
    _ensure_app()
    from PySide6.QtWidgets import QInputDialog

    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    (tmp_path / "Bestehend").mkdir()

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(
        QInputDialog, "getText",
        lambda *args, **kwargs: ("Bestehend", True)
    )

    browser.create_new_folder()
    warning.assert_called_once()
    assert "existiert bereits" in warning.call_args.args[2]


def test_rename_selection_renames_file(tmp_path, monkeypatch):
    """rename_selection benennt Datei erfolgreich um."""
    _ensure_app()
    from PySide6.QtWidgets import QInputDialog

    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    src_file = tmp_path / "alt.txt"
    src_file.write_text("Inhalt", encoding="utf-8")

    monkeypatch.setattr(
        QInputDialog, "getText",
        lambda *args, **kwargs: ("neu.txt", True)
    )

    browser.rename_selection(str(src_file))

    assert not src_file.exists()
    assert (tmp_path / "neu.txt").exists()
    assert (tmp_path / "neu.txt").read_text(encoding="utf-8") == "Inhalt"


def test_rename_selection_collision(tmp_path, monkeypatch):
    """Kollision beim Umbenennen zeigt Warnung und überschreibt nicht."""
    _ensure_app()
    from PySide6.QtWidgets import QInputDialog

    browser = FileBrowser()
    file1 = tmp_path / "eins.txt"
    file1.write_text("1", encoding="utf-8")
    file2 = tmp_path / "zwei.txt"
    file2.write_text("2", encoding="utf-8")

    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    monkeypatch.setattr(
        QInputDialog, "getText",
        lambda *args, **kwargs: ("zwei.txt", True)
    )

    browser.rename_selection(str(file1))

    warning.assert_called_once()
    assert file1.exists()
    assert file2.read_text(encoding="utf-8") == "2"


def test_delete_selection_confirmed(tmp_path, monkeypatch):
    """delete_selection löscht Dateien und Ordner bei Bestätigung mit Ja."""
    _ensure_app()

    browser = FileBrowser()
    browser.navigate_to(str(tmp_path))

    del_file = tmp_path / "loeschen.txt"
    del_file.write_text("weg", encoding="utf-8")
    del_dir = tmp_path / "loesch_ordner"
    del_dir.mkdir()
    (del_dir / "sub.txt").write_text("sub", encoding="utf-8")

    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )

    browser.delete_selection([str(del_file), str(del_dir)])

    assert not del_file.exists()
    assert not del_dir.exists()


def test_delete_selection_rejected(tmp_path, monkeypatch):
    """delete_selection bricht bei Nein ab und behält Dateien."""
    _ensure_app()

    browser = FileBrowser()
    keep_file = tmp_path / "behalten.txt"
    keep_file.write_text("hier", encoding="utf-8")

    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No
    )

    browser.delete_selection([str(keep_file)])
    assert keep_file.exists()


def test_copy_and_paste_selection(tmp_path):
    """copy_selection kopiert Pfade in die Zwischenablage und paste_from_clipboard fügt sie ein."""
    _ensure_app()

    browser = FileBrowser()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src_file = src_dir / "clip.txt"
    src_file.write_text("zwischenablage", encoding="utf-8")

    target_dir = tmp_path / "target"
    target_dir.mkdir()

    browser.get_selected_files = lambda: [str(src_file)]
    browser.copy_selection()

    browser.navigate_to(str(target_dir))
    browser.paste_from_clipboard()

    assert (target_dir / "clip.txt").exists()
    assert (target_dir / "clip.txt").read_text(encoding="utf-8") == "zwischenablage"


def test_save_path_as_prompt_and_add_to_blacklist(tmp_path, monkeypatch):
    """_save_path_as_prompt und _add_to_blacklist laufen fehlerfrei durch."""
    _ensure_app()

    browser = FileBrowser()
    info = Mock()
    monkeypatch.setattr(QMessageBox, "information", info)

    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')", encoding="utf-8")

    browser._save_path_as_prompt(str(test_file))
    info.assert_called()

    info.reset_mock()
    browser._add_to_blacklist(str(test_file))
    info.assert_called()
