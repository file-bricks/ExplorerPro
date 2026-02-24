#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro - Hauptanwendung
Phase 5: Vollständige Integration aller Module
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QSettings

from gui.main_window import MainWindow
from modules.privacy.privacy_monitor import PrivacyMonitor
from core.file_index import FileIndex

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
        
        # Monitor starten
        self.privacy_monitor.start()
        logging.info("PrivacyMonitor initialisiert")
    
    def _init_file_index(self):
        """Initialisiert die Datei-Indizierung"""
        config_dir = Path.home() / ".explorerpro"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_path = config_dir / "fileindex.db"
        self.file_index = FileIndex(str(db_path))
        
        # Index an Sidebar weitergeben
        self.sidebar.set_file_index(self.file_index)
        
        logging.info("FileIndex initialisiert")
        
    def _load_settings(self):
        """Lädt gespeicherte Einstellungen"""
        settings = QSettings()
        
        # Fenstergeometrie
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1400, 900)
            self.center_on_screen()
        
        # Splitter-Größen
        main_sizes = settings.value("splitter/main")
        if main_sizes:
            self.main_splitter.setSizes([int(s) for s in main_sizes])
        
        right_sizes = settings.value("splitter/right")
        if right_sizes:
            self.right_splitter.setSizes([int(s) for s in right_sizes])
    
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
                f"{len(results)} Treffer für: {query}", 5000
            )
            # Ergebnisse im SearchPanel anzeigen
            self.sidebar.search_panel.show_results(results)
            # Zum Such-Tab wechseln
            self.sidebar.switch_to_search()
        else:
            self.statusBar().showMessage(f"Keine Treffer für: {query}", 3000)
    
    def _on_privacy_warning(self, message: str):
        """Handler für Datenschutz-Warnungen"""
        self.statusBar().showMessage(f"⚠️ {message}", 5000)
    
    def _on_privacy_alert(self, alert):
        """Handler für Datenschutz-Alerts"""
        if alert.status.value == 'red':
            QMessageBox.warning(
                self,
                "Datenschutz-Warnung",
                f"{alert.message}\n\nErkannt: {', '.join(alert.detected_patterns)}"
            )
    
    def _on_app_launched(self, path: str):
        """Handler für gestartete Apps"""
        self.statusBar().showMessage(f"🚀 App gestartet: {Path(path).name}", 3000)
    
    def _on_prompt_copied(self, content: str):
        """Handler für kopierte Prompts"""
        preview = content[:50] + "..." if len(content) > 50 else content
        self.statusBar().showMessage(f"📋 Prompt kopiert: {preview}", 3000)
    
    def _on_sync_finished(self, count: int):
        """Handler für abgeschlossene Synchronisation"""
        self.statusBar().showMessage(f"🔄 Synchronisation abgeschlossen: {count} Dateien", 5000)
    
    def index_current_folder(self):
        """Indiziert den aktuellen Ordner"""
        from core.file_index import IndexWorker
        
        current_path = self.file_browser.current_path
        if not current_path:
            return
        
        # Worker starten
        self.index_worker = IndexWorker(self.file_index, current_path)
        self.index_worker.progress.connect(
            lambda c, t: self.statusBar().showMessage(f"Indiziere: {c}/{t}")
        )
        self.index_worker.finished_indexing.connect(
            lambda n: self.statusBar().showMessage(f"✅ {n} Dateien indiziert", 5000)
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
        
        # Einstellungen speichern
        settings = QSettings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("splitter/main", self.main_splitter.sizes())
        settings.setValue("splitter/right", self.right_splitter.sizes())
        
        logging.info("ExplorerPro beendet")
        super().closeEvent(event)
