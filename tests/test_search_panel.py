from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from gui.sidebar.search_panel import SearchWorker


_APP = QApplication.instance() or QApplication([])


class RecordingIndex:
    def __init__(self) -> None:
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return []


def test_search_worker_forwards_content_only_filter() -> None:
    index = RecordingIndex()
    worker = SearchWorker(
        index,
        "begriff",
        {
            "extension": ".py",
            "category": "Code",
            "min_size": 10,
            "max_size": 100,
            "content_only": True,
            "limit": 7,
        },
    )

    worker.run()

    assert index.calls == [
        {
            "query": "begriff",
            "extension": ".py",
            "category": "Code",
            "min_size": 10,
            "max_size": 100,
            "content_only": True,
            "limit": 7,
        }
    ]


def test_search_panel_controls_expose_accessible_context() -> None:
    from gui.sidebar.search_panel import SearchPanel

    panel = SearchPanel()

    assert panel.search_input.accessibleName() == "Volltextsuche"
    assert "Mindestens zwei Zeichen" in panel.search_input.accessibleDescription()
    assert panel.advanced_btn.accessibleName() == "Erweiterte Suche öffnen"
    assert "erweiterten Suchfiltern" in panel.advanced_btn.accessibleDescription()
    assert panel.type_combo.accessibleName() == "Dateityp-Filter"
    assert "ausgewählte Kategorien" in panel.type_combo.accessibleDescription()
    assert panel.content_only_cb.accessibleName() == "Nur im Inhalt suchen"
    assert "nicht im Dateinamen" in panel.content_only_cb.accessibleDescription()
    assert panel.results_list.accessibleName() == "Suchergebnisse"
    assert "Pfeiltasten auswählen" in panel.results_list.accessibleDescription()
    assert panel.clear_btn.accessibleName() == "Suche löschen"
    assert "Suchfeld" in panel.clear_btn.accessibleDescription()
