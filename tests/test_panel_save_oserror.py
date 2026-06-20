"""Regressionstests: _save_apps() und _save_prompts() fangen OSError ab (Bug #8-6, #8-7)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])


def test_apps_panel_save_does_not_raise_on_oserror():
    """_save_apps() darf bei OSError keine Exception zum Aufrufer weiterwerfen (Bug #8-6)."""
    from modules.launcher.apps_panel import AppsPanel

    panel = AppsPanel()
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = OSError("Disk full")
        try:
            panel._save_apps()
        except OSError:
            raise AssertionError("_save_apps() muss OSError intern abfangen")


def test_prompts_panel_save_does_not_raise_on_oserror():
    """_save_prompts() darf bei OSError keine Exception zum Aufrufer weiterwerfen (Bug #8-7)."""
    from modules.prompts.prompts_panel import PromptsPanel

    panel = PromptsPanel()
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = OSError("Disk full")
        try:
            panel._save_prompts()
        except OSError:
            raise AssertionError("_save_prompts() muss OSError intern abfangen")
