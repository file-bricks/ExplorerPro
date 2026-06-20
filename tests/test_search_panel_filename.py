"""Regressionstest: SearchPanel._on_results_ready() liest 'filename' aus dem Result-Dict (Bug #8-8)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])


def test_search_panel_shows_filename_not_empty():
    """_on_results_ready muss 'filename' lesen (DB-Spalte), nicht 'name' (Bug #8-8)."""
    from gui.sidebar.search_panel import SearchPanel

    panel = SearchPanel()
    fake_results = [
        {
            "filename": "bericht.txt",
            "path": "/tmp/bericht.txt",
            "extension": ".txt",
            "size": 512,
            "modified": None,
            "snippet": "",
            "score": 0.0,
            "category": "Dokumente",
        }
    ]
    panel._on_results_ready(fake_results)

    assert panel.results_list.count() == 1
    item = panel.results_list.item(0)
    assert "bericht.txt" in item.text(), (
        f"'bericht.txt' muss im Anzeige-Text stehen, war: '{item.text()}'"
    )
