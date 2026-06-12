from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1.5")

from PySide6 import QtCore, QtWidgets


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app import ExplorerProApp


SCREENSHOT_FILES = {
    "main": "main-window.png",
    "search": "search.png",
    "duplicates": "duplicates.png",
    "sync": "sync.png",
}


def _process_events(app: QtWidgets.QApplication, duration: float = 0.05) -> None:
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def _wait_for_worker(app: QtWidgets.QApplication, worker, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while worker is not None and worker.isRunning() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    if worker is not None and worker.isRunning():
        raise RuntimeError("Screenshot-Worker hat das Zeitlimit überschritten")


def _configure_runtime_dirs(temp_root: Path) -> Path:
    home_dir = temp_root / "home"
    home_dir.mkdir(parents=True, exist_ok=True)

    os.environ["HOME"] = str(home_dir)
    os.environ["USERPROFILE"] = str(home_dir)
    os.environ["APPDATA"] = str(home_dir / "AppData" / "Roaming")
    os.environ["LOCALAPPDATA"] = str(home_dir / "AppData" / "Local")
    os.environ["XDG_CONFIG_HOME"] = str(home_dir / ".config")
    os.environ["XDG_DATA_HOME"] = str(home_dir / ".local" / "share")

    settings_root = temp_root / "qsettings"
    settings_root.mkdir(parents=True, exist_ok=True)
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        str(settings_root),
    )
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.SystemScope,
        str(settings_root),
    )
    return home_dir


