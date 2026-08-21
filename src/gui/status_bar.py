#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StatusBar - Statusleiste mit Datenschutz-Ampel
"""

from PySide6.QtWidgets import (
    QStatusBar, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


class PrivacyIndicator(QLabel):
    """
    Ampel-Anzeige für Datenschutz-Status
    Basiert auf AmpelTool
    """
    
    clicked = Signal()
    
    # Status-Farben
    COLORS = {
        'green': '#2ecc71',   # Sicher
        'yellow': '#f1c40f',  # Warnung
        'red': '#e74c3c',     # Blockiert
        'gray': '#95a5a6',    # Inaktiv
    }
    
    TOOLTIPS = {
        'green': '🟢 Datenschutz: Alles OK\nClipboard ist sicher',
        'yellow': '🟡 Datenschutz: Warnung\nPotenziell sensible Daten erkannt',
        'red': '🔴 Datenschutz: Blockiert!\nSensible Daten wurden blockiert',
        'gray': '⚪ Datenschutz-Monitor inaktiv',
    }
    
    DESCRIPTIONS = {
        'green': 'Datenschutz-Status: Grün. Zwischenablage ist sicher und unbedenklich.',
        'yellow': 'Datenschutz-Status: Gelb. Warnung vor potenziell sensiblen Daten in der Zwischenablage.',
        'red': 'Datenschutz-Status: Rot. Sensible Daten wurden im Zwischenspeicher blockiert.',
        'gray': 'Datenschutz-Status: Grau. Datenschutz-Monitor ist inaktiv.',
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = 'gray'
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Datenschutz-Status")
        self.set_status('green')
    
    def set_status(self, status: str):
        """Setzt den Ampel-Status"""
        if status not in self.COLORS:
            status = 'gray'
        
        self._status = status
        color = self.COLORS[status]
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid {self._darken(color)};
            }}
            QLabel:focus {{
                border: 2px solid #0078D7;
            }}
        """)
        
        self.setToolTip(self.TOOLTIPS[status])
        self.setAccessibleName("Datenschutz-Status")
        self.setAccessibleDescription(self.DESCRIPTIONS.get(status, self.TOOLTIPS[status]))
    
    def _darken(self, hex_color: str) -> str:
        """Dunkelt eine Farbe ab"""
        color = QColor(hex_color)
        color = color.darker(120)
        return color.name()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    @property
    def status(self) -> str:
        return self._status


class StatusBarWidget(QStatusBar):
    """
    Erweiterte Statusleiste mit:
    - Datei-Anzahl
    - Speicherplatz
    - Datenschutz-Ampel
    - Sync-Status
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        # Linker Bereich: Pfad und Datei-Count
        self.path_label = QLabel("Bereit")
        self.path_label.setAccessibleName("Aktueller Ordnerpfad")
        self.path_label.setAccessibleDescription("Zeigt das aktuelle Arbeitsverzeichnis oder den Systemstatus an.")
        self.path_label.setToolTip("Aktueller Pfad / Status")
        self.addWidget(self.path_label, 1)
        
        # Trennlinie
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        self.addWidget(sep1)
        
        # Datei-Count
        self.file_count_label = QLabel("0 Dateien")
        self.file_count_label.setAccessibleName("Elementanzahl")
        self.file_count_label.setAccessibleDescription("Anzahl der Dateien und Ordner sowie aktuelle Elementauswahl.")
        self.file_count_label.setToolTip("Elemente im aktuellen Verzeichnis")
        self.addWidget(self.file_count_label)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        self.addWidget(sep2)
        
        # Speicherplatz
        self.space_label = QLabel("0 GB")
        self.space_label.setAccessibleName("Speicherplatzanzeige")
        self.space_label.setAccessibleDescription("Belegter oder berechneter Speicherplatz der Dateien.")
        self.space_label.setToolTip("Speichergröße der Elemente")
        self.addWidget(self.space_label)
        
        # Permanenter Bereich (rechts)
        
        # Sync-Status
        self.sync_label = QLabel("✓")
        self.sync_label.setToolTip("Synchronisierung: Aktuell")
        self.sync_label.setAccessibleName("Synchronisationsstatus")
        self.sync_label.setAccessibleDescription("Status der Dateisynchronisierung (aktuell oder aktiv).")
        self.addPermanentWidget(self.sync_label)
        
        # Datenschutz-Ampel
        self.privacy_indicator = PrivacyIndicator()
        self.privacy_indicator.clicked.connect(self._on_privacy_clicked)
        self.addPermanentWidget(self.privacy_indicator)
    
    def update_path(self, path: str):
        """Aktualisiert den Pfad"""
        full_path = path
        if len(path) > 60:
            path = "..." + path[-57:]
        self.path_label.setText(f"📁 {path}")
        self.path_label.setToolTip(f"Aktueller Pfad: {full_path}")
        self.path_label.setAccessibleDescription(f"Aktueller Ordnerpfad: {full_path}")
    
    def update_file_count(self, count: int, selected: int = 0):
        """Aktualisiert die Datei-Anzahl"""
        if selected > 0:
            text = f"{selected} von {count} ausgewählt"
        else:
            text = f"{count} Elemente"
        self.file_count_label.setText(text)
        self.file_count_label.setToolTip(text)
        self.file_count_label.setAccessibleDescription(text)
    
    def update_space(self, used_bytes: int):
        """Aktualisiert die Speicheranzeige"""
        gb = used_bytes / (1024 ** 3)
        if gb < 1:
            mb = used_bytes / (1024 ** 2)
            text = f"💾 {mb:.1f} MB"
        else:
            text = f"💾 {gb:.2f} GB"
        self.space_label.setText(text)
        self.space_label.setToolTip(f"Belegter Speicher: {text}")
        self.space_label.setAccessibleDescription(f"Speicherplatzanzeige: {text}")
    
    def set_privacy_status(self, status: str):
        """Setzt den Datenschutz-Status"""
        self.privacy_indicator.set_status(status)
    
    def set_sync_status(self, syncing: bool):
        """Setzt den Sync-Status"""
        if syncing:
            self.sync_label.setText("🔄")
            self.sync_label.setToolTip("Synchronisierung läuft...")
            self.sync_label.setAccessibleDescription("Synchronisation wird derzeit im Hintergrund ausgeführt.")
        else:
            self.sync_label.setText("✓")
            self.sync_label.setToolTip("Synchronisierung: Aktuell")
            self.sync_label.setAccessibleDescription("Synchronisation ist aktuell und auf dem neuesten Stand.")
    
    def _on_privacy_clicked(self):
        """Handler für Klick auf Ampel"""
        status = self.privacy_indicator.status
        # TODO: Privacy-Details-Dialog öffnen
        self.showMessage(f"Datenschutz-Status: {status.upper()}", 3000)
