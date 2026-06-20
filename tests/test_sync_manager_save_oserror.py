"""Regressionstest: SyncPanel._save_config() fängt OSError ab (Bug #8-10)."""
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


def test_sync_manager_save_does_not_raise_on_oserror():
    """_save_config() darf bei OSError keine Exception zum Aufrufer weiterwerfen (Bug #8-10)."""
    from modules.sync.sync_manager import SyncPanel

    panel = SyncPanel()
    with patch("builtins.open", mock_open()) as m:
        m.side_effect = OSError("Disk full")
        try:
            panel._save_config()
        except OSError:
            raise AssertionError("_save_config() muss OSError intern abfangen")
