"""User-visible regressions from ticket T-20260928-288887892."""
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu

import gui.browser.file_browser as browser_module
from gui.browser.file_browser import FileBrowser
from gui.main_window import MainWindow
from gui.preview.preview_panel import PreviewPanel
from modules.editor import quick_editor


def _app():
    return QApplication.instance() or QApplication([])


def _actions_from_real_context_event(browser, path, monkeypatch):
    browser.navigate_to(str(path.parent))
    browser.show()
    for _ in range(100):
        _app().processEvents()
        index = browser.proxy.mapFromSource(browser.model.index(str(path)))
        if index.isValid():
            break
        time.sleep(.01)
    assert index.isValid()
    menus = []

    class CapturingMenu(QMenu):
        def exec(self, *args):
            menus.append(self)

    monkeypatch.setattr(browser_module, "QMenu", CapturingMenu)
    pos = browser.table.visualRect(index).center()
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, pos, browser.table.viewport().mapToGlobal(pos)
    )
    QApplication.sendEvent(browser.table.viewport(), event)
    assert len(menus) == 1, "The viewport must deliver the real context menu event"
    return {action.text(): action for action in menus[0].actions() if action.text()}


def _blank_actions_from_real_context_event(browser, monkeypatch):
    menus = []

    class CapturingMenu(QMenu):
        def exec(self, *args):
            menus.append(self)

    monkeypatch.setattr(browser_module, "QMenu", CapturingMenu)
    pos = browser.table.viewport().rect().bottomRight()
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, pos, browser.table.viewport().mapToGlobal(pos)
    )
    QApplication.sendEvent(browser.table.viewport(), event)
    assert len(menus) == 1
    return {action.text(): action for action in menus[0].actions() if action.text()}


def test_collapsed_sidebar_and_preview_restore_and_render(tmp_path, monkeypatch):
    _app()
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    _app().processEvents()
    win.main_splitter.setSizes([0, 1200])
    win.right_splitter.setSizes([1200, 0])
    assert win.main_splitter.sizes()[0] == 0
    assert win.right_splitter.sizes()[1] == 0

    win._toggle_sidebar()
    win._toggle_preview()
    assert win.main_splitter.sizes()[0] > 0
    assert win.right_splitter.sizes()[1] > 0
    assert win.sidebar.stack.count() >= 6
    assert win.preview_panel.preview_stack.count() >= 6

    target = tmp_path / "Äpfel.txt"
    target.write_text("Vorschau mit Umlauten: Äpfel", encoding="utf-8")
    win.show_file_metadata(str(target))
    assert "Äpfel" in win.preview_panel.text_preview.toPlainText()
    assert win.preview_panel.isVisible()
    win.close()


def test_navigation_loads_files_and_selection_reaches_preview(tmp_path):
    _app()
    target = tmp_path / "Äpfel.txt"
    target.write_text("Sichtbare Vorschau: Äpfel", encoding="utf-8")
    browser = FileBrowser()
    preview = PreviewPanel()
    browser.file_selected.connect(preview.show_preview)
    browser.resize(800, 500)
    browser.show()
    browser.navigate_to(str(tmp_path))
    for _ in range(100):
        _app().processEvents()
        if browser.proxy.rowCount(browser.table.rootIndex()) > 0:
            break
        time.sleep(.01)
    root = browser.proxy.mapToSource(browser.table.rootIndex())
    assert Path(browser.model.filePath(root)) == tmp_path
    assert browser.proxy.rowCount(browser.table.rootIndex()) > 0
    item = browser.proxy.mapFromSource(browser.model.index(str(target)))
    assert item.isValid()
    browser._on_item_clicked(item)
    assert "Äpfel" in preview.text_preview.toPlainText()
    browser.close()
    preview.close()


def test_real_context_event_executes_each_file_action_and_rename(tmp_path, monkeypatch):
    _app()
    target = tmp_path / "alt.txt"
    target.write_text("x", encoding="utf-8")
    browser = FileBrowser()
    browser.resize(800, 500)
    actions = _actions_from_real_context_event(browser, target, monkeypatch)
    calls = {}
    bindings = {
        "📂 Öffnen": "_open_file",
        "✏️ In Editor öffnen": "_edit_file",
        "🔑 Prüfsummen berechnen...": "_show_checksums",
        "🔍 In Index suchen": "_search_in_index",
        "📊 Metadaten anzeigen": "_show_metadata",
        "🏷️ Tags bearbeiten": "_show_metadata",
        "🔄 Synchronisieren": "_sync_path",
        "📋 Pfad als Prompt speichern": "_save_path_as_prompt",
        "🛡️ Datenschutz prüfen": "_check_privacy",
        "🔴 Zur Blacklist hinzufügen": "_add_to_blacklist",
        "Kopieren": "copy_selection",
        "Löschen": "delete_selection",
    }
    for method in set(bindings.values()):
        calls[method] = Mock()
        monkeypatch.setattr(browser, method, calls[method])
    for label, method in bindings.items():
        assert label in actions
        actions[label].trigger()
        assert calls[method].called, label
        calls[method].reset_mock()
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("neu.txt", True))
    actions["Umbenennen"].trigger()
    assert not target.exists()
    assert (tmp_path / "neu.txt").exists()
    browser.close()


