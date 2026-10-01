"""Menu, settings persistence and all browser deletion entry points."""

import json
import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

from core import delete_service
from core.settings_manager import SettingsManager
import gui.browser.file_browser as browser_module
from gui.main_window import MainWindow
from gui.settings_dialog import SettingsDialog

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setattr(SettingsManager, "_instance", None)
    monkeypatch.setattr(SettingsManager, "_get_config_path", lambda self: tmp_path / "settings.json")
    return SettingsManager.instance()


@pytest.fixture
def window(settings):
    win = MainWindow()
    yield win
    win.close()
    win.deleteLater()
    _app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_menu_checkbox_default_and_json_roundtrip(window, settings):
    action = window.confirm_delete_action
    assert action.isCheckable() and action.isChecked()
    action.trigger()
    assert settings.get("general", "confirm_delete") is False
    assert json.loads(settings._config_path.read_text())["general"]["confirm_delete"] is False
    settings._settings = {}
    settings._load_settings()
    assert settings.get("general", "confirm_delete") is False
    second = MainWindow()
    try:
        assert not second.confirm_delete_action.isChecked()
        action.trigger()
        second.menuBar().actions()[1].menu().aboutToShow.emit()
        assert second.confirm_delete_action.isChecked()
        assert json.loads(settings._config_path.read_text())["general"]["confirm_delete"] is True
    finally:
        second.close()
        second.deleteLater()


def test_settings_dialog_and_menu_share_confirmation(window, settings, monkeypatch):
    window.confirm_delete_action.trigger()

    def accept(dialog):
        assert not dialog.confirm_delete_cb.isChecked()
        dialog.confirm_delete_cb.setChecked(True)
        dialog.apply_to_settings()
        return SettingsDialog.DialogCode.Accepted

    monkeypatch.setattr(SettingsDialog, "exec", accept)
    window._show_settings()
    assert window.confirm_delete_action.isChecked()
    assert settings.get("general", "confirm_delete") is True
    assert json.loads(settings._config_path.read_text())["general"]["confirm_delete"] is True


@pytest.mark.parametrize("invalid", [None, 0, "", "false", [], {}])
def test_only_explicit_json_false_disables_confirmation(window, settings, tmp_path, monkeypatch, invalid):
    settings._config_path.write_text(json.dumps({"general": {"confirm_delete": invalid}}))
    settings._load_settings()
    window._apply_settings()
    assert window.confirm_delete_action.isChecked()
    dialog = SettingsDialog(window)
    assert dialog.confirm_delete_cb.isChecked()
    target = tmp_path / "keep.txt"
    target.write_text("keep")
    question = Mock(return_value=QMessageBox.StandardButton.No)
    monkeypatch.setattr(QMessageBox, "question", question)
    assert not window.file_browser.delete_selection([str(target)])
    question.assert_called_once()
    assert target.exists()
    dialog.deleteLater()


def _context_delete(browser, target, monkeypatch):
    for _ in range(100):
        _app.processEvents()
        index = browser.proxy.mapFromSource(browser.model.index(str(target)))
        if index.isValid():
            break
        QTest.qWait(10)
    assert index.isValid()
    browser.table.selectRow(index.row())

    class CapturingMenu(QMenu):
        def exec(self, *args):
            next(a for a in self.actions() if a.text() == "Löschen").trigger()

    monkeypatch.setattr(browser_module, "QMenu", CapturingMenu)
    browser._show_context_menu(browser.table.visualRect(index).center())


@pytest.mark.parametrize("entry", ["direct", "keyboard", "context"])
@pytest.mark.parametrize("confirm", [True, False])
def test_all_entry_points_use_current_setting(window, settings, tmp_path, monkeypatch, entry, confirm):
    target = tmp_path / "selected.txt"
    target.write_text("delete")
    browser = window.file_browser
    browser.navigate_to(str(tmp_path))
    if not confirm:
        window.confirm_delete_action.trigger()
    question = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "question", question)
    if entry == "direct":
        assert browser.delete_selection([str(target)])
    elif entry == "keyboard":
        monkeypatch.setattr(browser, "get_selected_files", lambda: [str(target)])
        browser.table.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        )
    else:
        _context_delete(browser, target, monkeypatch)
    assert not target.exists()
    assert question.call_count == int(confirm)
    if confirm:
        assert question.call_args.args[-1] == QMessageBox.StandardButton.No


def test_reenabled_confirmation_cancellation_preserves_file(window, tmp_path, monkeypatch):
    target = tmp_path / "keep.txt"
    target.write_text("keep")
    window.confirm_delete_action.trigger()
    window.confirm_delete_action.trigger()
    monkeypatch.setattr(QMessageBox, "question", lambda *a: QMessageBox.StandardButton.No)
    assert not window.file_browser.delete_selection([str(target)])
    assert target.read_text() == "keep"


def test_partial_failure_warns_and_continues(window, tmp_path, monkeypatch):
    blocked = tmp_path / "blocked.txt"
    blocked.write_text("keep")
    good = tmp_path / "good.txt"
    good.write_text("delete")
    window.confirm_delete_action.trigger()
    actual_delete = delete_service.delete_path

    def delete(path):
        if path == str(blocked):
            raise PermissionError("blocked fixture")
        actual_delete(path)

    monkeypatch.setattr(delete_service, "delete_path", delete)
    warning = Mock()
    monkeypatch.setattr(QMessageBox, "warning", warning)
    assert not window.file_browser.delete_selection([str(blocked), str(good)])
    assert blocked.read_text() == "keep"
    assert not good.exists()
    assert "blocked.txt" in warning.call_args.args[2]
    warning.assert_called_once()
