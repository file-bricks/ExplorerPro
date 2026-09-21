#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
batch_rename_dialog.py - Interaktiver Dialog für Mehrfachumbenennungen

Funktionen:
- Tabellen-Live-Vorschau (Originalname, Neuer Name, Status)
- Suchen & Ersetzen mit optionaler Regex-Unterstützung
- Präfix & Suffix
- Nummerierung (Start, Schritt, Stellen/Padding)
- Groß-/Kleinschreibung (lower, upper, title, sentence)
- Dateiendung ändern
- Kollisionserkennung & Warnungen in Echtzeit
- Rollback-Option für direkte Rückgängig-Aktion
"""

import os
from typing import List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QMessageBox, QAbstractItemView
)
from PySide6.QtGui import QColor, QBrush

from core.batch_rename_service import (
    RenameRules, RenameItem, generate_preview, execute_rename, rollback_rename
)
from translator import t


class BatchRenameDialog(QDialog):
    """Dialog zur flexiblen Mehrfachumbenennung von Dateien."""

    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths = [p for p in file_paths if os.path.exists(p)]
        self.preview_items: List[RenameItem] = []
        self.history: List[tuple] = []

        self.setWindowTitle(t("Mehrfach umbenennen"))
        self.resize(900, 650)
        self.setMinimumSize(750, 500)
        self.setAccessibleName("Mehrfachumbenennung")
        self.setAccessibleDescription(
            "Regelbasierte Umbenennung mehrerer Dateien mit konfigurierbaren Ersetzungen, Präfixen, Suffixen und Nummerierung."
        )

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Info-Kopfzeile
        count_lbl = QLabel(f"{len(self.file_paths)} " + t("Dateien ausgewählt"))
        font = count_lbl.font()
        font.setBold(True)
        count_lbl.setFont(font)
        count_lbl.setAccessibleName("Auswahlzähler")
        main_layout.addWidget(count_lbl)

        # Regelsätze in Gruppen
        rules_layout = QHBoxLayout()
        rules_layout.setSpacing(10)

        # 1. Gruppe: Suchen & Ersetzen
        search_group = QGroupBox(t("Suchen & Ersetzen"))
        search_grid = QGridLayout(search_group)

        search_lbl = QLabel(t("Suchen:"))
        search_grid.addWidget(search_lbl, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setAccessibleName("Suchbegriff für Umbenennung")
        self.search_edit.setAccessibleDescription("Zu suchender Text im ursprünglichen Dateinamen.")
        self.search_edit.setToolTip("Zu ersetzender Teilstring im Dateinamen")
        search_lbl.setBuddy(self.search_edit)
        self.search_edit.textChanged.connect(self._update_preview)
        search_grid.addWidget(self.search_edit, 0, 1)

        replace_lbl = QLabel(t("Ersetzen:"))
        search_grid.addWidget(replace_lbl, 1, 0)
        self.replace_edit = QLineEdit()
        self.replace_edit.setAccessibleName("Ersetzungstext")
        self.replace_edit.setAccessibleDescription("Neuer Text, der anstelle des Suchbegriffs eingesetzt wird.")
        self.replace_edit.setToolTip("Neuer Text für gefundene Treffer")
        replace_lbl.setBuddy(self.replace_edit)
        self.replace_edit.textChanged.connect(self._update_preview)
        search_grid.addWidget(self.replace_edit, 1, 1)

        self.regex_cb = QCheckBox(t("Reguläre Ausdrücke (Regex)"))
        self.regex_cb.setAccessibleName("Reguläre Ausdrücke")
        self.regex_cb.setAccessibleDescription("Aktiviert die Auswertung regulärer Ausdrücke im Suchbegriff.")
        self.regex_cb.setToolTip("Suchbegriff als regulären Ausdruck auswerten")
        self.regex_cb.toggled.connect(self._update_preview)
        search_grid.addWidget(self.regex_cb, 2, 0, 1, 2)

        self.case_sensitive_cb = QCheckBox(t("Groß-/Kleinschreibung beachten"))
        self.case_sensitive_cb.setChecked(True)
        self.case_sensitive_cb.setAccessibleName("Groß- und Kleinschreibung beachten")
        self.case_sensitive_cb.setAccessibleDescription("Unterscheidet zwischen Groß- und Kleinbuchstaben beim Suchen.")
        self.case_sensitive_cb.setToolTip("Exakte Schreibweise beim Suchen berücksichtigen")
        self.case_sensitive_cb.toggled.connect(self._update_preview)
        search_grid.addWidget(self.case_sensitive_cb, 3, 0, 1, 2)

        rules_layout.addWidget(search_group)

        # 2. Gruppe: Präfix & Suffix
        affix_group = QGroupBox(t("Präfix & Suffix"))
        affix_grid = QGridLayout(affix_group)

        prefix_lbl = QLabel(t("Präfix:"))
        affix_grid.addWidget(prefix_lbl, 0, 0)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setAccessibleName("Dateinamen-Präfix")
        self.prefix_edit.setAccessibleDescription("Text, der vor jeden Dateinamen eingefügt wird.")
        self.prefix_edit.setToolTip("Präfix vor den Dateinamen stellen")
        prefix_lbl.setBuddy(self.prefix_edit)
        self.prefix_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.prefix_edit, 0, 1)

        suffix_lbl = QLabel(t("Suffix:"))
        affix_grid.addWidget(suffix_lbl, 1, 0)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setAccessibleName("Dateinamen-Suffix")
        self.suffix_edit.setAccessibleDescription("Text, der an das Ende des Dateinamens vor die Dateiendung gehängt wird.")
        self.suffix_edit.setToolTip("Suffix an den Dateinamen anhängen")
        suffix_lbl.setBuddy(self.suffix_edit)
        self.suffix_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.suffix_edit, 1, 1)

        case_lbl = QLabel(t("Groß-/Klein:"))
        affix_grid.addWidget(case_lbl, 2, 0)
        self.case_combo = QComboBox()
        self.case_combo.addItem(t("Unverändert"), None)
        self.case_combo.addItem(t("kleinbuchstaben"), "lower")
        self.case_combo.addItem(t("GROSSBUCHSTABEN"), "upper")
        self.case_combo.addItem(t("Wortanfang Groß"), "title")
        self.case_combo.addItem(t("Satzanfang groß"), "sentence")
        self.case_combo.setAccessibleName("Schreibweisenumwandlung")
        self.case_combo.setAccessibleDescription("Wandelt die Schreibweise aller Dateinamen einheitlich um.")
        self.case_combo.setToolTip("Groß- und Kleinschreibung des Namens anpassen")
        case_lbl.setBuddy(self.case_combo)
        self.case_combo.currentIndexChanged.connect(self._update_preview)
        affix_grid.addWidget(self.case_combo, 2, 1)

        ext_lbl = QLabel(t("Dateiendung:"))
        affix_grid.addWidget(ext_lbl, 3, 0)
        self.ext_edit = QLineEdit()
        self.ext_edit.setPlaceholderText(t("z. B. .txt (leer = beibehalten)"))
        self.ext_edit.setAccessibleName("Neue Dateiendung")
        self.ext_edit.setAccessibleDescription("Neue Dateiendung mit Punkt, oder leer lassen um bestehende Endung zu behalten.")
        self.ext_edit.setToolTip("Neue Endung eingeben oder leer lassen")
        ext_lbl.setBuddy(self.ext_edit)
        self.ext_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.ext_edit, 3, 1)

        rules_layout.addWidget(affix_group)

        # 3. Gruppe: Nummerierung
        num_group = QGroupBox(t("Nummerierung"))
        num_grid = QGridLayout(num_group)

        self.num_enabled_cb = QCheckBox(t("Nummerierung aktivieren"))
        self.num_enabled_cb.setAccessibleName("Nummerierung aktivieren")
        self.num_enabled_cb.setAccessibleDescription("Schaltet die sequentielle Dateinummerierung ein.")
        self.num_enabled_cb.setToolTip("Dateien fortlaufend nummerieren")
        self.num_enabled_cb.toggled.connect(self._update_preview)
        num_grid.addWidget(self.num_enabled_cb, 0, 0, 1, 2)

        start_lbl = QLabel(t("Startwert:"))
        num_grid.addWidget(start_lbl, 1, 0)
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 999999)
        self.start_spin.setValue(1)
        self.start_spin.setAccessibleName("Startwert der Nummerierung")
        self.start_spin.setToolTip("Startnummer der Zählung")
        start_lbl.setBuddy(self.start_spin)
        self.start_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.start_spin, 1, 1)

        step_lbl = QLabel(t("Schrittweite:"))
        num_grid.addWidget(step_lbl, 2, 0)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 1000)
        self.step_spin.setValue(1)
        self.step_spin.setAccessibleName("Schrittweite der Nummerierung")
        self.step_spin.setToolTip("Inkrement pro Datei")
        step_lbl.setBuddy(self.step_spin)
        self.step_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.step_spin, 2, 1)

        pad_lbl = QLabel(t("Stellen (Padding):"))
        num_grid.addWidget(pad_lbl, 3, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(1, 10)
        self.padding_spin.setValue(2)
        self.padding_spin.setAccessibleName("Stellenanzahl mit führenden Nullen")
        self.padding_spin.setToolTip("Mindeststellenanzahl (z. B. 2 ergibt 01, 02)")
        pad_lbl.setBuddy(self.padding_spin)
        self.padding_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.padding_spin, 3, 1)

        pos_lbl = QLabel(t("Position:"))
        num_grid.addWidget(pos_lbl, 4, 0)
        self.num_pos_combo = QComboBox()
        self.num_pos_combo.addItem(t("Am Ende (Suffix)"), "suffix")
        self.num_pos_combo.addItem(t("Am Anfang (Präfix)"), "prefix")
        self.num_pos_combo.addItem(t("Ersetzen"), "replace")
        self.num_pos_combo.setAccessibleName("Position der Nummerierung")
        self.num_pos_combo.setToolTip("Position der Nummerierung im Dateinamen")
        pos_lbl.setBuddy(self.num_pos_combo)
        self.num_pos_combo.currentIndexChanged.connect(self._update_preview)
        num_grid.addWidget(self.num_pos_combo, 4, 1)

        rules_layout.addWidget(num_group)

        main_layout.addLayout(rules_layout)

        # Vorschau-Tabelle
        preview_group = QGroupBox(t("Vorschau"))
        preview_layout = QVBoxLayout(preview_group)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            t("Originalname"), t("Neuer Name"), t("Status")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setAccessibleName("Umbenennungs-Vorschautabelle")
        self.table.setAccessibleDescription("Zeigt Originalnamen, vorgeschlagene neue Namen und eventuelle Konflikte.")
        self.table.setToolTip("Vorschautabelle aller zu ändernden Dateinamen")
        preview_layout.addWidget(self.table)

        # Statusleiste / Zusammenfassung
        self.summary_label = QLabel("")
        self.summary_label.setAccessibleName("Zusammenfassung der Umbenennung")
        preview_layout.addWidget(self.summary_label)

        main_layout.addWidget(preview_group)

        # Button-Leiste
        btn_layout = QHBoxLayout()

        self.rollback_btn = QPushButton(t("Rückgängig"))
        self.rollback_btn.setAccessibleName("Letzte Umbenennung rückgängig machen")
        self.rollback_btn.setToolTip("Macht die vorherige Umbenennungs-Aktion rückgängig")
        self.rollback_btn.setEnabled(False)
        self.rollback_btn.clicked.connect(self._do_rollback)
        btn_layout.addWidget(self.rollback_btn)

        btn_layout.addStretch()

        self.rename_btn = QPushButton(t("Umbenennen"))
        self.rename_btn.setAccessibleName("Dateien jetzt umbenennen")
        self.rename_btn.setToolTip("Führt die geplante Umbenennung für alle Dateien aus (Enter)")
        self.rename_btn.setDefault(True)
        self.rename_btn.clicked.connect(self._do_rename)
        btn_layout.addWidget(self.rename_btn)

        self.close_btn = QPushButton(t("Schließen"))
        self.close_btn.setAccessibleName("Dialog schließen")
        self.close_btn.setToolTip("Schließt das Mehrfachumbenennungs-Fenster (Esc)")
        self.close_btn.setShortcut("Escape")
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def _get_rules(self) -> RenameRules:
        ext_val = self.ext_edit.text().strip()
        change_ext = ext_val if ext_val else None

        return RenameRules(
            search_str=self.search_edit.text(),
            replace_str=self.replace_edit.text(),
            use_regex=self.regex_cb.isChecked(),
            regex_case_sensitive=self.case_sensitive_cb.isChecked(),
            prefix=self.prefix_edit.text(),
            suffix=self.suffix_edit.text(),
            case_mode=self.case_combo.currentData(),
            numbering_enabled=self.num_enabled_cb.isChecked(),
            start_num=self.start_spin.value(),
            step_num=self.step_spin.value(),
            padding=self.padding_spin.value(),
            number_position=self.num_pos_combo.currentData(),
            change_extension=change_ext,
        )

    def _update_preview(self):
        rules = self._get_rules()
        self.preview_items = generate_preview(self.file_paths, rules)

        self.table.setRowCount(len(self.preview_items))

        has_conflicts = False
        actionable_count = 0

        for row, item in enumerate(self.preview_items):
            # Original
            orig_item = QTableWidgetItem(item.original_name)
            self.table.setItem(row, 0, orig_item)

            # Neu
            new_item = QTableWidgetItem(item.new_name)
            self.table.setItem(row, 1, new_item)

            # Status
            status_item = QTableWidgetItem()
            if item.status == "ok":
                status_item.setText(t("Bereit"))
                status_item.setForeground(QBrush(QColor("#2e7d32")))  # Dunkelgrün
                actionable_count += 1
            elif item.status == "unchanged":
                status_item.setText(t("Unverändert"))
                status_item.setForeground(QBrush(QColor("#757575")))  # Grau
            elif item.status == "collision":
                status_item.setText(t("Kollision"))
                status_item.setToolTip(item.error_message or "")
                status_item.setForeground(QBrush(QColor("#c62828")))  # Rot
                has_conflicts = True
            elif item.status == "invalid":
                status_item.setText(t("Ungültig"))
                status_item.setToolTip(item.error_message or "")
                status_item.setForeground(QBrush(QColor("#c62828")))  # Rot
                has_conflicts = True

            self.table.setItem(row, 2, status_item)

        # Zusammenfassung
        if has_conflicts:
            self.summary_label.setText(
                f"⚠️ {actionable_count} " + t("zu ändern, Konflikte oder ungültige Namen gefunden!")
            )
            self.summary_label.setStyleSheet("color: #c62828; font-weight: bold;")
            self.rename_btn.setEnabled(False)
        elif actionable_count == 0:
            self.summary_label.setText(t("Keine Änderungen an den Dateinamen."))
            self.summary_label.setStyleSheet("color: #757575;")
            self.rename_btn.setEnabled(False)
        else:
            self.summary_label.setText(
                f"✓ {actionable_count} " + t("Dateien werden umbenannt.")
            )
            self.summary_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
            self.rename_btn.setEnabled(True)

    def _do_rename(self):
        success_count, errors, history = execute_rename(self.preview_items)
        self.history.extend(history)

        if errors:
            err_text = "\n".join(errors[:5])
            if len(errors) > 5:
                err_text += f"\n... und {len(errors) - 5} weitere"
            QMessageBox.warning(
                self, t("Fehler beim Umbenennen"),
                f"{success_count} " + t("Dateien umbenannt, aber Fehler aufgetreten:\n\n") + err_text
            )
        else:
            QMessageBox.information(
                self, t("Erfolg"),
                f"{success_count} " + t("Dateien erfolgreich umbenannt.")
            )

        if self.history:
            self.rollback_btn.setEnabled(True)

        # Aktualisiere die gespeicherten Pfade auf die neuen Pfade
        updated_paths = []
        for item in self.preview_items:
            if item.status == "ok":
                updated_paths.append(item.new_path)
            else:
                updated_paths.append(item.original_path)
        self.file_paths = updated_paths

        self._update_preview()
        if not errors:
            self.accept()

    def _do_rollback(self):
        if not self.history:
            return
        restored, errors = rollback_rename(self.history)
        self.history.clear()
        self.rollback_btn.setEnabled(False)

        if errors:
            QMessageBox.warning(
                self, t("Rollback unvollständig"),
                f"{restored} " + t("Dateien zurückgesetzt, Fehler:\n") + "\n".join(errors)
            )
        else:
            QMessageBox.information(
                self, t("Rollback erfolgreich"),
                f"{restored} " + t("Dateien wurden auf die ursprünglichen Namen zurückgesetzt.")
            )

        self._update_preview()