def test_real_context_event_executes_multi_selection_actions(tmp_path, monkeypatch):
    _app()
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    browser = FileBrowser()
    browser.resize(800, 500)
    browser.show()
    browser.navigate_to(str(tmp_path))
    for _ in range(100):
        _app().processEvents()
        if browser.proxy.rowCount(browser.table.rootIndex()) == 2:
            break
        time.sleep(.01)
    for path in (first, second):
        index = browser.proxy.mapFromSource(browser.model.index(str(path)))
        browser.table.selectionModel().select(
            index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        )
    batch = Mock()
    diff = Mock()
    monkeypatch.setattr(browser, "_show_batch_rename", batch)
    monkeypatch.setattr(browser, "_show_diff", diff)
    actions = _actions_from_real_context_event(browser, first, monkeypatch)
    actions["✏️ Mehrfach umbenennen..."].trigger()
    actions["⚖️ Dateien vergleichen (Diff)..."].trigger()
    batch.assert_called_once()
    diff.assert_called_once()
    browser.close()
    browser.deleteLater()
    _app().processEvents()


def test_real_context_event_executes_blank_area_actions(tmp_path, monkeypatch):
    _app()
    browser = FileBrowser()
    browser.resize(800, 500)
    browser.show()
    browser.navigate_to(str(tmp_path))
    methods = {
        "📄 Neue Datei...": "create_new_file",
        "📁 Neuer Ordner": "create_new_folder",
        "⚖️ Dateien vergleichen...": "_show_diff",
        "Einfügen": "paste_from_clipboard",
        "Aktualisieren": "refresh",
    }
    calls = {}
    for method in set(methods.values()):
        calls[method] = Mock()
        monkeypatch.setattr(browser, method, calls[method])
    actions = _blank_actions_from_real_context_event(browser, monkeypatch)
    for label, method in methods.items():
        assert label in actions
        actions[label].trigger()
        calls[method].assert_called_once()
    browser.close()
    browser.deleteLater()
    _app().processEvents()


def test_frozen_editor_uses_real_python_and_rejects_alias(tmp_path, monkeypatch):
    script = tmp_path / "script.py"
    script.write_text("print('script ran')", encoding="utf-8")
    fake_app = tmp_path / "ExplorerPro.exe"
    fake_app.write_bytes(b"app")
    alias = tmp_path / "python.exe"
    alias.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_app))
    monkeypatch.setattr(quick_editor.shutil, "which", lambda name: str(alias))
    assert quick_editor.find_python_interpreter() is None

    real_python = tmp_path / "real-python.exe"
    real_python.write_bytes(b"python")
    monkeypatch.setenv("EXPLORERPRO_PYTHON", str(real_python))
    assert quick_editor.find_python_interpreter() == str(real_python)
    monkeypatch.setenv("EXPLORERPRO_PYTHON", str(fake_app))
    assert quick_editor.find_python_interpreter() is None


def test_frozen_run_button_starts_interpreter_not_explorerpro(tmp_path, monkeypatch):
    _app()
    script = tmp_path / "run.py"
    script.write_text("print('script ran')", encoding="utf-8")
    fake_app = tmp_path / "ExplorerPro.exe"
    fake_app.write_bytes(b"app")
    interpreter = tmp_path / "python.exe"
    interpreter.write_bytes(b"python")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_app))
    monkeypatch.setenv("EXPLORERPRO_PYTHON", str(interpreter))

    launched = []
    monkeypatch.setattr(quick_editor.QProcess, "start", lambda self, program, args: launched.append((program, args)))
    editor = quick_editor.QuickEditorDialog(str(script))
    editor._run_code()
    assert launched == [(str(interpreter), [str(script)])]
    editor.close()


def test_right_click_on_unselected_row_selects_row(tmp_path, monkeypatch):
    _app()
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    browser = FileBrowser()
    browser.resize(800, 500)
    browser.show()
    browser.navigate_to(str(tmp_path))
    for _ in range(100):
        _app().processEvents()
        if browser.proxy.rowCount(browser.table.rootIndex()) == 2:
            break
        time.sleep(.01)

    idx_first = browser.proxy.mapFromSource(browser.model.index(str(first)))
    browser.table.selectRow(idx_first.row())
    assert [Path(p) for p in browser.get_selected_files()] == [first]

    idx_second = browser.proxy.mapFromSource(browser.model.index(str(second)))
    assert not browser.table.selectionModel().isRowSelected(idx_second.row(), idx_second.parent())

    menus = []

    class CapturingMenu(QMenu):
        def exec(self, *args):
            menus.append(self)

    monkeypatch.setattr(browser_module, "QMenu", CapturingMenu)
    pos = browser.table.visualRect(idx_second).center()
    event = QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, pos, browser.table.viewport().mapToGlobal(pos)
    )
    QApplication.sendEvent(browser.table.viewport(), event)

    assert browser.table.selectionModel().isRowSelected(idx_second.row(), idx_second.parent())
    assert second in [Path(p) for p in browser.get_selected_files()]

    browser.close()
    browser.deleteLater()
    _app().processEvents()
