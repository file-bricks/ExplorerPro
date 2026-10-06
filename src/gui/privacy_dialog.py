#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrivacySettingsDialog - Einstellungen der Datenschutz-Ampel

Bündelt alles, was die Ampel beeinflusst:
* Überwachung ein/aus, Hinweisdialoge, Ampel zurücksetzen
* eingebaute Erkennungsmuster und Suchoptionen
* frei editierbare Blacklist und Whitelist (inkl. Import/Export)
* einen Testbereich, der Eingaben mit der *noch nicht gespeicherten*
  Konfiguration prüft
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.ui_translator import NO_TRANSLATE
from modules.privacy.privacy_monitor import BUILTIN_PATTERNS
from modules.privacy.term_io import read_terms, write_terms
from translator import t

TERM_FILE_FILTER = "Textdateien (*.txt);;CSV-Dateien (*.csv);;Excel-Dateien (*.xlsx);;Alle Dateien (*)"

SEVERITY_LABELS = {"high": "hoch", "medium": "mittel", "low": "niedrig"}

STATUS_LABELS = {
    "green": "🟢 Grün – keine sensiblen Daten erkannt",
    "yellow": "🟡 Gelb – potenziell sensible Daten erkannt",
    "red": "🔴 Rot – sensible Daten erkannt",
    "gray": "⚪ Grau – Überwachung inaktiv",
}


