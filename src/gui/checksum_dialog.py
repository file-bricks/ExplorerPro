#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChecksumDialog - Dialog zur Anzeige, Berechnung und Verifikation von Prüfsummen (MD5, SHA-1, SHA-256, SHA-512)
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QProgressBar, QApplication,
    QMessageBox
)
from PySide6.QtCore import Slot
from PySide6.QtGui import QFont

from core.checksum_service import ChecksumWorker, verify_hash


class ChecksumDialog(QDialog):
    """Prüfsummen-Dialog für Dateien."""

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.worker = None
        self._calculated_hashes = {}

        filename = os.path.basename(filepath)
        self.setWindowTitle(f"Prüfsummen — {filename}")
        self.setMinimumWidth(580)
        self.setAccessibleName("Prüfsummen-Dialog")
        self.setAccessibleDescription(
            "Berechnet MD5, SHA-1, SHA-256 und SHA-512 Prüfsummen und ermöglicht den Vergleich."
        )

        self._setup_ui()
        self._start_calculation()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Datei-Info
        info_group = QGroupBox("📄 Datei-Information")
        info_layout = QFormLayout(info_group)

        self.path_label = QLabel(self.filepath)
        self.path_label.setWordWrap(True)
        info_layout.addRow("Pfad:", self.path_label)

        size_bytes = os.path.getsize(self.filepath) if os.path.isfile(self.filepath) else 0
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB ({size_bytes:,} Bytes)"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024*1024):.2f} MB ({size_bytes:,} Bytes)"
        else:
            size_str = f"{size_bytes / (1024*1024*1024):.2f} GB ({size_bytes:,} Bytes)"

        self.size_label = QLabel(size_str)
        info_layout.addRow("Größe:", self.size_label)
        layout.addWidget(info_group)

        # Fortschritt
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Prüfsummen-Gruppe
        hashes_group = QGroupBox("🔑 Berechnete Prüfsummen")
        hashes_layout = QFormLayout(hashes_group)
        hashes_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        mono_font = QFont("Consolas", 9)

        self.hash_edits = {}
        for algo in ("md5", "sha1", "sha256", "sha512"):
            row_layout = QHBoxLayout()
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setFont(mono_font)
            edit.setPlaceholderText("Wird berechnet...")
            edit.setAccessibleName(f"{algo.upper()} Prüfsumme")
            self.hash_edits[algo] = edit
            row_layout.addWidget(edit, 1)

            btn = QPushButton("Kopieren")
            btn.setToolTip(f"{algo.upper()} in Zwischenablage kopieren")
            btn.clicked.connect(lambda checked=False, a=algo: self._copy_hash(a))
            row_layout.addWidget(btn)

            label_text = f"{algo.upper()}:"
            hashes_layout.addRow(label_text, row_layout)

        # Alle Kopieren Button
        self.copy_all_btn = QPushButton("📋 Alle Prüfsummen kopieren")
        self.copy_all_btn.clicked.connect(self._copy_all_hashes)
        self.copy_all_btn.setEnabled(False)
        hashes_layout.addRow("", self.copy_all_btn)

        layout.addWidget(hashes_group)

        # Verifikation
        verify_group = QGroupBox("🔍 Prüfsumme vergleichen")
        verify_layout = QVBoxLayout(verify_group)

        verify_hint = QLabel("Fügen Sie einen erwarteten Hash-Wert ein, um die Integrität zu prüfen:")
        verify_layout.addWidget(verify_hint)

        self.verify_edit = QLineEdit()
        self.verify_edit.setFont(mono_font)
        self.verify_edit.setPlaceholderText("Erwarteten Hash hier einfügen...")
        self.verify_edit.setClearButtonEnabled(True)
        self.verify_edit.textChanged.connect(self._on_verify_text_changed)
        verify_layout.addWidget(self.verify_edit)

        self.verify_result_label = QLabel("Berechnung läuft...")
        self.verify_result_label.setStyleSheet("font-weight: bold; padding: 4px;")
        verify_layout.addWidget(self.verify_result_label)

        layout.addWidget(verify_group)

        # Dialog-Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.close_btn = QPushButton("Schließen")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _start_calculation(self):
        if not os.path.isfile(self.filepath):
            self.progress_bar.setVisible(False)
            self.verify_result_label.setText("Fehler: Datei existiert nicht mehr.")
            self.verify_result_label.setStyleSheet("color: red; font-weight: bold;")
            return

        self.worker = ChecksumWorker(self.filepath, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    @Slot(int, int)
    def _on_progress(self, bytes_read: int, total_bytes: int):
        if total_bytes > 0:
            percent = int((bytes_read / total_bytes) * 100)
            self.progress_bar.setValue(percent)

    @Slot(dict)
    def _on_finished(self, results: dict):
        self._calculated_hashes = results
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Fertig (100%)")
        self.copy_all_btn.setEnabled(True)

        for algo, val in results.items():
            if algo in self.hash_edits:
                self.hash_edits[algo].setText(val)

        self._on_verify_text_changed(self.verify_edit.text())

    @Slot(str)
    def _on_error(self, error_msg: str):
        self.progress_bar.setFormat("Fehlgeschlagen")
        self.verify_result_label.setText(f"Fehler: {error_msg}")
        self.verify_result_label.setStyleSheet("color: red; font-weight: bold;")

    def _copy_hash(self, algo: str):
        val = self._calculated_hashes.get(algo, "")
        if val:
            QApplication.clipboard().setText(val)

    def _copy_all_hashes(self):
        if not self._calculated_hashes:
            return
        filename = os.path.basename(self.filepath)
        lines = [
            f"Datei: {filename}",
            f"Pfad:  {self.filepath}",
            f"Größe: {os.path.getsize(self.filepath):,} Bytes",
            "-" * 40,
        ]
        for algo in ("md5", "sha1", "sha256", "sha512"):
            if algo in self._calculated_hashes:
                lines.append(f"{algo.upper():6}: {self._calculated_hashes[algo]}")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self,
            "Kopiert",
            "Alle Prüfsummen wurden formatiert in die Zwischenablage kopiert."
        )

    @Slot(str)
    def _on_verify_text_changed(self, text: str):
        text = text.strip()
        if not self._calculated_hashes:
            self.verify_result_label.setText("Warte auf Abschluss der Berechnung...")
            self.verify_result_label.setStyleSheet("color: #666; font-style: italic;")
            return

        if not text:
            self.verify_result_label.setText("Bereit zur Verifikation.")
            self.verify_result_label.setStyleSheet("color: #666; font-style: italic;")
            return

        match = verify_hash(self._calculated_hashes, text)
        if match:
            algo, _ = match
            self.verify_result_label.setText(f"✓ Übereinstimmung gefunden! ({algo.upper()})")
            self.verify_result_label.setStyleSheet("color: #0d8050; font-weight: bold;")
        else:
            self.verify_result_label.setText("✗ Keine Übereinstimmung mit berechneten Prüfsummen.")
            self.verify_result_label.setStyleSheet("color: #c00000; font-weight: bold;")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(500)
        super().closeEvent(event)
