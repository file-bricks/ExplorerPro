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
        main_layout.addWidget(count_lbl)

        # Regelsätze in Gruppen
        rules_layout = QHBoxLayout()
        rules_layout.setSpacing(10)

        # 1. Gruppe: Suchen & Ersetzen
        search_group = QGroupBox(t("Suchen & Ersetzen"))
        search_grid = QGridLayout(search_group)

        search_grid.addWidget(QLabel(t("Suchen:")), 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._update_preview)
        search_grid.addWidget(self.search_edit, 0, 1)

        search_grid.addWidget(QLabel(t("Ersetzen:")), 1, 0)
        self.replace_edit = QLineEdit()
        self.replace_edit.textChanged.connect(self._update_preview)
        search_grid.addWidget(self.replace_edit, 1, 1)

        self.regex_cb = QCheckBox(t("Reguläre Ausdrücke (Regex)"))
        self.regex_cb.toggled.connect(self._update_preview)
        search_grid.addWidget(self.regex_cb, 2, 0, 1, 2)

        self.case_sensitive_cb = QCheckBox(t("Groß-/Kleinschreibung beachten"))
        self.case_sensitive_cb.setChecked(True)
        self.case_sensitive_cb.toggled.connect(self._update_preview)
        search_grid.addWidget(self.case_sensitive_cb, 3, 0, 1, 2)

        rules_layout.addWidget(search_group)

        # 2. Gruppe: Präfix & Suffix
        affix_group = QGroupBox(t("Präfix & Suffix"))
        affix_grid = QGridLayout(affix_group)

        affix_grid.addWidget(QLabel(t("Präfix:")), 0, 0)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.prefix_edit, 0, 1)

        affix_grid.addWidget(QLabel(t("Suffix:")), 1, 0)
        self.suffix_edit = QLineEdit()
        self.suffix_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.suffix_edit, 1, 1)

        affix_grid.addWidget(QLabel(t("Groß-/Klein:")), 2, 0)
        self.case_combo = QComboBox()
        self.case_combo.addItem(t("Unverändert"), None)
        self.case_combo.addItem(t("kleinbuchstaben"), "lower")
        self.case_combo.addItem(t("GROSSBUCHSTABEN"), "upper")
        self.case_combo.addItem(t("Wortanfang Groß"), "title")
        self.case_combo.addItem(t("Satzanfang groß"), "sentence")
        self.case_combo.currentIndexChanged.connect(self._update_preview)
        affix_grid.addWidget(self.case_combo, 2, 1)

        affix_grid.addWidget(QLabel(t("Dateiendung:")), 3, 0)
        self.ext_edit = QLineEdit()
        self.ext_edit.setPlaceholderText(t("z. B. .txt (leer = beibehalten)"))
        self.ext_edit.textChanged.connect(self._update_preview)
        affix_grid.addWidget(self.ext_edit, 3, 1)

        rules_layout.addWidget(affix_group)

        # 3. Gruppe: Nummerierung
        num_group = QGroupBox(t("Nummerierung"))
        num_grid = QGridLayout(num_group)

        self.num_enabled_cb = QCheckBox(t("Nummerierung aktivieren"))
        self.num_enabled_cb.toggled.connect(self._update_preview)
        num_grid.addWidget(self.num_enabled_cb, 0, 0, 1, 2)

        num_grid.addWidget(QLabel(t("Startwert:")), 1, 0)
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 999999)
        self.start_spin.setValue(1)
        self.start_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.start_spin, 1, 1)

        num_grid.addWidget(QLabel(t("Schrittweite:")), 2, 0)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 1000)
        self.step_spin.setValue(1)
        self.step_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.step_spin, 2, 1)

        num_grid.addWidget(QLabel(t("Stellen (Padding):")), 3, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(1, 10)
        self.padding_spin.setValue(2)
        self.padding_spin.valueChanged.connect(self._update_preview)
        num_grid.addWidget(self.padding_spin, 3, 1)

        num_grid.addWidget(QLabel(t("Position:")), 4, 0)
        self.num_pos_combo = QComboBox()
        self.num_pos_combo.addItem(t("Am Ende (Suffix)"), "suffix")
        self.num_pos_combo.addItem(t("Am Anfang (Präfix)"), "prefix")
        self.num_pos_combo.addItem(t("Ersetzen"), "replace")
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
        preview_layout.addWidget(self.table)

        # Statusleiste / Zusammenfassung
        self.summary_label = QLabel("")
        preview_layout.addWidget(self.summary_label)

        main_layout.addWidget(preview_group)

        # Button-Leiste
        btn_layout = QHBoxLayout()

        self.rollback_btn = QPushButton(t("Rückgängig"))
        self.rollback_btn.setEnabled(False)
        self.rollback_btn.clicked.connect(self._do_rollback)
        btn_layout.addWidget(self.rollback_btn)

        btn_layout.addStretch()

        self.rename_btn = QPushButton(t("Umbenennen"))
        self.rename_btn.setDefault(True)
        self.rename_btn.clicked.connect(self._do_rename)
        btn_layout.addWidget(self.rename_btn)

        self.close_btn = QPushButton(t("Schließen"))
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
