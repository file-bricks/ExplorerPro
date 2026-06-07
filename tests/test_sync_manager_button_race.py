"""
Bugfix-Test: sync_manager.py SyncPanel._on_scan_finished() –
Bei dry_run=False darf der Sync-Button NICHT bereits bei Scan-Ende
reaktiviert werden (der _execute()-Lauf läuft noch im Thread).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from modules.sync.sync_manager import SyncPanel, SyncPair


def _make_panel() -> SyncPanel:
    panel = SyncPanel.__new__(SyncPanel)
    panel.sync_pairs = []
    panel.sync_worker = None
    panel.progress_bar = MagicMock()
    panel.sync_btn = MagicMock()
    panel.status_label = MagicMock()
    return panel


class TestSyncButtonRaceFix:
    """Button darf während _execute() nicht reaktiviert werden."""

    def _make_pair(self) -> SyncPair:
        return SyncPair(id="t1", name="Test", source="/src", target="/dst")

    def test_button_disabled_during_real_sync(self):
        """dry_run=False mit Actions: Button bleibt deaktiviert bis _on_sync_finished."""
        panel = _make_panel()
        panel._save_config = MagicMock()

        actions = [MagicMock()]
        panel._on_scan_finished(actions, dry_run=False, pair=self._make_pair())

        panel.sync_btn.setEnabled.assert_not_called(), (
            "sync_btn wurde schon nach dem Scan aktiviert, obwohl _execute() noch läuft"
        )
        panel.progress_bar.hide.assert_not_called(), (
            "progress_bar wurde versteckt obwohl _execute() noch läuft"
        )

    def test_button_enabled_on_no_actions(self):
        """Keine Aktionen: Button wird sofort reaktiviert."""
        panel = _make_panel()

        panel._on_scan_finished([], dry_run=False, pair=self._make_pair())

        panel.sync_btn.setEnabled.assert_called_with(True)

    def test_button_enabled_on_dry_run_with_actions(self):
        """dry_run=True: Button wird nach Scan reaktiviert (Vorschau-Dialog)."""
        panel = _make_panel()
        panel._show_preview_dialog = MagicMock()

        actions = [MagicMock()]
        panel._on_scan_finished(actions, dry_run=True, pair=self._make_pair())

        panel.sync_btn.setEnabled.assert_called_with(True)
        panel._show_preview_dialog.assert_called_once()
