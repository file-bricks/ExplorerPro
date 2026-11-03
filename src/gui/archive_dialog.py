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

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout
)

from core.archive_service import (
    ArchiveCompressWorker, ArchiveExtractWorker, ArchiveTestWorker,
    format_bytes, inspect_archive
)
from translator import t



def _get_archive_stem(path: str) -> str:
    """Ermittelt den Stammnamen ohne Archiv-Endung (unterstützt auch .tar.gz etc.)."""
    name = os.path.basename(path)
    for sfx in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz", ".zip", ".tar"):
        if name.lower().endswith(sfx):
            return name[:-len(sfx)]
    return Path(path).stem


class _ArchiveWorkerShutdownGuard(QObject):
    """Hält das Qt-Ereignisloop offen, bis Archiv-Threads sicher beendet sind."""

    def __init__(self, app):
        super().__init__(app)
        self._app = app
        self._workers = {}
        self._quit_pending = False
        self._allow_next_quit = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(20)
        self._poll_timer.timeout.connect(self._poll_workers)
        app.installEventFilter(self)

    def belongs_to(self, app) -> bool:
        return self._app is app

    def track(self, worker):
        self._workers[id(worker)] = worker
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def _running_workers(self):
        running = []
        stopped = []
        for worker_id, worker in tuple(self._workers.items()):
            try:
                if worker.isRunning():
                    running.append(worker)
                else:
                    stopped.append(worker_id)
            except RuntimeError:
                stopped.append(worker_id)
        for worker_id in stopped:
            self._workers.pop(worker_id, None)
        return running

    def eventFilter(self, watched, event):
        if watched is self._app and event.type() == QEvent.Type.Quit:
            if self._allow_next_quit:
                self._allow_next_quit = False
                return False
            running = self._running_workers()
            if running:
                event.ignore()
                self._quit_pending = True
                for worker in running:
                    owner = worker.parent()
                    if isinstance(owner, _ThreadAwareDialog):
                        owner.done(QDialog.DialogCode.Rejected)
                    cancel = getattr(worker, "cancel", None)
                    if callable(cancel):
                        cancel()
                if not self._poll_timer.isActive():
                    self._poll_timer.start()
                return True
        return super().eventFilter(watched, event)

    @Slot()
    def _poll_workers(self):
        if self._running_workers():
            return
        self._poll_timer.stop()
        if self._quit_pending:
            self._quit_pending = False
            self._allow_next_quit = True
            QTimer.singleShot(0, self._app.quit)


_archive_worker_shutdown_guard = None


def _track_archive_worker(worker):
    """Behält gestartete Archiv-Threads auch über ein QApplication.quit hinweg."""
    global _archive_worker_shutdown_guard
    app = QApplication.instance()
    if app is None:
        return
    if (
        _archive_worker_shutdown_guard is None
        or not _archive_worker_shutdown_guard.belongs_to(app)
    ):
        _archive_worker_shutdown_guard = _ArchiveWorkerShutdownGuard(app)
    _archive_worker_shutdown_guard.track(worker)


class _ThreadAwareDialog(QDialog):
    """Schließt einen Dialog erst, wenn seine QThread-Kinder beendet sind."""

    _worker_attributes = ("worker", "test_worker", "extract_worker")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_close_result = None
        self._close_poll_timer = QTimer(self)
        self._close_poll_timer.setInterval(20)
        self._close_poll_timer.timeout.connect(self._finish_pending_close)

    def _running_workers(self):
        workers = []
        seen = set()
        for attr_name in self._worker_attributes:
            worker = getattr(self, attr_name, None)
            if worker is None or id(worker) in seen:
                continue
            seen.add(id(worker))
            try:
                if worker.isRunning():
                    workers.append(worker)
            except RuntimeError:
                continue
        return workers

    def done(self, result: int):
        running = self._running_workers()
        if running:
            if self._pending_close_result is None:
                self._pending_close_result = result
            for worker in running:
                cancel = getattr(worker, "cancel", None)
                if callable(cancel):
                    cancel()
            self._close_poll_timer.start()
            return

        self._close_poll_timer.stop()
        if self._pending_close_result is not None:
            result = self._pending_close_result
            self._pending_close_result = None
        super().done(result)

    @Slot()
    def _finish_pending_close(self):
        if self._running_workers():
            return
        self._close_poll_timer.stop()
        result = self._pending_close_result
        self._pending_close_result = None
        if result is not None:
            super().done(result)

    def closeEvent(self, event):
        if self._running_workers():
            event.ignore()
            self.done(QDialog.DialogCode.Rejected)
            return
        super().closeEvent(event)

    def _when_worker_stops(self, worker, callback):
        if worker is not None and worker.isRunning():
            QTimer.singleShot(
                20,
                lambda: self._when_worker_stops(worker, callback),
            )
            return
        callback()


