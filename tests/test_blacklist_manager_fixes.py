"""
Bugfix-Tests: blacklist_manager.py BlacklistManager –
(1) _load() darf bei korrumpierter JSON-Datei (None, int) keinen TypeError werfen.
(2) import_from_file() darf keine 'nan'-Strings aus leeren Excel/CSV-Zellen übernehmen.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from modules.privacy.blacklist_manager import BlacklistManager


class TestBlacklistLoadRobustness:
    """_load() darf bei korrumpierter Datei nicht crashen."""

    def test_null_json_does_not_crash(self, tmp_path):
        bl_path = tmp_path / "blacklist.json"
        wl_path = tmp_path / "whitelist.json"
        bl_path.write_text("null", encoding="utf-8")
        wl_path.write_text("null", encoding="utf-8")

        mgr = BlacklistManager(config_dir=tmp_path)

        assert mgr.blacklist == []
        assert mgr.whitelist == []

    def test_integer_json_does_not_crash(self, tmp_path):
        bl_path = tmp_path / "blacklist.json"
        bl_path.write_text("42", encoding="utf-8")

        mgr = BlacklistManager(config_dir=tmp_path)

        assert mgr.blacklist == []

    def test_valid_list_still_loads(self, tmp_path):
        bl_path = tmp_path / "blacklist.json"
        bl_path.write_text(json.dumps(["secret", "password"]), encoding="utf-8")

        mgr = BlacklistManager(config_dir=tmp_path)

        assert set(mgr.blacklist) == {"secret", "password"}


class TestImportNanFix:
    """import_from_file() darf 'nan'-Strings nicht importieren."""

    def test_nan_skipped_from_txt_file(self, tmp_path):
        """TXT-Datei mit 'nan'-Zeile darf nicht zu Blacklist hinzugefügt werden."""
        txt_file = tmp_path / "terms.txt"
        txt_file.write_text("foo\nnan\nNaN\nbar\n", encoding="utf-8")

        mgr = BlacklistManager(config_dir=tmp_path)
        count = mgr.import_from_file(str(txt_file), target="blacklist")

        assert "nan" not in mgr.blacklist, "'nan' wurde trotz Fix importiert"
        assert "NaN" not in mgr.blacklist, "'NaN' wurde trotz Fix importiert"
        assert "foo" in mgr.blacklist
        assert "bar" in mgr.blacklist
        assert count == 2, f"Erwartet 2 importierte Begriffe, erhalten: {count}"

    def test_nan_skipped_from_csv(self, tmp_path):
        """CSV mit leerer Zeile (→ pandas NaN → 'nan') darf nicht importiert werden."""
        import pandas as pd

        csv_file = tmp_path / "terms.csv"
        # Leere Zeile erzeugt in pandas NaN, astype(str) macht daraus 'nan'
        csv_file.write_text("foo\n\nbar\n", encoding="utf-8")

        mgr = BlacklistManager(config_dir=tmp_path)
        count = mgr.import_from_file(str(csv_file), target="blacklist")

        assert "nan" not in mgr.blacklist, "'nan' aus leerem CSV-Feld wurde importiert"
        assert "foo" in mgr.blacklist
        assert "bar" in mgr.blacklist
        assert count == 2, f"Erwartet 2 importierte Begriffe, erhalten: {count}"
