#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro - Hauptanwendung
Phase 5: Vollständige Integration aller Module
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QSettings, QTimer

from gui.main_window import MainWindow
from modules.privacy.privacy_monitor import PrivacyMonitor
from core.file_index import FileIndex
from core.settings_manager import SettingsManager
from translator import t

logging.basicConfig(level=logging.INFO)


class ExplorerProApp(MainWindow):
    """
    ExplorerPro Hauptanwendung
    Erbt von MainWindow und fügt App-spezifische Logik hinzu
    
    Integrierte Module:
    - PrivacyMonitor (AmpelTool)
    - FileIndex (Datenbankindizierung)
    - DuplicateFinder
    - AppsPanel (SoftwareCenter)
    - PromptsPanel (ProfiPrompt)
    - SyncPanel (ProSync)
    """

    def __init__(self):
        super().__init__()

        # Komponenten initialisieren
        self._init_privacy_monitor()
        self._init_file_index()

        # Einstellungen & Verbindungen
        self._load_settings()
        self._setup_connections()
        self._apply_settings(startup=True)

        # Keep every drive's start page ready, shortly after the window is up.
        QTimer.singleShot(800, lambda: self.file_browser.preload_roots(self.sidebar.drive_paths()))

        logging.info("ExplorerPro gestartet")

    def _init_privacy_monitor(self):
        """Initialisiert den Datenschutz-Monitor"""
        config_dir = Path.home() / ".explorerpro"
        self.privacy_monitor = PrivacyMonitor(config_dir)

        # Signale verbinden
        self.privacy_monitor.status_changed.connect(
            self.status_widget.set_privacy_status
        )
        self.privacy_monitor.warning.connect(self._on_privacy_warning)
        self.privacy_monitor.alert.connect(self._on_privacy_alert)

        # Monitor starten (sofern in den Einstellungen nicht deaktiviert)
        if SettingsManager.instance().get("privacy", "enable_clipboard_monitor", True):
            self.privacy_monitor.start()
        else:
            self.privacy_monitor.stop()
        logging.info("PrivacyMonitor initialisiert")

    def _init_file_index(self):
        """Initialisiert die Datei-Indizierung"""
        config_dir = Path.home() / ".explorerpro"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_path = config_dir / "fileindex.db"
        self.file_index = FileIndex(str(db_path))

        # Index an Sidebar und Metadaten-Panel (Tags/Notizen) weitergeben
        self.sidebar.set_file_index(self.file_index)
        self.preview_panel.metadata_panel.set_file_index(self.file_index)

        logging.info("FileIndex initialisiert")

    def _load_settings(self):
        """Lädt gespeicherte Einstellungen"""
        settings = QSettings()

        # Fenstergeometrie
        remember = SettingsManager.instance().get("general", "remember_window_size", True)
        geometry = settings.value("window/geometry") if remember else None
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1400, 900)
            self.center_on_screen()

        # Splitter-Größen
        for key, splitter in (
            ("splitter/main", self.main_splitter),
            ("splitter/right", self.right_splitter),
        ):
            saved = settings.value(key)
            try:
                sizes = [int(size) for size in saved]
            except (TypeError, ValueError):
                continue
            # Qt saves a hidden splitter child as size 0. Restoring that value
            # collapses the panel even though its View action remains checked.
            if len(sizes) == splitter.count() and all(size > 0 for size in sizes):
                splitter.setSizes(sizes)

        # Older sessions saved zero-width panels while their menu actions stayed checked.
        self._toggle_sidebar()
        self._toggle_preview()

    def _setup_connections(self):
        """Verbindet Signale und Slots"""
        # Sidebar -> Browser
        self.sidebar.folder_selected.connect(self.file_browser.navigate_to)
        self.sidebar.favorite_selected.connect(self.file_browser.navigate_to)

        # Sidebar Module -> StatusBar
        self.sidebar.app_launched.connect(self._on_app_launched)
        self.sidebar.prompt_copied.connect(self._on_prompt_copied)
        self.sidebar.sync_finished.connect(self._on_sync_finished)

        # Browser -> Preview
        self.file_browser.file_selected.connect(self.preview_panel.show_preview)
        self.file_browser.path_changed.connect(lambda _path: self.preview_panel.clear_preview())

        # Browser -> StatusBar
        self.file_browser.path_changed.connect(self.status_widget.update_path)
        self.file_browser.path_changed.connect(self.toolbar.set_path)
        self.file_browser.selection_changed.connect(
            lambda count: self.status_widget.update_file_count(
                self.file_browser.file_count, count
            )
        )

        # Search
        self.toolbar.search_requested.connect(self._on_search)

        # Navigation-Buttons
        self.toolbar.back_action.triggered.connect(self.file_browser.go_back)
        self.toolbar.forward_action.triggered.connect(self.file_browser.go_forward)
        self.toolbar.up_action.triggered.connect(self.file_browser.go_up)
        self.toolbar.path_edit.returnPressed.connect(
            lambda: self.file_browser.navigate_to(self.toolbar.path_edit.text())
        )

    def _on_search(self, query: str):
        """Suche ausführen"""
        if not query.strip():
            return

        # In Datenbank suchen
        results = self.file_index.search(query, limit=100)

        if results:
            self.statusBar().showMessage(
                t("{count} Treffer für: {query}").format(count=len(results), query=query), 5000
            )
            # Ergebnisse im SearchPanel anzeigen
            self.sidebar.search_panel.show_results(results)
            # Zum Such-Tab wechseln
            self.sidebar.switch_to_search()
        else:
            self.statusBar().showMessage(t("Keine Treffer für: {query}").format(query=query), 3000)

    def _on_privacy_warning(self, message: str):
        """Handler für Datenschutz-Warnungen"""
        self.statusBar().showMessage(f"⚠️ {message}", 5000)

    def _on_privacy_alert(self, alert):
        """Handler für Datenschutz-Alerts"""
        if alert.status.value != 'red':
            return
        if not SettingsManager.instance().get("privacy", "show_notifications", True):
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(t("Datenschutz-Warnung"))
        box.setText(alert.message)
        box.setInformativeText(
            t("Erkannt: {items}").format(items=", ".join(alert.detected_patterns))
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        settings_btn = box.addButton(t("Einstellungen..."), QMessageBox.ButtonRole.ActionRole)
        box.exec()
        if box.clickedButton() is settings_btn:
            self._show_privacy_settings()

    def _on_app_launched(self, path: str):
        """Handler für gestartete Apps"""
        self.statusBar().showMessage("🚀 " + t("App gestartet: {name}").format(name=Path(path).name), 3000)

    def _on_prompt_copied(self, content: str):
        """Handler für kopierte Prompts"""
        preview = content[:50] + "..." if len(content) > 50 else content
        self.statusBar().showMessage("📋 " + t("Prompt kopiert: {text}").format(text=preview), 3000)

    def _on_sync_finished(self, count: int):
        """Handler für abgeschlossene Synchronisation"""
        self.statusBar().showMessage(
            "🔄 " + t("Synchronisation abgeschlossen: {count} Dateien").format(count=count), 5000
        )

    def index_current_folder(self):
        """Indiziert den aktuellen Ordner"""
        from core.file_index import IndexWorker

        current_path = self.file_browser.current_path
        if not current_path:
            return

        # Worker starten
        self.index_worker = IndexWorker(self.file_index, current_path)
        self.index_worker.progress.connect(
            lambda current, total: self.statusBar().showMessage(
                t("Indiziere: {current}/{total}").format(current=current, total=total)
            )
        )
        self.index_worker.finished_indexing.connect(
            lambda n: self.statusBar().showMessage(
                "✅ " + t("{count} Dateien indiziert").format(count=n), 5000
            )
        )
        self.index_worker.start()

    def show_duplicate_finder(self):
        """Zeigt den Duplikate-Finder Dialog"""
        from modules.indexer.duplicate_finder import DuplicateFinderDialog

        dialog = DuplicateFinderDialog(self.file_index, self)
        dialog.exec()

    def show_apps_panel(self):
        """Wechselt zum Apps-Panel"""
        self.sidebar.switch_to_apps()

    def show_prompts_panel(self):
        """Wechselt zum Prompts-Panel"""
        self.sidebar.switch_to_prompts()

    def show_sync_panel(self):
        """Wechselt zum Sync-Panel"""
        self.sidebar.switch_to_sync()

    def center_on_screen(self):
        """Fenster zentrieren"""
        screen = self.screen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def closeEvent(self, event):
        """Einstellungen beim Schließen speichern"""
        # Privacy Monitor stoppen
        self.privacy_monitor.stop()

        # IndexWorker stoppen (override run(), kein exec() → cancel() statt quit())
        if hasattr(self, "index_worker") and self.index_worker and self.index_worker.isRunning():
            self.index_worker.cancel()
            self.index_worker.wait(3000)

        # SearchPanel-Worker stoppen (Child-Widget bekommt kein closeEvent → explizit stoppen)
        if hasattr(self, "sidebar") and self.sidebar:
            sp = self.sidebar.search_panel
            if sp.search_worker and sp.search_worker.isRunning():
                sp.search_worker.cancel()
                sp.search_worker.wait(3000)

        # Offene Tag-/Notiz-Eingaben sichern
        self.preview_panel.metadata_panel.save_user_data()

        # Einstellungen speichern
        settings = QSettings()
        if SettingsManager.instance().get("general", "remember_window_size", True):
            settings.setValue("window/geometry", self.saveGeometry())
        for key, splitter in (
            ("splitter/main", self.main_splitter),
            ("splitter/right", self.right_splitter),
        ):
            sizes = splitter.sizes()
            if all(size > 0 for size in sizes):
                settings.setValue(key, sizes)

        logging.info("ExplorerPro beendet")
        super().closeEvent(event)
