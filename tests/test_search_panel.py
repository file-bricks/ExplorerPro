from __future__ import annotations

import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gui.sidebar.search_panel import SearchWorker


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