class ArchiveCompressDialog(_ThreadAwareDialog):
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
            t("Ziel-Archivdatei auswählen"),
            curr_text or os.path.join(init_dir, "Archiv.zip"),
            t("Alle unterstützten Archive (*.zip *.tar *.tar.gz *.tgz *.tar.bz2 *.tbz2 *.tar.xz *.txz);;ZIP-Archive (*.zip);;TAR-Archive (*.tar *.tar.gz *.tgz *.tar.bz2 *.tbz2 *.tar.xz *.txz);;Alle Dateien (*.*)")
        )
        if path:
            lower = path.lower()
            if not any(lower.endswith(ext) for ext in (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
                path += ".zip"
            self.dest_edit.setText(path)

    def _start_compression(self):
        dest_path = self.dest_edit.text().strip()
        if not dest_path:
            QMessageBox.warning(self, t("Fehler"), t("Bitte geben Sie einen Zielpfad an."))
            return

        lower = dest_path.lower()
        if not any(lower.endswith(ext) for ext in (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
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
        _track_archive_worker(self.worker)
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
        self._when_worker_stops(
            self.worker,
            lambda: self._finish_compression(success, dest_path, count, total_bytes),
        )

    def _finish_compression(self, success: bool, dest_path: str, count: int, total_bytes: int):
        if self._pending_close_result is not None:
            return
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
        if self._pending_close_result is not None:
            return
        QMessageBox.critical(self, t("Fehler beim Komprimieren"), f"{err_msg}")

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText(t("Wird abgebrochen..."))
        self.reject()


class ArchiveExtractDialog(_ThreadAwareDialog):
    """Dialog zum sicheren Entpacken eines ZIP-Archivs."""

    def __init__(self, zip_path: str, default_target_dir: str = "", parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.default_target_dir = default_target_dir or os.path.dirname(zip_path)
        self.worker: Optional[ArchiveExtractWorker] = None
        self.extracted_target: Optional[str] = None

        self.setWindowTitle(t("Archiv entpacken"))
        self.setMinimumWidth(560)
        self.setAccessibleName(t("Archiv entpacken"))
        self.setAccessibleDescription(
            t("Ermöglicht das sichere Entpacken eines Archivs in ein Zielverzeichnis.")
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
            summary, _ = inspect_archive(self.zip_path)
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

        stem = _get_archive_stem(self.zip_path)
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
            stem = _get_archive_stem(self.zip_path)
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
        _track_archive_worker(self.worker)
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
        self._when_worker_stops(
            self.worker,
            lambda: self._finish_extraction(success, target_dir, count, total_bytes),
        )

    def _finish_extraction(self, success: bool, target_dir: str, count: int, total_bytes: int):
        if self._pending_close_result is not None:
            return
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
        if self._pending_close_result is not None:
            return
        QMessageBox.critical(self, t("Fehler beim Entpacken"), f"{err_msg}")

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText(t("Wird abgebrochen..."))
        self.reject()


class ArchiveViewerDialog(_ThreadAwareDialog):
    """Vollständiger Archiv-Inspektor mit Metadaten, Suche und CRC-Integritätstest."""

    def __init__(self, zip_path: str, parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.summary = None
        self.entries = []
        self.test_worker: Optional[ArchiveTestWorker] = None
        self.extract_worker: Optional[ArchiveExtractWorker] = None
        self._extract_error: Optional[str] = None

        filename = os.path.basename(zip_path)
        self.setWindowTitle(t("Archiv durchsuchen — ") + filename)
        self.resize(780, 520)
        self.setAccessibleName(t("Archiv-Inspektor-Dialog"))
        self.setAccessibleDescription(
            t("Zeigt den Inhalt des Archivs mit Dateigrößen, Kompressionsraten und Prüfoptionen.")
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
            self.summary, self.entries = inspect_archive(self.zip_path)
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
            self.stats_label.setText(f"{t('Fehler:')} {exc}")
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
        if self.test_worker is not None and self.test_worker.isRunning():
            return
        self.integrity_label.setText(t("Integrität wird geprüft..."))
        self.test_btn.setEnabled(False)

        self.test_worker = ArchiveTestWorker(self.zip_path, parent=self)
        _track_archive_worker(self.test_worker)
        self.test_worker.finished.connect(self._on_test_finished)
        self.test_worker.start()

    @Slot(bool, str)
    def _on_test_finished(self, is_valid: bool, msg: str):
        self._when_worker_stops(
            self.test_worker,
            lambda: self._finish_integrity_test(is_valid, msg),
        )

    def _finish_integrity_test(self, is_valid: bool, msg: str):
        if self._pending_close_result is not None:
            return
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

        if self.extract_worker is not None and self.extract_worker.isRunning():
            return

        self._extract_error = None
        self.extract_selected_btn.setEnabled(False)
        self.extract_all_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self.integrity_label.setText(t("Entpacken wird gestartet..."))
        self.extract_worker = ArchiveExtractWorker(
            self.zip_path,
            folder,
            members=selected_members,
            overwrite=True,
            parent=self
        )
        _track_archive_worker(self.extract_worker)
        self.extract_worker.error.connect(self._on_selected_extract_error)
        self.extract_worker.finished.connect(
            lambda success, target, count, total: self._on_selected_extract_finished(
                success, target, count, total
            )
        )
        self.extract_worker.start()

    @Slot(str)
    def _on_selected_extract_error(self, err_msg: str):
        self._extract_error = err_msg

    @Slot(bool, str, int, int)
    def _on_selected_extract_finished(
        self, success: bool, target_dir: str, count: int, total_bytes: int
    ):
        self._when_worker_stops(
            self.extract_worker,
            lambda: self._finish_selected_extraction(
                success, target_dir, count, total_bytes
            ),
        )

    def _finish_selected_extraction(
        self, success: bool, target_dir: str, count: int, total_bytes: int
    ):
        if self._pending_close_result is not None:
            return
        self.extract_selected_btn.setEnabled(True)
        self.extract_all_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        if success:
            self.integrity_label.setText(t("Erfolgreich entpackt"))
            QMessageBox.information(
                self,
                t("Auswahl entpackt"),
                t("Die ausgewählten Dateien wurden erfolgreich entpackt nach:\n")
                + target_dir,
            )
        else:
            message = self._extract_error or t("Vorgang abgebrochen.")
            self.integrity_label.setText(t("Entpacken fehlgeschlagen.") + " " + message)
            QMessageBox.critical(self, t("Fehler beim Entpacken"), message)


class ArchiveExtractProgressDialog(_ThreadAwareDialog):
    """Nicht blockierender Fortschrittsdialog für direktes Entpacken."""

    completed = Signal(bool)

    def __init__(self, zip_path: str, target_dir: str, parent=None):
        super().__init__(parent)
        self._extract_error: Optional[str] = None
        self._cancel_requested = False
        self.setWindowTitle(t("Archiv entpacken"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        self.status_label = QLabel(t("Entpacken wird gestartet..."))
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)
        self.cancel_btn = QPushButton(t("Abbrechen"))
        self.cancel_btn.clicked.connect(self._cancel)
        layout.addWidget(self.cancel_btn)

        self.worker = ArchiveExtractWorker(zip_path, target_dir, parent=self)
        _track_archive_worker(self.worker)
        self.worker.progress.connect(self._on_progress)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)
        self.status_label.setText(filename or t("Entpacken wird gestartet..."))

    @Slot(str)
    def _on_error(self, err_msg: str):
        self._extract_error = err_msg

    @Slot(bool, str, int, int)
    def _on_finished(self, success: bool, target_dir: str, count: int, total_bytes: int):
        self._when_worker_stops(
            self.worker,
            lambda: self._finish(success, target_dir, count, total_bytes),
        )

    def _finish(self, success: bool, target_dir: str, count: int, total_bytes: int):
        if self._pending_close_result is not None:
            self.completed.emit(False)
            return
        if success:
            self.completed.emit(True)
            QMessageBox.information(
                self,
                t("Archiv entpackt"),
                t("Erfolgreich entpackt") + ":\n" + target_dir,
            )
            self.accept()
            return

        if self._cancel_requested and not self._extract_error:
            self.status_label.setText(t("Vorgang abgebrochen."))
            self.completed.emit(False)
            self.reject()
            return

        message = self._extract_error or t("Vorgang abgebrochen.")
        self.status_label.setText(t("Entpacken fehlgeschlagen.") + " " + message)
        self.completed.emit(False)
        QMessageBox.critical(self, t("Fehler beim Entpacken"), message)
        self.reject()

    def _cancel(self):
        if self.worker.isRunning():
            self._cancel_requested = True
            self.worker.cancel()
            self.status_label.setText(t("Wird abgebrochen..."))
            self.cancel_btn.setEnabled(False)


class ArchiveIntegrityProgressDialog(_ThreadAwareDialog):
    """Nicht blockierender CRC-Prüfdialog für ZIP-Archive."""

    def __init__(self, zip_path: str, parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.setWindowTitle(t("Integritätsprüfung"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        self.status_label = QLabel(t("Integrität wird geprüft..."))
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)
        self.close_btn = QPushButton(t("Schließen"))
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)

        self.test_worker = ArchiveTestWorker(zip_path, parent=self)
        _track_archive_worker(self.test_worker)
        self.test_worker.finished.connect(self._on_finished)
        self.test_worker.start()

    @Slot(bool, str)
    def _on_finished(self, is_valid: bool, message: str):
        self._when_worker_stops(
            self.test_worker,
            lambda: self._finish(is_valid, message),
        )

    def _finish(self, is_valid: bool, message: str):
        if self._pending_close_result is not None:
            return
        self.progress_bar.setVisible(False)
        self.close_btn.setText(t("Fertig"))
        if is_valid:
            self.status_label.setText(t("Archiv ist fehlerfrei (CRC-Prüfung bestanden)"))
            QMessageBox.information(
                self,
                t("Integritätsprüfung"),
                t("Archiv ist fehlerfrei (CRC-Prüfung bestanden)")
                + "\n"
                + os.path.basename(self.zip_path),
            )
        else:
            self.status_label.setText(t("Integritätsfehler: ") + message)
            QMessageBox.warning(
                self,
                t("Integritätsprüfung"),
                t("Integritätsfehler: ") + message,
            )
