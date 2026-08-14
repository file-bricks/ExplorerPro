"""
Bugfix-Test (Usertest Welle 1, 2026-08-14): Zwei Menuebefehle waren funktionslos.

U1  Tools -> "Einstellungen..." besass kein triggered.connect; der Klick loeste
    nichts aus, weil die QAction nur der Menueleiste hinzugefuegt wurde.
U2  Der Toolbar-Schalter "Ansicht" (QToolButton, InstantPopup) hatte nie ein
    Menue per setMenu() zugewiesen bekommen. Ein InstantPopup-Button ohne Menue
    reagiert auf einen Klick garantiert nicht.

Die Tests halten beide Verdrahtungen fest und pruefen zusaetzlich, dass der
Dialog eine Referenz am Fenster behaelt (sonst raeumt der Garbage Collector ihn
sofort ab) und dass Speichern und Zuruecklesen der Einstellungen funktioniert.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMenu

_app = QApplication.instance() or QApplication([])

from gui.main_window import MainWindow  # noqa: E402
from gui.settings_dialog import SettingsDialog  # noqa: E402


def _find_action(win: MainWindow, prefix: str):
    for menu in win.menuBar().findChildren(QMenu):
        for action in menu.actions():
            if action.text().startswith(prefix):
                return action
    return None


class TestSettingsMenuAction:
    """U1: Der Menuepunkt Einstellungen muss ein Fenster oeffnen."""

    def test_settings_action_exists(self):
        win = MainWindow()
        assert _find_action(win, "Einstellungen...") is not None

    def test_settings_action_opens_dialog(self, monkeypatch):
        win = MainWindow()
        opened = {}

        def fake_exec(self):
            opened["titel"] = self.windowTitle()
            opened["tabs"] = [self.tabs.tabText(i) for i in range(self.tabs.count())]
            return SettingsDialog.DialogCode.Rejected

        monkeypatch.setattr(SettingsDialog, "exec", fake_exec)
        win._show_settings()

        assert opened.get("titel") == "Einstellungen"
        assert "Allgemein" in opened.get("tabs", [])

    def test_dialog_reference_is_kept(self, monkeypatch):
        """Ohne gehaltene Referenz verschwindet der Dialog sofort wieder."""
        win = MainWindow()
        monkeypatch.setattr(
            SettingsDialog, "exec", lambda self: SettingsDialog.DialogCode.Rejected
        )
        win._show_settings()

        assert isinstance(win.settings_dialog, SettingsDialog)
        assert win.settings_dialog.parent() is win


class TestViewToolButtonMenu:
    """U2: Der Toolbar-Schalter Ansicht muss ein Menue aufklappen."""

    def test_view_button_has_menu(self):
        win = MainWindow()
        assert win.toolbar.view_btn.menu() is not None

    def test_view_menu_contains_expected_entries(self):
        win = MainWindow()
        titles = [
            action.text()
            for action in win.toolbar.view_btn.menu().actions()
            if not action.isSeparator()
        ]

        assert "Sidebar anzeigen" in titles
        assert "Vorschau anzeigen" in titles
        assert "Aktualisieren" in titles

    def test_view_menu_shares_actions_with_menubar(self):
        """Gemeinsame Aktionen halten die Haekchen in beiden Menues synchron."""
        win = MainWindow()
        menu_actions = win.toolbar.view_btn.menu().actions()

        assert win.toggle_sidebar in menu_actions
        assert win.toggle_preview in menu_actions

    def test_toggle_sidebar_from_view_menu_works(self):
        # isVisibleTo statt isVisible: Das Fenster wird im Test nie angezeigt,
        # dadurch meldet jedes Kind-Widget grundsaetzlich isVisible() == False.
        win = MainWindow()
        before = win.sidebar.isVisibleTo(win)

        win.toggle_sidebar.trigger()

        assert win.sidebar.isVisibleTo(win) != before


class TestSettingsDialogRoundtrip:
    """Der Dialog muss Werte laden, schreiben und zurueckliefern."""

    def test_settings_roundtrip(self, tmp_path):
        win = MainWindow()
        dialog = SettingsDialog(win)
        dialog.settings._config_path = tmp_path / "settings.json"

        before = dialog.settings.get("general", "show_hidden_files", False)
        dialog.show_hidden_cb.setChecked(not before)
        dialog.apply_to_settings()

        assert dialog.settings.get("general", "show_hidden_files") is (not before)
        assert (tmp_path / "settings.json").exists()

        dialog.show_hidden_cb.setChecked(before)
        dialog.apply_to_settings()

    def test_collect_settings_covers_all_sections(self):
        win = MainWindow()
        collected = SettingsDialog(win).collect_settings()

        assert set(collected) == {
            "general", "index", "preview", "privacy", "appearance"
        }

    def test_apply_settings_does_not_raise(self):
        win = MainWindow()
        win._apply_settings()

    def test_file_browser_can_toggle_hidden_files(self):
        win = MainWindow()
        win.file_browser.set_show_hidden_files(True)
        win.file_browser.set_show_hidden_files(False)
