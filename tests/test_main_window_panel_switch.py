"""
Bugfix-Test: main_window.py – show_apps_panel / show_prompts_panel / show_sync_panel
waren leere Stubs (pass) und taten nichts, obwohl Sidebar bereits switch_to_*()
bereitstellte. Menü-Items mit Ctrl+1/2/3 hatten daher keinen Effekt.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from gui.main_window import MainWindow


class TestMainWindowPanelSwitch:
    """show_apps/prompts/sync_panel müssen Sidebar-Methoden aufrufen."""

    def _make_window(self) -> MainWindow:
        win = MainWindow()
        win.sidebar = MagicMock()
        return win

    def test_show_apps_panel_calls_sidebar(self):
        win = self._make_window()
        win.show_apps_panel()
        win.sidebar.switch_to_apps.assert_called_once()

    def test_show_prompts_panel_calls_sidebar(self):
        win = self._make_window()
        win.show_prompts_panel()
        win.sidebar.switch_to_prompts.assert_called_once()

    def test_show_sync_panel_calls_sidebar(self):
        win = self._make_window()
        win.show_sync_panel()
        win.sidebar.switch_to_sync.assert_called_once()
