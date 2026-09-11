#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_dialog.py - Datei-Vergleichs-Dialog (Diff Viewer)

Funktionen:
- Gegenüberstellung zweier Dateien (Text oder Binär)
- Zeilenweiser Diff mit visueller Syntax-Hervorhebung (+ Grün, - Rot)
- Größen- und SHA-256-Hash-Prüfung
- Statistik über hinzugefügte, gelöschte und identische Zeilen
- Export & Zwischenablage des Unified-Diffs
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox,
    QFileDialog, QApplication, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

from core.diff_service import (
    compare_files, generate_unified_diff_text, DiffResult
)
from translator import t


class DiffDialog(QDialog):
    """Dialog zur visuellen Gegenüberstellung und Analyse zweier Dateien."""

    def __init__(self, file1: str = "", file2: str = "", parent=None):
        super().__init__(parent)
        self.file1 = file1
        self.file2 = file2
        self.current_diff: Optional[DiffResult] = None

        self.setWindowTitle(t("Dateien vergleichen (Diff)"))
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)

        self._setup_ui()
        if self.file1 and self.file2 and os.path.exists(self.file1) and os.path.exists(self.file2):
            self._do_compare()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # 1. Datei-Auswahl
        files_group = QGroupBox(t("Zu vergleichende Dateien"))
        files_grid = QGridLayout(files_group)

        files_grid.addWidget(QLabel(t("Datei 1 (Basis):")), 0, 0)
        self.file1_edit = QLineEdit(self.file1)
        self.file1_edit.setPlaceholderText(t("Pfad zu Datei 1..."))
        files_grid.addWidget(self.file1_edit, 0, 1)
        browse1_btn = QPushButton(t("Durchsuchen..."))
        browse1_btn.clicked.connect(self._browse_file1)
        files_grid.addWidget(browse1_btn, 0, 2)

        files_grid.addWidget(QLabel(t("Datei 2 (Vergleich):")), 1, 0)
        self.file2_edit = QLineEdit(self.file2)
        self.file2_edit.setPlaceholderText(t("Pfad zu Datei 2..."))
        files_grid.addWidget(self.file2_edit, 1, 1)
        browse2_btn = QPushButton(t("Durchsuchen..."))
        browse2_btn.clicked.connect(self._browse_file2)
        files_grid.addWidget(browse2_btn, 1, 2)

        compare_btn = QPushButton("🔍 " + t("Vergleichen"))
        compare_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        compare_btn.clicked.connect(self._do_compare)
        files_grid.addWidget(compare_btn, 2, 1, 1, 2)

        main_layout.addWidget(files_group)

        # 2. Metadaten- & Statistik-Leiste
        self.status_group = QGroupBox(t("Vergleichs-Status"))
        status_layout = QVBoxLayout(self.status_group)

        self.status_label = QLabel(t("Wählen Sie zwei Dateien aus und klicken Sie auf 'Vergleichen'."))
        font = self.status_label.font()
        font.setBold(True)
        self.status_label.setFont(font)
        status_layout.addWidget(self.status_label)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #616161;")
        status_layout.addWidget(self.meta_label)

        main_layout.addWidget(self.status_group)

        # 3. Diff-Tabelle
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            t("Zeile 1"), t("Zeile 2"), t("Inhalt")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table)

        # 4. Button-Leiste
        btn_layout = QHBoxLayout()

        self.copy_btn = QPushButton("📋 " + t("Unified-Diff kopieren"))
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_unified_diff)
        btn_layout.addWidget(self.copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(t("Schließen"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

    def _browse_file1(self):
        path, _ = QFileDialog.getOpenFileName(self, t("Datei 1 auswählen"), self.file1_edit.text() or "")
        if path:
            self.file1_edit.setText(path)

    def _browse_file2(self):
        path, _ = QFileDialog.getOpenFileName(self, t("Datei 2 auswählen"), self.file2_edit.text() or "")
        if path:
            self.file2_edit.setText(path)

    def _do_compare(self):
        f1 = self.file1_edit.text().strip()
        f2 = self.file2_edit.text().strip()

        if not f1 or not f2:
            QMessageBox.warning(self, t("Fehlende Angabe"), t("Bitte wählen Sie zwei Dateien zum Vergleichen aus."))
            return

        if not os.path.exists(f1):
            QMessageBox.warning(self, t("Datei nicht gefunden"), f"{t('Datei nicht gefunden')}:\n{f1}")
            return
        if not os.path.exists(f2):
            QMessageBox.warning(self, t("Datei nicht gefunden"), f"{t('Datei nicht gefunden')}:\n{f2}")
            return

        try:
            self.current_diff = compare_files(f1, f2)
        except Exception as exc:
            QMessageBox.critical(self, t("Fehler"), f"{t('Fehler beim Dateivergleich')}:\n{exc}")
            return

        self._render_diff()

    def _render_diff(self):
        diff = self.current_diff
        if not diff:
            return

        # Status & Header
        if diff.is_identical:
            self.status_label.setText(f"✓ {t('Dateien sind absolut identisch')}")
            self.status_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 13px;")
        else:
            self.status_label.setText(f"≠ {t('Dateien weisen Unterschiede auf')}")
            self.status_label.setStyleSheet("color: #c62828; font-weight: bold; font-size: 13px;")

        # Details
        size_txt = f"{diff.file1_name} ({diff.file1_size:,} Bytes) ↔ {diff.file2_name} ({diff.file2_size:,} Bytes)"
        hash_txt = f"SHA256 1: {diff.file1_hash[:16]}... | SHA256 2: {diff.file2_hash[:16]}..."
        if diff.is_binary:
            stat_txt = t("Binärvergleich")
        else:
            stat_txt = (
                f"+{diff.stats['added']} " + t("hinzugefügt") + " | " +
                f"-{diff.stats['deleted']} " + t("entfernt") + " | " +
                f"{diff.stats['identical']} " + t("identisch")
            )
        self.meta_label.setText(f"{size_txt}\n{hash_txt}\n{stat_txt}")

        # Tabelle befüllen
        self.table.setRowCount(len(diff.lines))
        mono_font = QFont("Consolas, Courier New, monospace")
        mono_font.setPointSize(9)

        for row, line in enumerate(diff.lines):
            # Zeilennummer links
            item_l = QTableWidgetItem(str(line.line_num_left) if line.line_num_left is not None else "")
            item_l.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_l.setFont(mono_font)

            # Zeilennummer rechts
            item_r = QTableWidgetItem(str(line.line_num_right) if line.line_num_right is not None else "")
            item_r.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_r.setFont(mono_font)

            # Inhalt
            prefix = ""
            if line.tag == "insert":
                prefix = "+ "
            elif line.tag == "delete":
                prefix = "- "
            elif line.tag == "equal":
                prefix = "  "

            item_c = QTableWidgetItem(prefix + line.content)
            item_c.setFont(mono_font)

            # Farbliche Markierung
            if line.tag == "insert":
                bg_brush = QBrush(QColor("#e8f5e9"))  # Sanftes Grün
                fg_brush = QBrush(QColor("#1b5e20"))
            elif line.tag == "delete":
                bg_brush = QBrush(QColor("#ffebee"))  # Sanftes Rot
                fg_brush = QBrush(QColor("#b71c1c"))
            elif line.tag == "info":
                bg_brush = QBrush(QColor("#f5f5f5"))
                fg_brush = QBrush(QColor("#616161"))
            else:
                bg_brush = QBrush(QColor("#ffffff"))
                fg_brush = QBrush(QColor("#212121"))

            item_l.setBackground(bg_brush)
            item_r.setBackground(bg_brush)
            item_c.setBackground(bg_brush)

            item_l.setForeground(fg_brush)
            item_r.setForeground(fg_brush)
            item_c.setForeground(fg_brush)

            self.table.setItem(row, 0, item_l)
            self.table.setItem(row, 1, item_r)
            self.table.setItem(row, 2, item_c)

        self.copy_btn.setEnabled(True)

    def _copy_unified_diff(self):
        f1 = self.file1_edit.text().strip()
        f2 = self.file2_edit.text().strip()
        if not f1 or not f2:
            return

        text = generate_unified_diff_text(f1, f2)
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(
                self, t("Kopiert"),
                t("Unified-Diff wurde in die Zwischenablage kopiert.")
            )
        else:
            QMessageBox.information(
                self, t("Diff"),
                t("Keine Text-Unterschiede zum Kopieren vorhanden.")
            )

    def closeEvent(self, event):
        super().closeEvent(event)
