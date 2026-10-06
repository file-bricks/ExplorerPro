#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
properties_dialog.py - Detaillierter Datei- und Ordner-Eigenschaften-Dialog
========================================================================
Zeigt Dateisystem-Attribute, Metadaten, rekursive Ordnergrößen, Zeitstempel,
Berechtigungen und kryptografische Prüfsummen (SHA-256, MD5) an.
"""

from __future__ import annotations

import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.checksum_service import compute_file_hashes
from core.file_icon_helper import get_file_icon
from core.platform_utils import open_path_with_system
from translator import t


def format_size(num_bytes: int) -> str:
    """Formatiert Byte-Werte lesbar mit Tausendertrennpunkten und passender Einheit."""
    if num_bytes < 0:
        return "0 Bytes"
    if num_bytes < 1024:
        return f"{num_bytes:,} Bytes".replace(",", ".")
    for unit, factor in [("KB", 1024), ("MB", 1024**2), ("GB", 1024**3), ("TB", 1024**4)]:
        if num_bytes < factor * 1024:
            val = num_bytes / factor
            val_str = f"{val:.2f}".replace(".", ",")
            return f"{num_bytes:,} Bytes ({val_str} {unit})".replace(",", ".")
    val = num_bytes / (1024**4)
    val_str = f"{val:.2f}".replace(".", ",")
    return f"{num_bytes:,} Bytes ({val_str} TB)".replace(",", ".")


def calculate_folder_stats(folder_path: str, max_files: int = 100_000) -> Tuple[int, int, int]:
    """
    Berechnet rekursiv Dateianzahl, Ordneranzahl und Gesamtgröße eines Verzeichnisses.
    Gibt (file_count, dir_count, total_bytes) zurück.
    """
    file_count = 0
    dir_count = 0
    total_bytes = 0

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return (0, 0, 0)

    try:
        for root, dirs, files in os.walk(folder_path, followlinks=False):
            dir_count += len(dirs)
            for f in files:
                file_count += 1
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except (OSError, PermissionError):
                    pass
                if file_count >= max_files:
                    break
            if file_count >= max_files:
                break
    except (OSError, PermissionError):
        pass

    return (file_count, dir_count, total_bytes)


class FilePropertiesDialog(QDialog):
    """Eigenschaften-Dialog für Dateien und Ordner mit Detailreitern."""

    def __init__(self, target_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.target_path = os.path.abspath(target_path)
        self.is_dir = os.path.isdir(self.target_path)
        self.filename = os.path.basename(self.target_path) or self.target_path

        title_label = t("Eigenschaften von {name}").replace("{name}", self.filename)
        self.setWindowTitle(title_label)
        self.setMinimumWidth(520)
        self.setMinimumHeight(440)
        self.setModal(True)
        self.setAccessibleName(t("Datei-Eigenschaften Dialog"))
        self.setAccessibleDescription(
            t("Zeigt detaillierte Datei- und Ordnereigenschaften, Zeitstempel, Prüfsummen und Berechtigungen an.")
        )

        self._setup_ui()
        self._load_properties()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Header: Icon + Name
        header_layout = QHBoxLayout()
        self.icon_label = QLabel(self)
        icon = get_file_icon(self.target_path)
        pixmap = icon.pixmap(QSize(48, 48))
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setFixedSize(52, 52)
        header_layout.addWidget(self.icon_label)

        name_layout = QVBoxLayout()
        self.name_edit = QLineEdit(self.filename, self)
        self.name_edit.setReadOnly(True)
        self.name_edit.setFont(QFont("", 11, QFont.Weight.Bold))
        self.name_edit.setAccessibleName(t("Elementname"))
        name_layout.addWidget(self.name_edit)

        self.type_subtitle = QLabel(self)
        self.type_subtitle.setStyleSheet("color: gray;")
        name_layout.addWidget(self.type_subtitle)

        header_layout.addLayout(name_layout, 1)
        main_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setAccessibleName(t("Eigenschaften-Reiter"))

        # Tab 1: Allgemein
        self.tab_general = QWidget(self)
        self.form_general = QFormLayout(self.tab_general)
        self.form_general.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.form_general.setSpacing(8)
        self.tabs.addTab(self.tab_general, t("Allgemein"))

        # Tab 2: Prüfsummen / Statistik
        self.tab_checksums = QWidget(self)
        self.layout_checksums = QVBoxLayout(self.tab_checksums)
        self.layout_checksums.setSpacing(10)
        self.tabs.addTab(self.tab_checksums, t("Prüfsummen & Details"))

        main_layout.addWidget(self.tabs, 1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        self.copy_path_btn = QPushButton(t("📋 Pfad kopieren"), self)
        self.copy_path_btn.setToolTip(t("Vollständigen Dateipfad in die Zwischenablage kopieren"))
        self.copy_path_btn.clicked.connect(self._copy_full_path)
        btn_layout.addWidget(self.copy_path_btn)

        self.open_location_btn = QPushButton(t("📂 Im Dateimanager öffnen"), self)
        self.open_location_btn.setToolTip(t("Speicherort im System-Dateimanager anzeigen"))
        self.open_location_btn.clicked.connect(self._open_location)
        btn_layout.addWidget(self.open_location_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton(t("Schließen"), self)
        self.close_btn.setDefault(True)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(btn_layout)

    def _load_properties(self) -> None:
        """Liest Attribute vom Dateisystem und befüllt die Reiter."""
        if not os.path.exists(self.target_path):
            self.type_subtitle.setText(t("Element nicht gefunden"))
            return

        try:
            st = os.stat(self.target_path)
        except OSError as exc:
            self.type_subtitle.setText(t("Fehler beim Lesen: {error}").format(error=exc))
            return

        # Dateityp ermitteln
        ext = Path(self.target_path).suffix.lower()
        if self.is_dir:
            type_str = t("Dateiordner")
        elif ext:
            type_str = t("{type}-Datei ({extension})").format(type=ext[1:].upper(), extension=ext)
        else:
            type_str = t("Datei")
        self.type_subtitle.setText(type_str)

        # Tab 1: Formular befüllen
        self._add_form_row(t("Dateityp:"), type_str)

        location_edit = QLineEdit(os.path.dirname(self.target_path), self)
        location_edit.setReadOnly(True)
        self.form_general.addRow(QLabel(t("Speicherort:")), location_edit)

        if self.is_dir:
            file_count, dir_count, total_bytes = calculate_folder_stats(self.target_path)
            size_str = format_size(total_bytes)
            contains_str = t("{files} Dateien, {folders} Ordner").format(
                files=f"{file_count:,}", folders=f"{dir_count:,}"
            ).replace(",", ".")
            self._add_form_row(t("Größe:"), size_str)
            self._add_form_row(t("Inhalt:"), contains_str)
        else:
            self._add_form_row(t("Größe:"), format_size(st.st_size))

        # Zeitstempel
        try:
            created_dt = datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            created_dt = t("Unbekannt")
        try:
            modified_dt = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            modified_dt = t("Unbekannt")
        try:
            accessed_dt = datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            accessed_dt = t("Unbekannt")

        self._add_form_row(t("Erstellt:"), created_dt)
        self._add_form_row(t("Geändert:"), modified_dt)
        self._add_form_row(t("Letzter Zugriff:"), accessed_dt)

        # Attribute
        is_readonly = not os.access(self.target_path, os.W_OK)
        is_hidden = self.filename.startswith(".")
        if sys.platform.startswith("win"):
            try:
                attrs = getattr(st, "st_file_attributes", 0)
                if attrs & stat.FILE_ATTRIBUTE_HIDDEN:
                    is_hidden = True
            except AttributeError:
                pass

        attr_parts = []
        if is_readonly:
            attr_parts.append(t("Schreibgeschützt"))
        else:
            attr_parts.append(t("Schreibbar"))
        if is_hidden:
            attr_parts.append(t("Versteckt"))
        mode_octal = oct(stat.S_IMODE(st.st_mode))
        attr_parts.append(f"POSIX {mode_octal}")

        self._add_form_row(t("Attribute:"), ", ".join(attr_parts))

        # Tab 2: Prüfsummen & Details
        if not self.is_dir and os.path.isfile(self.target_path):
            self._setup_file_checksums(st.st_size)
        else:
            self._setup_folder_details()

    def _add_form_row(self, label_text: str, value_text: str) -> None:
        val_lbl = QLabel(value_text, self)
        val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.form_general.addRow(QLabel(label_text), val_lbl)

    def _setup_file_checksums(self, file_size: int) -> None:
        # GroupBox Prüfsummen
        group_hash = QGroupBox(t("Kryptografische Prüfsummen"), self)
        form_hash = QFormLayout(group_hash)
        form_hash.setSpacing(8)

        # SHA-256
        self.sha256_edit = QLineEdit(self)
        self.sha256_edit.setReadOnly(True)
        self.sha256_edit.setFont(QFont("Courier New", 9))
        btn_copy_sha = QPushButton(t("Kopieren"), self)
        btn_copy_sha.clicked.connect(lambda: self._copy_to_clip(self.sha256_edit.text()))
        row_sha = QHBoxLayout()
        row_sha.addWidget(self.sha256_edit, 1)
        row_sha.addWidget(btn_copy_sha)
        form_hash.addRow(QLabel("SHA-256:"), row_sha)

        # MD5
        self.md5_edit = QLineEdit(self)
        self.md5_edit.setReadOnly(True)
        self.md5_edit.setFont(QFont("Courier New", 9))
        btn_copy_md5 = QPushButton(t("Kopieren"), self)
        btn_copy_md5.clicked.connect(lambda: self._copy_to_clip(self.md5_edit.text()))
        row_md5 = QHBoxLayout()
        row_md5.addWidget(self.md5_edit, 1)
        row_md5.addWidget(btn_copy_md5)
        form_hash.addRow(QLabel("MD5:"), row_md5)

        self.layout_checksums.addWidget(group_hash)

        # Hashes berechnen (falls Datei <= 50 MB direkt, sonst per Button)
        if file_size <= 50 * 1024 * 1024:
            try:
                hashes = compute_file_hashes(self.target_path, algorithms=("sha256", "md5"))
                self.sha256_edit.setText(hashes.get("sha256", ""))
                self.md5_edit.setText(hashes.get("md5", ""))
            except Exception as exc:
                self.sha256_edit.setText(t("Fehler: {error}").format(error=exc))
                self.md5_edit.setText(t("Fehler: {error}").format(error=exc))
        else:
            self.sha256_edit.setPlaceholderText(t("Datei > 50 MB: Klick zum Berechnen"))
            self.md5_edit.setPlaceholderText(t("Datei > 50 MB: Klick zum Berechnen"))
            calc_btn = QPushButton(t("Prüfsummen jetzt berechnen"), self)
            calc_btn.clicked.connect(self._compute_large_hashes)
            self.layout_checksums.addWidget(calc_btn)

        # Text-Dateistatistik
        ext = Path(self.target_path).suffix.lower()
        text_extensions = {".txt", ".py", ".md", ".json", ".xml", ".html", ".css", ".js", ".yaml", ".yml", ".ini", ".log"}
        if ext in text_extensions and file_size <= 5 * 1024 * 1024:
            self._setup_text_stats()

        self.layout_checksums.addStretch()

    def _compute_large_hashes(self) -> None:
        try:
            hashes = compute_file_hashes(self.target_path, algorithms=("sha256", "md5"))
            self.sha256_edit.setText(hashes.get("sha256", ""))
            self.md5_edit.setText(hashes.get("md5", ""))
        except Exception as exc:
            QMessageBox.warning(self, t("Prüfsummen-Fehler"), str(exc))

    def _setup_text_stats(self) -> None:
        try:
            with open(self.target_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            line_count = len(lines)
            word_count = sum(len(line.split()) for line in lines)
            char_count = sum(len(line) for line in lines)

            group_text = QGroupBox(t("Text-Metriken"), self)
            form_text = QFormLayout(group_text)
            form_text.addRow(QLabel(t("Zeilen:")), QLabel(f"{line_count:,}".replace(",", ".")))
            form_text.addRow(QLabel(t("Wörter:")), QLabel(f"{word_count:,}".replace(",", ".")))
            form_text.addRow(QLabel(t("Zeichen:")), QLabel(f"{char_count:,}".replace(",", ".")))
            self.layout_checksums.addWidget(group_text)
        except Exception:
            pass

    def _setup_folder_details(self) -> None:
        group_info = QGroupBox(t("Ordner-Struktur"), self)
        form_info = QFormLayout(group_info)
        rel_path = os.path.relpath(self.target_path, os.path.dirname(self.target_path))
        form_info.addRow(QLabel(t("Relativer Pfad:")), QLabel(rel_path))
        self.layout_checksums.addWidget(group_info)
        self.layout_checksums.addStretch()

    def _copy_full_path(self) -> None:
        self._copy_to_clip(self.target_path)
        QMessageBox.information(
            self,
            t("Pfad kopiert"),
            t("Vollständiger Pfad in die Zwischenablage kopiert:\n\n{path}").format(path=self.target_path)
        )

    def _copy_to_clip(self, text: str) -> None:
        if text:
            QApplication.clipboard().setText(text)

    def _open_location(self) -> None:
        target = os.path.dirname(self.target_path) if not self.is_dir else self.target_path
        try:
            open_path_with_system(target)
        except Exception as exc:
            QMessageBox.warning(self, t("Dateimanager öffnen"), t("Konnte Ordner nicht öffnen:\n{error}").format(error=exc))
