#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_dialog.py - Interaktive Archiv-Dialoge für ExplorerPro
=============================================================
Stellt dialogbasierte Benutzeroberflächen bereit:
- ArchiveCompressDialog: ZIP-Erstellung aus Auswahl mit Kompressionsstufen
- ArchiveExtractDialog: Sichere Entpackung mit Unterordner-Option & Zip-Slip-Schutz
- ArchiveViewerDialog: Vollständiger Archiv-Inspektor mit Suche, Metriken und CRC-Test
"""

import os
from pathlib import Path
from typing import List, Optional
import zipfile

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout
)

from core.archive_service import (
    ArchiveCompressWorker, ArchiveExtractWorker, ArchiveTestWorker,
    format_bytes, inspect_zip
)
from translator import t


class ArchiveCompressDialog(QDialog):
    """Dialog zur Erstellung eines neuen ZIP-Archivs aus einer Auswahl."""

    def __init__(self, sources: List[str], current_dir: str = "", parent=None):
        super().__init__(parent)
        self.sources = [s for s in sources if os.path.exists(s)]
        self.current_dir = current_dir or (os.path.dirname(self.sources[0]) if self.sources else "")
        self.worker: Optional[ArchiveCompressWorker] = None
        self.created_archive: Optional[str] = None

        self.setWindowTitle(t("Zu ZIP-Archiv komprimieren"))
        self.setMinimumWidth(560)
        self.setAccessibleName(t("ZIP-Archiv erstellen"))
        self.setAccessibleDescription(
            t("Ermöglicht das Komprimieren von Dateien und Ordnern in ein ZIP-Archiv.")
        )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Auswahl-Zusammenfassung
        summary_group = QGroupBox(t("Ausgewählte Elemente"))
        summary_layout = QVBoxLayout(summary_group)
        count = len(self.sources)
        if count == 1:
            first_name = os.path.basename(self.sources[0])
            summary_label = QLabel(f"📄 1 Element ausgewählt: {first_name}")
        else:
            summary_label = QLabel(f"📁 {count} Elemente ausgewählt")
        summary_label.setWordWrap(True)
        summary_layout.addWidget(summary_label)
        layout.addWidget(summary_group)

        # Zielarchiv-Eingabe
        dest_group = QGroupBox(t("Zielarchiv"))
        dest_layout = QHBoxLayout(dest_group)

        default_name = "Archiv.zip"
        if count == 1:
            stem = Path(self.sources[0]).stem
            default_name = f"{stem}.zip"
        elif count > 1 and self.current_dir:
            parent_name = Path(self.current_dir).name
            if parent_name:
                default_name = f"{parent_name}.zip"

        default_target = os.path.join(self.current_dir, default_name)

        self.dest_edit = QLineEdit(default_target)
        self.dest_edit.setAccessibleName(t("Zielpfad für das ZIP-Archiv"))
        self.dest_edit.setToolTip(t("Geben Sie den vollständigen Pfad für die neue ZIP-Datei an"))
        dest_layout.addWidget(self.dest_edit, 1)

        browse_btn = QPushButton(t("Durchsuchen..."))
        browse_btn.setAccessibleName(t("Zielverzeichnis durchsuchen"))
        browse_btn.clicked.connect(self._browse_destination)
        dest_layout.addWidget(browse_btn)

        layout.addWidget(dest_group)

        # Optionen-Gruppe
        options_group = QGroupBox(t("Kompressionsoptionen"))
        options_layout = QFormLayout(options_group)

        self.method_combo = QComboBox()
        self.method_combo.setAccessibleName(t("Kompressionsmethode"))
        self.method_combo.addItem(t("Standard (DEFLATED, Stufe 6)"), (zipfile.ZIP_DEFLATED, 6))
        self.method_combo.addItem(t("Maximal (DEFLATED, Stufe 9)"), (zipfile.ZIP_DEFLATED, 9))
        self.method_combo.addItem(t("Schnell (DEFLATED, Stufe 1)"), (zipfile.ZIP_DEFLATED, 1))
        self.method_combo.addItem(t("Keine Kompression (STORED)"), (zipfile.ZIP_STORED, 0))

        if hasattr(zipfile, "ZIP_BZIP2"):
            self.method_combo.addItem(t("BZIP2 Kompression"), (zipfile.ZIP_BZIP2, 9))
        if hasattr(zipfile, "ZIP_LZMA"):
            self.method_combo.addItem(t("LZMA Kompression"), (zipfile.ZIP_LZMA, 0))

        options_layout.addRow(t("Methode:"), self.method_combo)
        layout.addWidget(options_group)

        # Fortschrittsbalken
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setAccessibleName(t("Komprimierungsfortschritt"))
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Button-Leiste
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.create_btn = QPushButton(t("📦 Archiv erstellen"))
        self.create_btn.setDefault(True)
        self.create_btn.setAccessibleName(t("Archiverstellung starten"))
        self.create_btn.clicked.connect(self._start_compression)
        btn_layout.addWidget(self.create_btn)

        self.cancel_btn = QPushButton(t("Abbrechen"))
        self.cancel_btn.setAccessibleName(t("Vorgang abbrechen"))
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _browse_destination(self):
        curr_text = self.dest_edit.text()
        init_dir = os.path.dirname(curr_text) if curr_text else self.current_dir
        path, _ = QFileDialog.getSaveFileName(
            self,
            t("Ziel-ZIP-Datei auswählen"),
            curr_text or os.path.join(init_dir, "Archiv.zip"),
            t("ZIP-Archive (*.zip);;Alle Dateien (*.*)")
        )
        if path:
            if not path.lower().endswith(".zip"):
                path += ".zip"
            self.dest_edit.setText(path)

    def _start_compression(self):
        dest_path = self.dest_edit.text().strip()
        if not dest_path:
            QMessageBox.warning(self, t("Fehler"), t("Bitte geben Sie einen Zielpfad an."))
            return

        if not dest_path.lower().endswith(".zip"):
            dest_path += ".zip"
            self.dest_edit.setText(dest_path)

        if os.path.exists(dest_path):
            reply = QMessageBox.question(
                self,
                t("Datei überschreiben"),
                t("Die Zieldatei existiert bereits. Möchten Sie sie überschreiben?\n") + dest_path,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        comp_type, comp_level = self.method_combo.currentData()

        self.create_btn.setEnabled(False)
        self.dest_edit.setEnabled(False)
        self.method_combo.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(t("Komprimierung wird vorbereitet..."))

        self.worker = ArchiveCompressWorker(
            self.sources,
            dest_path,
            compression=comp_type,
            compresslevel=comp_level,
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        short_name = os.path.basename(filename)
        self.status_label.setText(f"{current}/{total}: {short_name}")

    @Slot(bool, str, int, int)
    def _on_finished(self, success: bool, dest_path: str, count: int, total_bytes: int):
        self.progress_bar.setVisible(False)
        self.create_btn.setEnabled(True)
        self.dest_edit.setEnabled(True)
        self.method_combo.setEnabled(True)

        if success:
            self.created_archive = dest_path
            formatted_size = format_bytes(total_bytes)
            QMessageBox.information(
                self,
                t("Archiv erstellt"),
                t("Das Archiv wurde erfolgreich erstellt:\n\n")
                + f"{dest_path}\n\n"
                + f"{count} " + t("Elemente") + f" ({formatted_size})"
            )
            self.accept()
        else:
            if self.worker and self.worker._is_cancelled:
                self.status_label.setText(t("Vorgang abgebrochen."))
            else:
                self.status_label.setText(t("Erstellung fehlgeschlagen."))

    @Slot(str)
    def _on_error(self, err_msg: str):
        QMessageBox.critical(self, t("Fehler beim Komprimieren"), f"{err_msg}")

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText(t("Wird abgebrochen..."))
            self.worker.wait(1500)
        self.reject()


class ArchiveExtractDialog(QDialog):
    """Dialog zum sicheren Entpacken eines ZIP-Archivs."""

    def __init__(self, zip_path: str, default_target_dir: str = "", parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.default_target_dir = default_target_dir or os.path.dirname(zip_path)
        self.worker: Optional[ArchiveExtractWorker] = None
        self.extracted_target: Optional[str] = None

        self.setWindowTitle(t("ZIP-Archiv entpacken"))
        self.setMinimumWidth(560)
        self.setAccessibleName(t("ZIP-Archiv entpacken"))
        self.setAccessibleDescription(
            t("Ermöglicht das sichere Entpacken eines ZIP-Archivs in ein Zielverzeichnis.")
        )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Archiv-Info
        info_group = QGroupBox(t("Archiv-Information"))
        info_layout = QFormLayout(info_group)
        name_label = QLabel(os.path.basename(self.zip_path))
        info_layout.addRow(t("Archiv:"), name_label)

        try:
            summary, _ = inspect_zip(self.zip_path)
            details = f"{summary.total_files} " + t("Dateien") + f", {summary.total_folders} " + t("Ordner")
            details += f" ({summary.formatted_uncompressed_size})"
            info_layout.addRow(t("Inhalt:"), QLabel(details))
        except Exception:
            info_layout.addRow(t("Inhalt:"), QLabel(t("Konnte Archiv nicht analysieren")))

        layout.addWidget(info_group)

        # Zielordner
        target_group = QGroupBox(t("Zielverzeichnis"))
        target_layout = QHBoxLayout(target_group)

        self.target_edit = QLineEdit(self.default_target_dir)
        self.target_edit.setAccessibleName(t("Zielordner zum Entpacken"))
        self.target_edit.setToolTip(t("Wählen Sie den Ordner, in den die Dateien entpackt werden sollen"))
        target_layout.addWidget(self.target_edit, 1)

        browse_btn = QPushButton(t("Durchsuchen..."))
        browse_btn.setAccessibleName(t("Zielordner durchsuchen"))
        browse_btn.clicked.connect(self._browse_target)
        target_layout.addWidget(browse_btn)

        layout.addWidget(target_group)

        # Optionen
        options_group = QGroupBox(t("Optionen"))
        options_layout = QVBoxLayout(options_group)

        stem = Path(self.zip_path).stem
        self.subfolder_cb = QCheckBox(t("In Unterordner entpacken: ") + f"'{stem}'")
        self.subfolder_cb.setChecked(True)
        self.subfolder_cb.setAccessibleName(t("In separaten Unterordner entpacken"))
        options_layout.addWidget(self.subfolder_cb)

        self.overwrite_cb = QCheckBox(t("Vorhandene Dateien überschreiben"))
        self.overwrite_cb.setChecked(True)
        self.overwrite_cb.setAccessibleName(t("Vorhandene Dateien überschreiben"))
        options_layout.addWidget(self.overwrite_cb)

        layout.addWidget(options_group)

        # Fortschrittsbalken
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setAccessibleName(t("Entpackfortschritt"))
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.extract_btn = QPushButton(t("📦 Entpacken"))
        self.extract_btn.setDefault(True)
        self.extract_btn.setAccessibleName(t("Entpackvorgang starten"))
        self.extract_btn.clicked.connect(self._start_extraction)
        btn_layout.addWidget(self.extract_btn)

        self.cancel_btn = QPushButton(t("Abbrechen"))
        self.cancel_btn.setAccessibleName(t("Vorgang abbrechen"))
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _browse_target(self):
        curr = self.target_edit.text() or self.default_target_dir
        folder = QFileDialog.getExistingDirectory(
            self,
            t("Zielverzeichnis zum Entpacken wählen"),
            curr
        )
        if folder:
            self.target_edit.setText(folder)

    def _start_extraction(self):
        base_dir = self.target_edit.text().strip()
        if not base_dir:
            QMessageBox.warning(self, t("Fehler"), t("Bitte geben Sie ein Zielverzeichnis an."))
            return

        final_target = base_dir
        if self.subfolder_cb.isChecked():
            stem = Path(self.zip_path).stem
            final_target = os.path.join(base_dir, stem)

        self.extracted_target = final_target
        overwrite = self.overwrite_cb.isChecked()

        self.extract_btn.setEnabled(False)
        self.target_edit.setEnabled(False)
        self.subfolder_cb.setEnabled(False)
        self.overwrite_cb.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setVisible(True)
        self.status_label.setText(t("Entpacken wird gestartet..."))

        self.worker = ArchiveExtractWorker(
            self.zip_path,
            final_target,
            overwrite=overwrite,
            parent=self
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        short_name = os.path.basename(filename)
        self.status_label.setText(f"{current}/{total}: {short_name}")

    @Slot(bool, str, int, int)
    def _on_finished(self, success: bool, target_dir: str, count: int, total_bytes: int):
        self.progress_bar.setVisible(False)
        self.extract_btn.setEnabled(True)
        self.target_edit.setEnabled(True)
        self.subfolder_cb.setEnabled(True)
        self.overwrite_cb.setEnabled(True)

        if success:
            formatted_size = format_bytes(total_bytes)
            QMessageBox.information(
                self,
                t("Erfolgreich entpackt"),
                t("Dateien wurden erfolgreich entpackt nach:\n\n")
                + f"{target_dir}\n\n"
                + f"{count} " + t("Dateien") + f" ({formatted_size})"
            )
            self.accept()
        else:
            if self.worker and self.worker._is_cancelled:
                self.status_label.setText(t("Vorgang abgebrochen."))
            else:
                self.status_label.setText(t("Entpacken fehlgeschlagen."))

    @Slot(str)
    def _on_error(self, err_msg: str):
        QMessageBox.critical(self, t("Fehler beim Entpacken"), f"{err_msg}")

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText(t("Wird abgebrochen..."))
            self.worker.wait(1500)
        self.reject()


class ArchiveViewerDialog(QDialog):
    """Vollständiger Archiv-Inspektor mit Metadaten, Suche und CRC-Integritätstest."""

    def __init__(self, zip_path: str, parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.summary = None
        self.entries = []
        self.test_worker: Optional[ArchiveTestWorker] = None

        filename = os.path.basename(zip_path)
        self.setWindowTitle(t("Archiv durchsuchen — ") + filename)
        self.resize(780, 520)
        self.setAccessibleName(t("Archiv-Inspektor-Dialog"))
        self.setAccessibleDescription(
            t("Zeigt den Inhalt des ZIP-Archivs mit Dateigrößen, Kompressionsraten und Prüfoptionen.")
        )

        self._setup_ui()
        self._load_archive()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Kopf-Banner mit Metadaten
        header_group = QGroupBox(t("Archiv-Übersicht"))
        header_layout = QFormLayout(header_group)

        self.path_label = QLabel(self.zip_path)
        self.path_label.setWordWrap(True)
        header_layout.addRow(t("Pfad:"), self.path_label)

        self.stats_label = QLabel(t("Wird geladen..."))
        header_layout.addRow(t("Kennzahlen:"), self.stats_label)

        layout.addWidget(header_group)

        # Filterleiste
        filter_layout = QHBoxLayout()
        filter_label = QLabel(t("Filter:"))
        filter_layout.addWidget(filter_label)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(t("Dateinamen im Archiv filtern..."))
        self.filter_edit.setAccessibleName(t("Archiv-Filter"))
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_edit, 1)

        self.test_btn = QPushButton(t("🧪 Integrität prüfen"))
        self.test_btn.setAccessibleName(t("Archiv-Integrität prüfen"))
        self.test_btn.setToolTip(t("Führt einen CRC-Prüfsummentest aller Dateien im Archiv durch"))
        self.test_btn.clicked.connect(self._test_integrity)
        filter_layout.addWidget(self.test_btn)

        layout.addLayout(filter_layout)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            t("Name / Pfad"),
            t("Größe"),
            t("Komprimiert"),
            t("Ersparnis"),
            t("Geändert am"),
            t("CRC32")
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setAccessibleName(t("Archiv-Inhaltstabelle"))
        layout.addWidget(self.table, 1)

        # Status & Aktionsleiste
        action_layout = QHBoxLayout()

        self.integrity_label = QLabel("")
        action_layout.addWidget(self.integrity_label, 1)

        self.extract_selected_btn = QPushButton(t("📦 Ausgewählte entpacken..."))
        self.extract_selected_btn.setAccessibleName(t("Nur ausgewählte Dateien entpacken"))
        self.extract_selected_btn.clicked.connect(self._extract_selected)
        action_layout.addWidget(self.extract_selected_btn)

        self.extract_all_btn = QPushButton(t("📦 Alle entpacken..."))
        self.extract_all_btn.setAccessibleName(t("Gesamtes Archiv entpacken"))
        self.extract_all_btn.clicked.connect(self._extract_all)
        action_layout.addWidget(self.extract_all_btn)

        close_btn = QPushButton(t("Schließen"))
        close_btn.clicked.connect(self.accept)
        action_layout.addWidget(close_btn)

        layout.addLayout(action_layout)

    def _load_archive(self):
        try:
            self.summary, self.entries = inspect_zip(self.zip_path)
            stats_text = (
                f"{self.summary.total_files} " + t("Dateien") + f", "
                f"{self.summary.total_folders} " + t("Ordner") + " | "
                + t("Entpackt: ") + f"{self.summary.formatted_uncompressed_size} | "
                + t("Komprimiert: ") + f"{self.summary.formatted_compressed_size} "
                f"({self.summary.overall_ratio:.1f}% " + t("Ersparnis") + ")"
            )
            if self.summary.is_encrypted:
                stats_text += " | 🔒 " + t("Verschlüsselt")
            self.stats_label.setText(stats_text)
            self._populate_table()
        except Exception as exc:
            self.stats_label.setText(t("Fehler: ") + str(exc))
            QMessageBox.critical(self, t("Archivfehler"), t("Archiv konnte nicht gelesen werden:\n") + str(exc))

    def _populate_table(self):
        self.table.setRowCount(0)
        filter_text = self.filter_edit.text().strip().lower()

        filtered_entries = [
            e for e in self.entries
            if not filter_text or filter_text in e.filename.lower()
        ]

        self.table.setRowCount(len(filtered_entries))
        for row, entry in enumerate(filtered_entries):
            prefix = "📁 " if entry.is_dir else "📄 "
            item_name = QTableWidgetItem(f"{prefix}{entry.filename}")
            item_name.setData(Qt.ItemDataRole.UserRole, entry.filename)

            item_size = QTableWidgetItem(entry.formatted_size if not entry.is_dir else "-")
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            item_comp = QTableWidgetItem(entry.formatted_compressed_size if not entry.is_dir else "-")
            item_comp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            ratio_str = f"{entry.compression_ratio:.1f}%" if not entry.is_dir and entry.file_size > 0 else "-"
            item_ratio = QTableWidgetItem(ratio_str)
            item_ratio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            item_date = QTableWidgetItem(entry.formatted_date)
            item_crc = QTableWidgetItem(f"{entry.crc:08X}" if not entry.is_dir else "-")

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
            self.table.setItem(row, 2, item_comp)
            self.table.setItem(row, 3, item_ratio)
            self.table.setItem(row, 4, item_date)
            self.table.setItem(row, 5, item_crc)

    def _apply_filter(self):
        self._populate_table()

    def _test_integrity(self):
        self.integrity_label.setText(t("Integrität wird geprüft..."))
        self.test_btn.setEnabled(False)

        self.test_worker = ArchiveTestWorker(self.zip_path, parent=self)
        self.test_worker.finished.connect(self._on_test_finished)
        self.test_worker.start()

    @Slot(bool, str)
    def _on_test_finished(self, is_valid: bool, msg: str):
        self.test_btn.setEnabled(True)
        if is_valid:
            self.integrity_label.setText("✅ " + t("Archiv ist fehlerfrei (CRC-Prüfung bestanden)"))
            self.integrity_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self.integrity_label.setText("❌ " + t("Integritätsfehler: ") + msg)
            self.integrity_label.setStyleSheet("color: #c62828; font-weight: bold;")

    def _extract_all(self):
        dlg = ArchiveExtractDialog(self.zip_path, parent=self)
        dlg.exec()

    def _extract_selected(self):
        selected_rows = set()
        for idx in self.table.selectedIndexes():
            selected_rows.add(idx.row())

        if not selected_rows:
            QMessageBox.information(
                self,
                t("Auswahl erforderlich"),
                t("Bitte wählen Sie zuerst die zu entpackenden Dateien in der Tabelle aus.")
            )
            return

        selected_members = []
        for r in selected_rows:
            item = self.table.item(r, 0)
            if item:
                fname = item.data(Qt.ItemDataRole.UserRole)
                if fname:
                    selected_members.append(fname)

        folder = QFileDialog.getExistingDirectory(
            self,
            t("Zielverzeichnis für ausgewählte Dateien"),
            os.path.dirname(self.zip_path)
        )
        if not folder:
            return

        worker = ArchiveExtractWorker(
            self.zip_path,
            folder,
            members=selected_members,
            overwrite=True,
            parent=self
        )
        worker.start()
        worker.wait()
        QMessageBox.information(
            self,
            t("Auswahl entpackt"),
            t("Die ausgewählten Dateien wurden erfolgreich entpackt nach:\n") + folder
        )
