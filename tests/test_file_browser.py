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