def _write_demo_configs(home_dir: Path) -> None:
    config_dir = home_dir / ".explorerpro"
    config_dir.mkdir(parents=True, exist_ok=True)

    apps = [
        {
            "name": "VS Code",
            "path": "C:/Programme/VSCode/Code.exe",
            "icon": "",
            "category": "Entwicklung",
            "description": "Editor für Projekte und Skripte",
            "arguments": "",
            "working_dir": "",
            "favorite": True,
        },
        {
            "name": "Berichtsmappe",
            "path": "C:/Tools/Berichte/Berichtsmappe.exe",
            "icon": "",
            "category": "Office",
            "description": "Projektberichte lokal prüfen",
            "arguments": "",
            "working_dir": "",
            "favorite": False,
        },
    ]
    sync_pairs = [
        {
            "id": "sync_docs",
            "name": "Dokumente zu Archiv",
            "source": "C:/Arbeitsbereich/Dokumente",
            "target": "D:/Archiv/Dokumente",
            "direction": "source_to_target",
            "conflict_resolution": "newer_wins",
            "exclude_patterns": ["*.tmp", "*.bak"],
            "include_hidden": False,
            "enabled": True,
            "last_sync": "2026-06-12T08:15:00",
        },
        {
            "id": "sync_exports",
            "name": "Exporte bidirektional",
            "source": "C:/Arbeitsbereich/Exporte",
            "target": "D:/Archiv/Exporte",
            "direction": "bidirectional",
            "conflict_resolution": "newer_wins",
            "exclude_patterns": ["Thumbs.db", ".DS_Store"],
            "include_hidden": False,
            "enabled": True,
            "last_sync": "2026-06-11T18:42:00",
        },
    ]

    (config_dir / "apps.json").write_text(
        json.dumps(apps, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (config_dir / "sync.json").write_text(
        json.dumps(sync_pairs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_demo_workspace(temp_root: Path) -> tuple[Path, Path, list[Path]]:
    workspace = temp_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    preview_file = workspace / "Überblick äöü.txt"
    preview_file.write_text(
        "Projektüberblick\nÄpfel, Öl und Übersicht bleiben lokal sichtbar.\n",
        encoding="utf-8",
    )

    report_dir = workspace / "Berichte"
    report_dir.mkdir(exist_ok=True)
    (report_dir / "Statusbericht.md").write_text(
        "# Status\n\nDatenschutzprüfung und Suchpfade sind vorbereitet.\n",
        encoding="utf-8",
    )

    duplicate_a = workspace / "Duplikat-A.txt"
    duplicate_b = workspace / "Duplikat-B.txt"
    duplicate_content = "gleicher inhalt\nmit umlauten äöü\n"
    duplicate_a.write_text(duplicate_content, encoding="utf-8")
    duplicate_b.write_text(duplicate_content, encoding="utf-8")

    return workspace, preview_file, [duplicate_a, duplicate_b]


def _save_widget(widget: QtWidgets.QWidget, target: Path) -> None:
    widget.show()
    widget.raise_()
    widget.activateWindow()
    app = QtWidgets.QApplication.instance()
    if app is not None:
        _process_events(app)
    pixmap = widget.grab()
    if pixmap.isNull():
        raise RuntimeError(f"Screenshot für {target.name} konnte nicht erzeugt werden")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(target)):
        raise RuntimeError(f"Screenshot {target} konnte nicht gespeichert werden")


def generate_store_screenshots(output_dir: Path) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="explorerpro-store-shots-") as temp_dir:
        temp_root = Path(temp_dir)
        home_dir = _configure_runtime_dirs(temp_root)
        _write_demo_configs(home_dir)
        workspace, preview_file, duplicates = _build_demo_workspace(temp_root)

        QtCore.QStandardPaths.setTestModeEnabled(True)
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setOrganizationName("ExplorerPro")
        app.setApplicationName("ExplorerPro Store Screenshots")

        window = ExplorerProApp()
        window.resize(1500, 920)
        window.show()
        _process_events(app)

        targets = [
            output_dir / SCREENSHOT_FILES["main"],
            output_dir / SCREENSHOT_FILES["search"],
            output_dir / SCREENSHOT_FILES["duplicates"],
            output_dir / SCREENSHOT_FILES["sync"],
        ]

        try:
            window.file_browser.navigate_to(str(workspace))
            window.preview_panel.show_preview(str(preview_file))
            window.statusBar().showMessage("ExplorerPro mit lokaler Vorschau", 0)
            _process_events(app)
            _save_widget(window, targets[0])

            search_panel = window.sidebar.search_panel
            search_panel.search_input.setText("überblick")
            search_panel.type_combo.setCurrentIndex(1)
            search_panel.show_results(
                [
                    {
                        "path": str(preview_file),
                        "name": preview_file.name,
                        "extension": ".txt",
                        "size": preview_file.stat().st_size,
                        "modified": None,
                        "snippet": "Projektüberblick mit Äpfeln und Übersicht",
                        "score": 1.0,
                        "category": "Dokumente",
                    },
                    {
                        "path": str(workspace / "Berichte" / "Statusbericht.md"),
                        "name": "Statusbericht.md",
                        "extension": ".md",
                        "size": (workspace / "Berichte" / "Statusbericht.md").stat().st_size,
                        "modified": None,
                        "snippet": "Datenschutzprüfung und Suchpfade sind vorbereitet.",
                        "score": 0.8,
                        "category": "Dokumente",
                    },
                ]
            )
            window.sidebar.switch_to_search()
            _process_events(app)
            _save_widget(window, targets[1])

            from modules.indexer.duplicate_finder import DuplicateFinderDialog

            duplicate_dialog = DuplicateFinderDialog(parent=window)
            duplicate_dialog.source_combo.setCurrentIndex(1)
            duplicate_dialog.folder_label.setText(str(workspace))
            duplicate_dialog.folder_label.setToolTip(str(workspace))
            duplicate_dialog.min_size_spin.setValue(0)
            duplicate_dialog._start_scan()
            _wait_for_worker(app, duplicate_dialog.scan_worker)
            _process_events(app)
            duplicate_dialog._select_all_duplicates()
            _process_events(app)
            _save_widget(duplicate_dialog, targets[2])
            duplicate_dialog.close()
            _process_events(app)

            sync_panel = window.sidebar.sync_panel
            if sync_panel.pair_list.count() > 0:
                sync_panel.pair_list.setCurrentRow(0)
            sync_panel.status_label.setText("2 Sync-Paare für Vorschau vorbereitet")
            window.sidebar.switch_to_sync()
            _process_events(app)
            _save_widget(window, targets[3])
        finally:
            window.close()
            _process_events(app)

    return targets


def main() -> None:
    targets = generate_store_screenshots(PROJECT_ROOT / "README" / "screenshots" / "store")
    for target in targets:
        print(target.name)


if __name__ == "__main__":
    main()
