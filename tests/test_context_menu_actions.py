"""Regressionstests T-20260926-912169808: Kontextmenü-Aktionen, Editor-Dirty-Flag, Qt-Übersetzung."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox

import gui.browser.file_browser as file_browser_module
from gui.browser.file_browser import FileBrowser
from core.file_index import FileIndex


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _context_actions(browser: FileBrowser, path: Path, monkeypatch) -> dict:
    """Öffnet das Kontextmenü auf `path` und gibt dessen Aktionen nach Text zurück."""
    app = _ensure_app()
    browser.navigate_to(str(path.parent))
    for _ in range(100):
        app.processEvents()
        index = browser.proxy.mapFromSource(browser.model.index(str(path)))
        if index.isValid():
            break
        time.sleep(0.02)
    assert index.isValid()
    browser.table.selectRow(index.row())

    captured = {}

    class _CapturingMenu(QMenu):
        def exec(self, *args):
            captured["menu"] = self

    monkeypatch.setattr(file_browser_module, "QMenu", _CapturingMenu)
    browser._show_context_menu(browser.table.visualRect(index).center())
    return {a.text(): a for a in captured["menu"].actions() if a.text()}


def test_context_menu_rename_and_delete(tmp_path, monkeypatch):
    _ensure_app()
    target = tmp_path / "alt.txt"
    target.write_text("x", encoding="utf-8")
    browser = FileBrowser()
    browser.resize(800, 600)

    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("neu.txt", True))
    _context_actions(browser, target, monkeypatch)["Umbenennen"].trigger()
    assert (tmp_path / "neu.txt").exists() and not target.exists()

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    _context_actions(browser, tmp_path / "neu.txt", monkeypatch)["Löschen"].trigger()
    assert not (tmp_path / "neu.txt").exists()


def test_metadata_and_tags_actions_show_hidden_panel_and_persist_tags(tmp_path, monkeypatch):
    _ensure_app()
    from gui.main_window import MainWindow

    target = tmp_path / "doku.txt"
    target.write_text("x", encoding="utf-8")
    index = FileIndex(str(tmp_path / "index.db"))

    win = MainWindow()
    win.preview_panel.metadata_panel.set_file_index(index)
    win.toggle_preview.setChecked(False)
    win._toggle_preview()
    assert win.preview_panel.isHidden()

    actions = _context_actions(win.file_browser, target, monkeypatch)
    actions["📊 Metadaten anzeigen"].trigger()
    assert not win.preview_panel.isHidden()
    panel = win.preview_panel.metadata_panel
    assert panel.name_label.text() == "doku.txt"

    actions["🏷️ Tags bearbeiten"].trigger()
    panel.tags_edit.setText("wichtig, projekt")
    panel.notes_edit.setPlainText("Notiz")
    panel.tags_edit.editingFinished.emit()
    assert index.get_tags(str(target)) == ["projekt", "wichtig"]
    assert index.get_note(str(target)) == "Notiz"

    # Neu laden zeigt die gespeicherten Werte wieder an
    panel.clear_metadata()
    panel.show_metadata(str(target))
    assert panel.tags_edit.text() == "projekt, wichtig"
    assert panel.notes_edit.toPlainText() == "Notiz"
    win.deleteLater()


def test_reindex_keeps_tags(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("inhalt", encoding="utf-8")
    index = FileIndex(str(tmp_path / "index.db"))
    index.set_tags(str(target), ["rot"])
    assert index.index_file(str(target), calculate_hash=False)
    assert index.get_tags(str(target)) == ["rot"]
    assert [r["path"] for r in index.advanced_search(tags=["rot"])] == [str(target)]


def test_quick_editor_not_modified_after_open(tmp_path):
    app = _ensure_app()
    from modules.editor.quick_editor import QuickEditorDialog

    target = tmp_path / "script.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")
    editor = QuickEditorDialog(str(target))
    for _ in range(5):  # verzögertes Highlighting abarbeiten lassen
        app.processEvents()
    assert editor._modified is False
    assert editor.modified_label.text() == ""

    editor.editor.insertPlainText("# x\n")
    assert editor._modified is True
    editor.editor.document().undo()
    assert editor._modified is False
    editor.deleteLater()


def test_qt_standard_buttons_are_german():
    app = _ensure_app()
    from main import install_qt_translations

    translator = install_qt_translations(app, "de")
    try:
        assert translator is not None
        box = QMessageBox(
            QMessageBox.Icon.Question, "t", "t",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        assert box.button(QMessageBox.StandardButton.Save).text() == "Speichern"
        assert box.button(QMessageBox.StandardButton.Cancel).text() == "Abbrechen"
    finally:
        app.removeTranslator(translator)


def test_translator_importable_from_source_start():
    """main.py muss die Projektwurzel (translator.py) auf sys.path legen."""
    code = (
        "import runpy, sys; runpy.run_path(sys.argv[1], run_name='probe'); "
        "import gui.batch_rename_dialog, gui.diff_dialog, gui.settings_dialog"
    )
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH="")
    result = subprocess.run(
        [sys.executable, "-c", code, str(SRC_DIR / "main.py")],
        cwd=str(ROOT.parent), env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_spec_bundles_translator_and_locales():
    spec = (ROOT / "ExplorerPro.spec").read_text(encoding="utf-8")
    assert "pathex=[str(src_dir), str(project_root)]" in spec
    assert "(str(project_root / 'locales'), 'locales')" in spec
