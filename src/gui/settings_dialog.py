#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SettingsDialog - Einstellungsfenster für ExplorerPro

Bearbeitet die Sektionen des SettingsManager (general, index, preview,
privacy, appearance) und schreibt sie beim Bestätigen in die
settings.json des Benutzerprofils.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
    QCheckBox, QComboBox, QSpinBox, QLineEdit, QPushButton, QLabel,
    QDialogButtonBox, QFileDialog
)

from core.settings_manager import SettingsManager
from translator import TranslationSystem


class SettingsDialog(QDialog):
    """Dialog für die Anwendungseinstellungen."""

    THEMES = [
        ("system", "Systemvorgabe"),
        ("light", "Hell"),
        ("dark", "Dunkel"),
    ]

    def __init__(self, parent=None, settings: SettingsManager = None):
        super().__init__(parent)
        self.settings = settings or SettingsManager.instance()
        self.setWindowTitle("Einstellungen")
        self.setMinimumWidth(520)
        self.setAccessibleName("Einstellungen")
        self.setAccessibleDescription(
            "Bearbeitet Allgemein-, Index-, Vorschau-, Datenschutz- und "
            "Darstellungseinstellungen von ExplorerPro."
        )
        self._setup_ui()
        self._load_settings()

    # ===== Aufbau =====

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Einstellungsbereiche")
        self.tabs.addTab(self._build_general_tab(), "Allgemein")
        self.tabs.addTab(self._build_index_tab(), "Index")
        self.tabs.addTab(self._build_preview_tab(), "Vorschau")
        self.tabs.addTab(self._build_privacy_tab(), "Datenschutz")
        self.tabs.addTab(self._build_appearance_tab(), "Darstellung")
        layout.addWidget(self.tabs)

        hint = QLabel(
            "Die Einstellungen werden in der Konfigurationsdatei des "
            "Benutzerprofils gespeichert."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Übernehmen")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        path_row = QHBoxLayout()
        self.start_folder_edit = QLineEdit()
        self.start_folder_edit.setPlaceholderText("Leer = Benutzerordner")
        self.start_folder_edit.setAccessibleName("Startordner")
        self.start_folder_edit.setAccessibleDescription("Standardordner, der beim Start der Anwendung geöffnet wird.")
        self.start_folder_edit.setToolTip("Standardverzeichnis beim Programmstart")
        path_row.addWidget(self.start_folder_edit)
        browse_btn = QPushButton("Auswählen...")
        browse_btn.setAccessibleName("Startordner auswählen")
        browse_btn.setToolTip("Dateidialog zur Auswahl des Startordners öffnen")
        browse_btn.clicked.connect(self._choose_start_folder)
        path_row.addWidget(browse_btn)
        form.addRow("Startordner:", path_row)

        self.language_cb = QComboBox()
        self.language_cb.setAccessibleName("Sprachauswahl")
        self.language_cb.setAccessibleDescription("Auswahl der Benutzeroberflächensprache.")
        self.language_cb.setToolTip("Programmsprache für Menüs und Dialoge")
        for code, display in TranslationSystem.get_language_display_names().items():
            self.language_cb.addItem(display, code)
        form.addRow("Sprache:", self.language_cb)

        self.show_hidden_cb = QCheckBox("Versteckte Dateien anzeigen")
        self.show_hidden_cb.setAccessibleName("Versteckte Dateien anzeigen")
        self.show_hidden_cb.setToolTip("Versteckte Dateien und Systemordner im Dateibrowser anzeigen")
        form.addRow(self.show_hidden_cb)

        self.confirm_delete_cb = QCheckBox("Vor dem Löschen nachfragen")
        self.confirm_delete_cb.setAccessibleName("Vor dem Löschen nachfragen")
        self.confirm_delete_cb.setToolTip("Sicherheitsabfrage vor dem unwiderruflichen Löschen einblenden")
        form.addRow(self.confirm_delete_cb)

        self.remember_size_cb = QCheckBox("Fenstergröße merken")
        self.remember_size_cb.setAccessibleName("Fenstergröße merken")
        self.remember_size_cb.setToolTip("Fenstergröße und Position beim Beenden speichern")
        form.addRow(self.remember_size_cb)

        return page

    def _build_index_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.auto_index_cb = QCheckBox("Ordner automatisch indizieren")
        self.auto_index_cb.setAccessibleName("Ordner automatisch indizieren")
        self.auto_index_cb.setToolTip("Verzeichnisse im Hintergrund automatisch für die Schnellsuche indizieren")
        form.addRow(self.auto_index_cb)

        self.index_startup_cb = QCheckBox("Beim Programmstart indizieren")
        self.index_startup_cb.setAccessibleName("Beim Programmstart indizieren")
        self.index_startup_cb.setToolTip("Indexprüfung direkt beim Start von ExplorerPro durchführen")
        form.addRow(self.index_startup_cb)

        self.max_file_size_spin = QSpinBox()
        self.max_file_size_spin.setRange(1, 10000)
        self.max_file_size_spin.setSuffix(" MB")
        self.max_file_size_spin.setAccessibleName("Maximale Dateigröße für den Index")
        self.max_file_size_spin.setToolTip("Dateien über dieser Größe werden nicht indiziert")
        form.addRow("Maximale Dateigröße:", self.max_file_size_spin)

        return page

    def _build_preview_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.show_preview_cb = QCheckBox("Vorschaufenster anzeigen")
        self.show_preview_cb.setAccessibleName("Vorschaufenster anzeigen")
        self.show_preview_cb.setToolTip("Vorschauleiste auf der rechten Seite einblenden")
        form.addRow(self.show_preview_cb)

        self.preview_images_cb = QCheckBox("Bilder in der Vorschau anzeigen")
        self.preview_images_cb.setAccessibleName("Bilder in der Vorschau anzeigen")
        self.preview_images_cb.setToolTip("Miniaturansichten für Grafikdateien rendern")
        form.addRow(self.preview_images_cb)

        self.preview_pdfs_cb = QCheckBox("PDF-Dateien in der Vorschau anzeigen")
        self.preview_pdfs_cb.setAccessibleName("PDF-Dateien in der Vorschau anzeigen")
        self.preview_pdfs_cb.setToolTip("Erste Seite von PDF-Dokumenten im Vorschaufenster darstellen")
        form.addRow(self.preview_pdfs_cb)

        self.preview_code_cb = QCheckBox("Quelltext in der Vorschau anzeigen")
        self.preview_code_cb.setAccessibleName("Quelltext in der Vorschau anzeigen")
        self.preview_code_cb.setToolTip("Syntaxhervorhebung für Quellcode und Textdateien nutzen")
        form.addRow(self.preview_code_cb)

        self.max_preview_spin = QSpinBox()
        self.max_preview_spin.setRange(1, 1000)
        self.max_preview_spin.setSuffix(" MB")
        self.max_preview_spin.setAccessibleName("Maximale Dateigröße für die Vorschau")
        self.max_preview_spin.setToolTip("Maximale Dateigröße für generierte Vorschauen")
        form.addRow("Maximale Vorschaugröße:", self.max_preview_spin)

        return page

    def _build_privacy_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.clipboard_monitor_cb = QCheckBox("Zwischenablage überwachen")
        self.clipboard_monitor_cb.setAccessibleName("Zwischenablage überwachen")
        self.clipboard_monitor_cb.setToolTip("Zwischenablage kontinuierlich auf schutzwürdige Muster überwachen")
        form.addRow(self.clipboard_monitor_cb)

        self.auto_block_cb = QCheckBox("Sensible Inhalte automatisch blockieren")
        self.auto_block_cb.setAccessibleName("Sensible Inhalte automatisch blockieren")
        self.auto_block_cb.setToolTip("Kopieren hochsensibler Daten wie Passwörter und API-Keys blockieren")
        form.addRow(self.auto_block_cb)

        self.notifications_cb = QCheckBox("Hinweise anzeigen")
        self.notifications_cb.setAccessibleName("Hinweise anzeigen")
        self.notifications_cb.setToolTip("Benachrichtigung bei erkannten Datenschutz-Mustern einblenden")
        form.addRow(self.notifications_cb)

        note = QLabel(
            "Erkennungsmuster werden unter Tools, Datenschutz-Einstellungen "
            "gepflegt."
        )
        note.setWordWrap(True)
        form.addRow(note)

        return page

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName("Farbschema")
        self.theme_combo.setToolTip("Farbschema der Benutzeroberfläche")
        for value, label in self.THEMES:
            self.theme_combo.addItem(label, value)
        form.addRow("Farbschema:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 32)
        self.font_size_spin.setAccessibleName("Schriftgröße")
        self.font_size_spin.setToolTip("Basisschriftgröße in Punkten")
        form.addRow("Schriftgröße:", self.font_size_spin)

        self.icon_size_spin = QSpinBox()
        self.icon_size_spin.setRange(12, 64)
        self.icon_size_spin.setSuffix(" px")
        self.icon_size_spin.setAccessibleName("Symbolgröße")
        self.icon_size_spin.setToolTip("Größe der Dateisymbole in Pixeln")
        form.addRow("Symbolgröße:", self.icon_size_spin)

        return page

    # ===== Laden und Speichern =====

    def _choose_start_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Startordner auswählen", self.start_folder_edit.text()
        )
        if folder:
            self.start_folder_edit.setText(folder)

    def _load_settings(self):
        """Überträgt die gespeicherten Werte in die Bedienelemente."""
        get = self.settings.get

        self.start_folder_edit.setText(get("general", "start_folder", "") or "")
        self.show_hidden_cb.setChecked(bool(get("general", "show_hidden_files", False)))
        self.confirm_delete_cb.setChecked(bool(get("general", "confirm_delete", True)))
        self.remember_size_cb.setChecked(bool(get("general", "remember_window_size", True)))

        self.auto_index_cb.setChecked(bool(get("index", "auto_index", True)))
        self.index_startup_cb.setChecked(bool(get("index", "index_on_startup", False)))
        self.max_file_size_spin.setValue(int(get("index", "max_file_size_mb", 100)))

        self.show_preview_cb.setChecked(bool(get("preview", "show_preview", True)))
        self.preview_images_cb.setChecked(bool(get("preview", "preview_images", True)))
        self.preview_pdfs_cb.setChecked(bool(get("preview", "preview_pdfs", True)))
        self.preview_code_cb.setChecked(bool(get("preview", "preview_code", True)))
        self.max_preview_spin.setValue(int(get("preview", "max_preview_size_mb", 10)))

        self.clipboard_monitor_cb.setChecked(
            bool(get("privacy", "enable_clipboard_monitor", True))
        )
        self.auto_block_cb.setChecked(bool(get("privacy", "auto_block_sensitive", True)))
        self.notifications_cb.setChecked(bool(get("privacy", "show_notifications", True)))

        theme = get("appearance", "theme", "system")
        index = self.theme_combo.findData(theme)
        self.theme_combo.setCurrentIndex(index if index >= 0 else 0)
        self.font_size_spin.setValue(int(get("appearance", "font_size", 10)))
        self.icon_size_spin.setValue(int(get("appearance", "icon_size", 24)))

    def collect_settings(self) -> dict:
        """Liest die Bedienelemente aus und gibt die Werte als Dict zurück."""
        return {
            "general": {
                "start_folder": self.start_folder_edit.text().strip(),
                "show_hidden_files": self.show_hidden_cb.isChecked(),
                "confirm_delete": self.confirm_delete_cb.isChecked(),
                "remember_window_size": self.remember_size_cb.isChecked(),
            },
            "index": {
                "auto_index": self.auto_index_cb.isChecked(),
                "index_on_startup": self.index_startup_cb.isChecked(),
                "max_file_size_mb": self.max_file_size_spin.value(),
            },
            "preview": {
                "show_preview": self.show_preview_cb.isChecked(),
                "preview_images": self.preview_images_cb.isChecked(),
                "preview_pdfs": self.preview_pdfs_cb.isChecked(),
                "preview_code": self.preview_code_cb.isChecked(),
                "max_preview_size_mb": self.max_preview_spin.value(),
            },
            "privacy": {
                "enable_clipboard_monitor": self.clipboard_monitor_cb.isChecked(),
                "auto_block_sensitive": self.auto_block_cb.isChecked(),
                "show_notifications": self.notifications_cb.isChecked(),
            },
            "appearance": {
                "theme": self.theme_combo.currentData(),
                "font_size": self.font_size_spin.value(),
                "icon_size": self.icon_size_spin.value(),
            },
        }

    def apply_to_settings(self):
        """Schreibt die Werte in den SettingsManager und speichert sie."""
        for section, values in self.collect_settings().items():
            for key, value in values.items():
                self.settings.set(section, key, value)
        self.settings.save()

    def _save_and_close(self):
        self.apply_to_settings()
        self.accept()
