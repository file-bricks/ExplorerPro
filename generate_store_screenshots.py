from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_SCALE_FACTOR", "1.5")

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap


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


def _force_native_platform() -> None:
    """Entfernt eine geerbte offscreen-Plattform VOR der QApplication-Erzeugung.

    Unter QT_QPA_PLATFORM=offscreen rendert Qt auf Windows keine echten
    Glyphen -- jede Glyphe wird als .notdef-Kaestchen (Tofu) gerastert; ein
    Screenshot per grab() sieht dann gueltig aus, ist aber unbrauchbar (Fund
    aus der Store-Welle 1, behoben u.a. in SoftwareCenter/ProfiPrompt/
    CleanMarkdown/LitZen/ProSync/PromptBoard/Klangpult/PDFtoPDFocr -- dieses
    Skript setzte denselben Fehler bislang per `setdefault` selbst).
    """
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        del os.environ["QT_QPA_PLATFORM"]


def _render_probe_char(app: QtWidgets.QApplication, ch: str) -> bytes:
    pm = QPixmap(48, 48)
    pm.fill(Qt.GlobalColor.white)
    p = QPainter(pm)
    p.setFont(app.font())
    p.drawText(pm.rect(), Qt.AlignCenter, ch)
    p.end()
    return bytes(pm.toImage().constBits())


def _assert_font_rendering(app: QtWidgets.QApplication) -> None:
    """Bricht ab statt still ein Tofu-Screenshot-Set zu erzeugen."""
    platform = QtWidgets.QApplication.platformName()
    if platform == "offscreen":
        raise RuntimeError(
            "Qt laeuft unter 'offscreen' -- Screenshots waeren Tofu (Kaestchen "
            "statt Text). QT_QPA_PLATFORM=offscreen nicht setzen."
        )
    probes = ["A", "B", "g", "8", "M"]
    renders = [_render_probe_char(app, ch) for ch in probes]
    blank = _render_probe_char(app, " ")
    distinct = len(set(renders))
    non_blank = sum(1 for r in renders if r != blank)
    if not (distinct >= 3 and non_blank >= len(probes) - 1):
        raise RuntimeError(
            f"Font-Rendering-Selbsttest fehlgeschlagen (Plattform '{platform}'): "
            "gerenderte Glyphen sind nicht unterscheidbar (Tofu-Verdacht). "
            "Abbruch, um kein defektes Screenshot-Set zu erzeugen."
        )


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
        _force_native_platform()
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setOrganizationName("ExplorerPro")
        app.setApplicationName("ExplorerPro Store Screenshots")
        _assert_font_rendering(app)

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
            window.sidebar.switch_to_search()
            # setText()/setCurrentIndex() above start the real (debounced)
            # SearchWorker against the temp FileIndex asynchronously. If
            # show_results() below ran first, that background worker could
            # finish afterwards and overwrite the injected demo results with
            # a real (empty) 0-hits result -- exactly what happened before
            # this fix: the demo query has no built FTS index behind it, so
            # the async real search always resolves to "0 Ergebnisse". Let
            # any pending async search finish first, then cancel it, so the
            # manually injected demo results are guaranteed to be the last
            # (and therefore visible) state before the screenshot.
            _process_events(app)
            if search_panel.search_timer.isActive():
                search_panel.search_timer.stop()
            if search_panel.search_worker and search_panel.search_worker.isRunning():
                search_panel.search_worker.cancel()
                search_panel.search_worker.wait()
            search_panel.show_results(
                [
                    {
                        "path": str(preview_file),
                        # SearchPanel._on_results_ready() liest den DB-Spaltennamen
                        # "filename", nicht "name" -- mit "name" blieb die Liste
                        # leer und der Screenshot zeigte "0 Ergebnisse" trotz
                        # zweier übergebener Treffer.
                        "filename": preview_file.name,
                        "extension": ".txt",
                        "size": preview_file.stat().st_size,
                        "modified": None,
                        "snippet": "Projektüberblick mit Äpfeln und Übersicht",
                        "score": 1.0,
                        "category": "Dokumente",
                    },
                    {
                        "path": str(workspace / "Berichte" / "Statusbericht.md"),
                        "filename": "Statusbericht.md",
                        "extension": ".md",
                        "size": (workspace / "Berichte" / "Statusbericht.md").stat().st_size,
                        "modified": None,
                        "snippet": "Datenschutzprüfung und Suchpfade sind vorbereitet.",
                        "score": 0.8,
                        "category": "Dokumente",
                    },
                ]
            )
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
