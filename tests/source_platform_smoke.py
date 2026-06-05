from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from app import ExplorerProApp
from core.platform_utils import get_system_open_command
from core.settings_manager import SettingsManager
from modules.indexer.duplicate_finder import DuplicateFinderDialog


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _process_events(app: QApplication, duration: float = 0.05) -> None:
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def _wait_for_worker(app: QApplication, worker, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while worker.isRunning() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not worker.isRunning(), "Duplicate scan timed out"


def main() -> None:
    app = _ensure_app()

    with tempfile.TemporaryDirectory(prefix="explorerpro-platform-smoke-") as tmp_dir:
        workspace = Path(tmp_dir)
        preview_file = workspace / "Überblick äöü.txt"
        preview_file.write_text("Äpfel\nÖl\nÜberblick", encoding="utf-8")

        duplicate_a = workspace / "Duplikat-A.txt"
        duplicate_b = workspace / "Duplikat-B.txt"
        duplicate_a.write_text("gleich\ninhalt\n", encoding="utf-8")
        duplicate_b.write_text("gleich\ninhalt\n", encoding="utf-8")

        window = ExplorerProApp()
        window.show()
        _process_events(app)

        assert window.windowTitle() == "ExplorerPro"
        window.file_browser.navigate_to(str(workspace))
        _process_events(app)
        assert Path(window.file_browser.current_path) == workspace

        window.preview_panel.show_preview(str(preview_file))
        _process_events(app)
        assert "Äpfel" in window.preview_panel.text_preview.toPlainText()

        window.sidebar.search_panel.show_results(
            [
                {
                    "path": str(preview_file),
                    "name": preview_file.name,
                    "extension": ".txt",
                    "size": preview_file.stat().st_size,
                    "modified": None,
                    "snippet": "Äpfel und Überblick",
                    "score": 1.0,
                    "category": "Dokumente",
                }
            ]
        )
        _process_events(app)
        assert window.sidebar.search_panel.results_list.count() == 1

        settings = SettingsManager()
        settings.set("appearance", "theme", "system")
        settings.save()
        assert settings.config_dir.exists()

        command = get_system_open_command(str(preview_file))
        if sys.platform == "darwin":
            assert command == ["open", str(preview_file)]
        elif sys.platform.startswith("win"):
            assert command is None
        else:
            assert command == ["xdg-open", str(preview_file)]

        dialog = DuplicateFinderDialog(parent=window)
        dialog.source_combo.setCurrentIndex(1)
        dialog.folder_label.setText(str(workspace))
        dialog.min_size_spin.setValue(0)
        dialog._start_scan()
        assert dialog.scan_worker is not None
        _wait_for_worker(app, dialog.scan_worker)
        _process_events(app)

        assert dialog.tree.topLevelItemCount() >= 1
        top_item = dialog.tree.topLevelItem(0)
        assert top_item is not None
        assert top_item.childCount() >= 2

        dialog.close()
        window.close()
        _process_events(app)

    print("source_platform_smoke: OK")


if __name__ == "__main__":
    main()