class TermListEditor(QWidget):
    """Bearbeitbare Begriffsliste mit Filter, Import und Export."""

    changed = Signal()

    def __init__(self, list_name: str, hint: str, parent=None):
        super().__init__(parent)
        self._list_name = list_name
        layout = QVBoxLayout(self)

        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        add_row = QHBoxLayout()
        self.term_edit = QLineEdit()
        self.term_edit.setPlaceholderText("Neuen Begriff eingeben und Enter drücken")
        self.term_edit.setAccessibleName(t("Neuer Begriff für: {list}").format(list=list_name))
        self.term_edit.setToolTip("Mehrere Begriffe können durch Zeilenumbruch oder Semikolon getrennt werden.")
        self.term_edit.returnPressed.connect(self.add_from_input)
        add_row.addWidget(self.term_edit, 1)
        self.add_btn = QPushButton("Hinzufügen")
        self.add_btn.setAccessibleName(t("Begriff hinzufügen zu: {list}").format(list=list_name))
        self.add_btn.clicked.connect(self.add_from_input)
        add_row.addWidget(self.add_btn)
        layout.addLayout(add_row)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Liste filtern...")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setAccessibleName(t("Liste filtern: {list}").format(list=list_name))
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QListWidget()
        self.list_widget.setProperty(NO_TRANSLATE, True)  # Einträge sind Nutzerdaten
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setSortingEnabled(True)
        self.list_widget.setAccessibleName(t("Einträge: {list}").format(list=list_name))
        self.list_widget.setToolTip("Doppelklick bearbeitet einen Eintrag, Entf entfernt die Auswahl.")
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.list_widget, 1)
        QShortcut(QKeySequence.StandardKey.Delete, self.list_widget, activated=self.remove_selected)

        buttons = QHBoxLayout()
        self.remove_btn = QPushButton("Entfernen")
        self.remove_btn.setAccessibleName(t("Ausgewählte Einträge entfernen: {list}").format(list=list_name))
        self.remove_btn.clicked.connect(self.remove_selected)
        buttons.addWidget(self.remove_btn)

        self.import_btn = QPushButton("Importieren...")
        self.import_btn.setAccessibleName(t("Aus Datei importieren: {list}").format(list=list_name))
        self.import_btn.setToolTip("Begriffe aus TXT (eine Zeile pro Begriff), CSV oder Excel übernehmen")
        self.import_btn.clicked.connect(self.import_terms)
        buttons.addWidget(self.import_btn)

        self.export_btn = QPushButton("Exportieren...")
        self.export_btn.setAccessibleName(t("In Datei exportieren: {list}").format(list=list_name))
        self.export_btn.clicked.connect(self.export_terms)
        buttons.addWidget(self.export_btn)

        buttons.addStretch()

        self.clear_btn = QPushButton("Alle löschen")
        self.clear_btn.setAccessibleName(t("Liste vollständig leeren: {list}").format(list=list_name))
        self.clear_btn.clicked.connect(self.clear_terms)
        buttons.addWidget(self.clear_btn)
        layout.addLayout(buttons)

        self.count_label = QLabel()
        layout.addWidget(self.count_label)
        self._update_buttons()

    # ----- Daten -----

    def terms(self) -> list:
        return [self.list_widget.item(i).text().strip() for i in range(self.list_widget.count())
                if self.list_widget.item(i).text().strip()]

    def set_terms(self, terms) -> None:
        self.list_widget.blockSignals(True)
        try:
            self.list_widget.clear()
            for term in sorted({str(x).strip() for x in terms if str(x).strip()}, key=str.lower):
                self._append_item(term)
        finally:
            self.list_widget.blockSignals(False)
        self._update_buttons()

    def add_terms(self, terms) -> int:
        existing = {term.lower() for term in self.terms()}
        added = 0
        self.list_widget.blockSignals(True)
        try:
            for term in terms:
                term = str(term).strip()
                if term and term.lower() not in existing:
                    self._append_item(term)
                    existing.add(term.lower())
                    added += 1
        finally:
            self.list_widget.blockSignals(False)
        if added:
            self._apply_filter(self.filter_edit.text())
            self.changed.emit()
        self._update_buttons()
        return added

    def _append_item(self, term: str) -> None:
        item = QListWidgetItem(term)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)

    # ----- Aktionen -----

    def add_from_input(self) -> None:
        raw = self.term_edit.text()
        parts = [part.strip() for chunk in raw.splitlines() for part in chunk.split(";")]
        if self.add_terms(part for part in parts if part):
            self.term_edit.clear()
        self.term_edit.setFocus()

    def remove_selected(self) -> None:
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()}, reverse=True)
        if not rows:
            return
        for row in rows:
            self.list_widget.takeItem(row)
        self.changed.emit()
        self._update_buttons()

    def clear_terms(self) -> None:
        if self.list_widget.count() == 0:
            return
        reply = QMessageBox.question(
            self,
            t("Liste leeren"),
            t("Sollen wirklich alle {count} Einträge entfernt werden?").format(
                count=self.list_widget.count()
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.list_widget.clear()
        self.changed.emit()
        self._update_buttons()

    def import_terms(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("Begriffe importieren"), "", t(TERM_FILE_FILTER))
        if not path:
            return
        try:
            terms = read_terms(path)
        except Exception as exc:
            QMessageBox.warning(
                self, t("Import fehlgeschlagen"),
                t("Die Datei konnte nicht gelesen werden:") + f"\n{path}\n\n{exc}",
            )
            return
        added = self.add_terms(terms)
        QMessageBox.information(
            self, t("Import abgeschlossen"),
            t("{added} neue Begriffe übernommen ({total} in der Datei).").format(
                added=added, total=len(terms)
            ),
        )

    def export_terms(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("Begriffe exportieren"), f"{self._list_name.lower()}.txt", t(TERM_FILE_FILTER)
        )
        if not path:
            return
        try:
            write_terms(path, self.terms())
        except Exception as exc:
            QMessageBox.warning(
                self, t("Export fehlgeschlagen"),
                t("Die Datei konnte nicht geschrieben werden:") + f"\n{path}\n\n{exc}",
            )

    # ----- Anzeige -----

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if not item.text().strip():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.changed.emit()
        self._update_buttons()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _update_buttons(self) -> None:
        count = self.list_widget.count()
        self.remove_btn.setEnabled(bool(self.list_widget.selectedItems()))
        self.clear_btn.setEnabled(count > 0)
        self.export_btn.setEnabled(count > 0)
        self.count_label.setText(t("{count} Einträge").format(count=count))


class PrivacySettingsDialog(QDialog):
    """Dialog für Datenschutz-Einstellungen inkl. Black- und Whitelist."""

    def __init__(self, privacy_monitor, parent=None, settings=None):
        super().__init__(parent)
        self.privacy_monitor = privacy_monitor
        if settings is None:
            from core.settings_manager import SettingsManager

            settings = SettingsManager.instance()
        self.settings = settings
        self.setWindowTitle("Datenschutz-Einstellungen")
        self.setMinimumSize(560, 560)
        self.setAccessibleName("Datenschutz-Einstellungen")
        self.setAccessibleDescription(
            "Konfiguration von Erkennungsmustern, Blacklist, Whitelist und automatischer Bereinigung."
        )
        self._setup_ui()
        self._load_settings()

    # ===== Aufbau =====

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Datenschutz-Bereiche")
        self.tabs.addTab(self._build_detection_tab(), "Erkennung")

        self.blacklist_editor = TermListEditor(
            "Blacklist",
            "Begriffe der Blacklist gelten immer als sensibel (z. B. Namen, Projekt- oder "
            "Kundennummern). Sie färben die Ampel, sobald sie in der Zwischenablage auftauchen.",
        )
        self.blacklist_editor.changed.connect(self._update_stats)
        self.tabs.addTab(self.blacklist_editor, "Blacklist")

        self.whitelist_editor = TermListEditor(
            "Whitelist",
            "Begriffe der Whitelist werden nie als sensibel gemeldet – auch wenn ein Muster "
            "passt (z. B. die eigene Firmen-E-Mail-Adresse).",
        )
        self.whitelist_editor.changed.connect(self._update_stats)
        self.tabs.addTab(self.whitelist_editor, "Whitelist")

        self.tabs.addTab(self._build_test_tab(), "Testen")
        layout.addWidget(self.tabs, 1)

        # Statistik
        stats_group = QGroupBox("Statistik")
        stats_layout = QFormLayout(stats_group)
        self.blacklist_count_label = QLabel("0")
        self.whitelist_count_label = QLabel("0")
        self.active_patterns_label = QLabel("0")
        stats_layout.addRow("Blacklist-Einträge:", self.blacklist_count_label)
        stats_layout.addRow("Whitelist-Einträge:", self.whitelist_count_label)
        stats_layout.addRow("Aktive Patterns:", self.active_patterns_label)
        layout.addWidget(stats_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Speichern")
        ok_btn.setAccessibleName("Einstellungen speichern")
        ok_btn.setToolTip(t("Speichert die Datenschutz-Einstellungen (Enter)"))
        apply_btn = buttons.button(QDialogButtonBox.StandardButton.Apply)
        apply_btn.setText("Übernehmen")
        apply_btn.setAccessibleName("Einstellungen übernehmen")
        apply_btn.setToolTip("Änderungen anwenden, ohne den Dialog zu schließen")
        apply_btn.clicked.connect(self.apply_settings)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Abbrechen")
        cancel_btn.setAccessibleName("Abbrechen")
        cancel_btn.setToolTip(t("Verwirft Änderungen (Esc)"))
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_detection_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget()
        layout = QVBoxLayout(page)

        # Überwachung
        monitor_group = QGroupBox("Datenschutz-Ampel")
        monitor_layout = QVBoxLayout(monitor_group)
        self.monitor_enabled_cb = QCheckBox("Zwischenablage überwachen")
        self.monitor_enabled_cb.setAccessibleName("Zwischenablage überwachen")
        self.monitor_enabled_cb.setToolTip(t("Zwischenablage kontinuierlich auf schutzwürdige Muster überwachen"))
        monitor_layout.addWidget(self.monitor_enabled_cb)

        self.notifications_cb = QCheckBox("Warnhinweis bei roter Ampel als Dialog anzeigen")
        self.notifications_cb.setAccessibleName("Warnhinweis bei roter Ampel anzeigen")
        self.notifications_cb.setToolTip("Benachrichtigung bei erkannten Datenschutz-Mustern einblenden")
        monitor_layout.addWidget(self.notifications_cb)

        status_row = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setAccessibleName("Aktueller Ampelstatus")
        status_row.addWidget(self.status_label, 1)
        self.reset_btn = QPushButton("Ampel zurücksetzen")
        self.reset_btn.setAccessibleName("Ampel zurücksetzen")
        self.reset_btn.setToolTip("Setzt eine gelbe oder rote Ampel wieder auf Grün")
        self.reset_btn.clicked.connect(self._reset_status)
        status_row.addWidget(self.reset_btn)
        monitor_layout.addLayout(status_row)
        layout.addWidget(monitor_group)

        # Pattern-Gruppe
        pattern_group = QGroupBox("Erkennungsmuster")
        pattern_layout = QVBoxLayout(pattern_group)

        self.pattern_checks = {}
        for key, info in BUILTIN_PATTERNS.items():
            name = t(info['name'])
            description = t(info['description'])
            cb = QCheckBox(f"{name} – {description}")
            cb.setAccessibleName(f"{name} " + t("Erkennungsmuster"))
            cb.setAccessibleDescription(description)
            cb.setToolTip(t("Schweregrad: {severity}").format(
                severity=t(SEVERITY_LABELS.get(info['severity'], info['severity']))
            ))
            cb.toggled.connect(self._update_stats)
            self.pattern_checks[key] = cb
            pattern_layout.addWidget(cb)

        layout.addWidget(pattern_group)

        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QVBoxLayout(options_group)

        self.case_sensitive_cb = QCheckBox("Groß-/Kleinschreibung beachten")
        self.case_sensitive_cb.setAccessibleName("Groß- und Kleinschreibung beachten")
        self.case_sensitive_cb.setToolTip(t("Groß-/Kleinschreibung bei der Mustersuche berücksichtigen"))
        options_layout.addWidget(self.case_sensitive_cb)

        self.whole_words_cb = QCheckBox("Nur ganze Wörter")
        self.whole_words_cb.setAccessibleName("Nur ganze Wörter")
        self.whole_words_cb.setToolTip(t("Nur eigenständige Wörter als Treffer werten"))
        options_layout.addWidget(self.whole_words_cb)

        self.auto_clear_cb = QCheckBox("Clipboard bei ROT automatisch leeren")
        self.auto_clear_cb.setAccessibleName("Clipboard bei Alarm automatisch leeren")
        self.auto_clear_cb.setToolTip("Zwischenablage automatisch leeren, wenn sensible Daten erkannt werden")
        options_layout.addWidget(self.auto_clear_cb)

        layout.addWidget(options_group)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def _build_test_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel(
            "Text einfügen und prüfen, wie die Ampel mit den aktuellen (auch noch nicht "
            "gespeicherten) Einstellungen reagieren würde."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.test_input = QPlainTextEdit()
        self.test_input.setPlaceholderText("Beispieltext zum Prüfen...")
        self.test_input.setAccessibleName("Testtext für die Datenschutz-Prüfung")
        layout.addWidget(self.test_input, 1)
        self.test_btn = QPushButton("Prüfen")
        self.test_btn.setAccessibleName("Testtext prüfen")
        self.test_btn.clicked.connect(self.run_test)
        layout.addWidget(self.test_btn)
        self.test_result = QPlainTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setAccessibleName("Prüfergebnis")
        self.test_result.setMaximumHeight(140)
        layout.addWidget(self.test_result)
        return page

    # ===== Laden/Speichern =====

    def _load_settings(self):
        """Lädt aktuelle Einstellungen"""
        monitor = self.privacy_monitor
        for key, cb in self.pattern_checks.items():
            cb.setChecked(bool(monitor.pattern_enabled.get(key, False)))

        self.case_sensitive_cb.setChecked(bool(monitor.case_sensitive))
        self.whole_words_cb.setChecked(bool(monitor.whole_words))
        self.auto_clear_cb.setChecked(bool(monitor._auto_clear))
        self.monitor_enabled_cb.setChecked(bool(monitor.enabled))
        self.notifications_cb.setChecked(
            bool(self.settings.get("privacy", "show_notifications", True))
        )
        self.blacklist_editor.set_terms(monitor.blacklist)
        self.whitelist_editor.set_terms(monitor.whitelist)
        self._update_status_label()
        self._update_stats()

    def _patterns(self) -> dict:
        return {key: cb.isChecked() for key, cb in self.pattern_checks.items()}

    def apply_settings(self):
        """Überträgt alle Werte auf den Monitor und speichert sie dauerhaft."""
        monitor = self.privacy_monitor
        for key, enabled in self._patterns().items():
            monitor.pattern_enabled[key] = enabled
        monitor.case_sensitive = self.case_sensitive_cb.isChecked()
        monitor.whole_words = self.whole_words_cb.isChecked()
        monitor._auto_clear = self.auto_clear_cb.isChecked()
        monitor.set_lists(self.blacklist_editor.terms(), self.whitelist_editor.terms())

        enabled = self.monitor_enabled_cb.isChecked()
        if enabled != monitor.enabled:
            monitor.enabled = enabled
        else:
            monitor.recheck_clipboard()

        self.settings.set("privacy", "enable_clipboard_monitor", enabled)
        self.settings.set("privacy", "show_notifications", self.notifications_cb.isChecked())
        self.settings.set("privacy", "auto_block_sensitive", self.auto_clear_cb.isChecked())
        self.settings.save()
        self._update_status_label()

    def _save_and_close(self):
        """Speichert und schließt"""
        self.apply_settings()
        self.accept()

    # ===== Hilfen =====

    def _reset_status(self):
        self.privacy_monitor.reset_status()
        self._update_status_label()

    def _update_status_label(self):
        status = self.privacy_monitor.status
        self.status_label.setText(t("Status: {status}").format(status=t(STATUS_LABELS.get(status, status))))

    def _update_stats(self, *_):
        self.blacklist_count_label.setText(str(len(self.blacklist_editor.terms())))
        self.whitelist_count_label.setText(str(len(self.whitelist_editor.terms())))
        self.active_patterns_label.setText(str(sum(1 for v in self._patterns().values() if v)))

    def run_test(self):
        text = self.test_input.toPlainText()
        if not text.strip():
            self.test_result.setPlainText(t("Bitte zuerst einen Text eingeben."))
            return
        alert = self.privacy_monitor.preview_check(
            text,
            blacklist=self.blacklist_editor.terms(),
            whitelist=self.whitelist_editor.terms(),
            patterns=self._patterns(),
            case_sensitive=self.case_sensitive_cb.isChecked(),
            whole_words=self.whole_words_cb.isChecked(),
        )
        lines = [t("Ergebnis: {status}").format(status=t(STATUS_LABELS.get(alert.status.value, alert.status.value)))]
        if alert.detected_patterns:
            lines.append(t("Erkannt:"))
            lines.extend(f"  • {item}" for item in alert.detected_patterns)
            lines.append("")
            lines.append(t("Anonymisiert:"))
            lines.append(alert.anonymized_text)
        self.test_result.setPlainText("\n".join(lines))
