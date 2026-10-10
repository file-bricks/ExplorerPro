#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileBrowser - Dateilisten-Ansicht mit QuickEditor-Integration
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView,
    QMenu, QAbstractItemView, QMessageBox, QFileSystemModel,
    QApplication, QInputDialog, QDialog, QLabel
)
from PySide6.QtCore import (
    Qt, Signal, QDir, QModelIndex, QSortFilterProxyModel,
    QStandardPaths, QUrl, QMimeData, QSize, QTimer
)
from PySide6.QtGui import QAction, QCursor, QDrag, QKeySequence
import os
import subprocess
import shutil
import sys
from pathlib import Path

from core.async_fs import AsyncFs
from core.platform_utils import open_path_with_system, normalize_user_path, drive_kind
from translator import t

# Editor-Extensions
EDITOR_EXTENSIONS = {
    '.py', '.pyw', '.js', '.jsx', '.ts', '.tsx',
    '.html', '.htm', '.css', '.scss', '.less',
    '.json', '.xml', '.yaml', '.yml', '.toml',
    '.md', '.txt', '.rst', '.ini', '.cfg',
    '.sql', '.sh', '.bash', '.bat', '.ps1',
    '.c', '.cpp', '.h', '.hpp', '.java',
    '.rb', '.php', '.go', '.rs', '.swift'
}


def base_entry_filters() -> QDir.Filter:
    """Filter für die Dateiliste.

    Unter Windows blendet Qt ohne ``QDir.System`` Einträge aus, die weder als
    Datei noch als Ordner erkannt werden. Das betrifft u. a. OneDrive-/Cloud-
    Platzhalter (Reparse-Points mit Cloud-Tag) und Verknüpfungen (*.lnk).
    """
    filters = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
    if sys.platform.startswith("win"):
        filters |= QDir.Filter.System
    return filters


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _classify(path: str):
    """Blocking stat calls (worker): 'file', 'dir' or None."""
    if os.path.isfile(path):
        return "file"
    return "dir" if os.path.isdir(path) else None


def _probe(path: str) -> bool:
    """A listing proves the drive answers right now (worker)."""
    os.listdir(path)
    return True


class _DnDTableView(QTableView):
    """QTableView-Unterklasse: delegiert DnD-Events und Tastatur-Shortcuts an den FileBrowser.

    Notwendig, weil QAbstractItemView.startDrag() und keyPressEvent
    C++-virtuelle Methoden sind, die sich sauber durch Subclassing überschreiben lassen.
    """

    def __init__(self, file_browser, parent=None):
        super().__init__(parent)
        self._fb = file_browser

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self._fb._handle_url_drop(event)
        else:
            super().dropEvent(event)

    def startDrag(self, supported_actions):
        self._fb._start_drag_files(supported_actions)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fb._ensure_name_column_visible()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._fb.delete_selection()
            event.accept()
        elif event.key() == Qt.Key.Key_F2:
            self._fb.rename_selection()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            self._fb.show_properties()
            event.accept()
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) and event.key() == Qt.Key.Key_C:
            self._fb.copy_path_to_clipboard()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self._fb.copy_selection()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self._fb.paste_from_clipboard()
            event.accept()
        else:
            super().keyPressEvent(event)



class FileBrowser(QWidget):
    """
    Datei-Browser mit Tabellen-Ansicht
    Integriert QuickEditor für Code-Dateien
    """

    # Standardbreiten für Größe, Typ, Änderungsdatum (Pixel)
    COLUMN_WIDTHS = {1: 90, 2: 150, 3: 135}
    MIN_NAME_WIDTH = 160

    # Signale
    file_selected = Signal(str)
    folder_changed = Signal(str)
    path_changed = Signal(str)          # Für Toolbar & StatusBar
    selection_changed = Signal(int)     # Anzahl ausgewählter Dateien
    file_double_clicked = Signal(str)
    edit_requested = Signal(str)        # Datei im Editor öffnen

    # Switching to a path nobody has proven reachable is validated in a worker, so a
    # dead/slow drive never blocks the GUI. Paths in _known_dirs go straight in.
    ASYNC_VALIDATE = True
    NAV_TIMEOUT_MS = 15000
    PRELOAD_TIMEOUT_MS = 15000
    PRELOAD_GAP_MS = 300  # throttle between two drive preloads

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""
        self._history = []
        self._history_index = -1
        self._file_count = 0
        self._known_dirs = set()
        self._tokens = {}           # token -> (kind, path)
        self._nav_token = 0
        self._preload_queue = []
        self._preload_busy = False
        self._preload_seq = 0
        self._fs = AsyncFs(self)
        self._fs.finished.connect(self._on_fs_result)
        self._setup_ui()
        self._busy = QLabel(t("wird geladen …"), self.table.viewport())
        self._busy.hide()

        # Startverzeichnis (Einstellung "Startordner", sonst Benutzerordner)
        self._navigate_sync(self.default_start_path())

    @staticmethod
    def default_start_path() -> str:
        """Startordner aus den Einstellungen oder das Benutzerverzeichnis."""
        home = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.HomeLocation
        )
        try:
            from core.settings_manager import SettingsManager

            configured = SettingsManager.instance().get("general", "start_folder", "") or ""
        except Exception:
            configured = ""
        if isinstance(configured, str) and configured.strip():
            candidate = normalize_user_path(configured)
            if os.path.isdir(candidate):
                return candidate
        return home

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Datei-System-Model
        self.model = QFileSystemModel(self)
        self.model.setFilter(base_entry_filters())
        self.model.directoryLoaded.connect(self._on_directory_loaded)

        # Sortier-Proxy
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # Tabellen-View (DnD-fähige Unterklasse für startDrag-Override)
        self.table = _DnDTableView(self)
        self.table.setModel(self.proxy)

        # Spalten konfigurieren
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        # System-Icons: explizite Größe damit die Icons in Spalte 0 sichtbar
        # dargestellt werden (QFileSystemModel liefert sie über QFileIconProvider).
        self.table.setIconSize(QSize(16, 16))
        # Lange Namen in der Mitte kürzen, damit Anfang und Endung lesbar bleiben.
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setWordWrap(False)

        # Header: Die Namensspalte erhält den Restplatz. Die übrigen Spalten
        # haben feste, vom Nutzer veränderbare Breiten. Mit ResizeToContents
        # konnten lange Typbezeichnungen ("Komprimierter (gezippter) Ordner")
        # die Namensspalte auf wenige Pixel zusammendrücken – sichtbar blieb
        # dann nur noch der Typ "Ordner" statt des Ordnernamens.
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(48)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in self.COLUMN_WIDTHS.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(column, width)

        # Signale
        self.table.clicked.connect(self._on_item_clicked)
        self.table.doubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Selection-Signal
        self.table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        # Drag-and-Drop aktivieren
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.table.setDropIndicatorShown(True)
        self.table.setAccessibleName("Dateiliste")
        self.table.setAccessibleDescription(
            "Tabelle der Dateien und Ordner im aktuellen Verzeichnis. "
            "Navigieren mit Pfeiltasten, Öffnen mit Enter oder Doppelklick."
        )
        self.table.setToolTip("Dateien und Ordner im aktuellen Verzeichnis")
        self.setAcceptDrops(True)   # Widget-Level als Fallback für Randbereich

        layout.addWidget(self.table)

    def _ensure_name_column_visible(self):
        """Verkleinert Zusatzspalten, wenn sonst kein Platz für Namen bleibt."""
        header = self.table.horizontalHeader()
        available = self.table.viewport().width()
        if available <= 0:
            return
        others = [c for c in self.COLUMN_WIDTHS if not self.table.isColumnHidden(c)]
        used = sum(header.sectionSize(c) for c in others)
        overflow = used + self.MIN_NAME_WIDTH - available
        if overflow <= 0:
            return
        # Zuerst den Typ, dann das Datum, zuletzt die Größe verkleinern.
        for column in (2, 3, 1):
            if overflow <= 0 or column not in others:
                continue
            size = header.sectionSize(column)
            shrink = min(overflow, max(0, size - header.minimumSectionSize()))
            if shrink:
                header.resizeSection(column, size - shrink)
                overflow -= shrink

    def _on_directory_loaded(self, path: str):
        """Handler wenn Verzeichnis geladen wurde"""
        if os.path.normcase(os.path.normpath(path)) == os.path.normcase(os.path.normpath(self._current_path or "")):
            self._busy.hide()
            self._update_file_count()
            self.selection_changed.emit(len(self.get_selected_files()))

    def _update_file_count(self):
        """Aktualisiert die Anzahl sichtbarer Einträge.

        Zählt die Zeilen des (asynchron geladenen) Modells statt das
        Verzeichnis erneut synchron im GUI-Thread aufzulisten – bei Netzwerk-
        und Cloud-Ordnern blockierte das zuvor die Oberfläche.
        """
        if not self._current_path:
            self._file_count = 0
            return
        root = self.model.index(self._current_path)
        self._file_count = self.model.rowCount(root) if root.isValid() else 0

    def _on_selection_changed(self):
        """Handler für Auswahl-Änderungen"""
        selected = len(self.get_selected_files())
        self.selection_changed.emit(selected)

    def navigate_to(self, path: str):
        """Navigiert zu einem Pfad; unbekannte Pfade werden im Hintergrund geprüft."""
        if not path:
            return
        path = normalize_user_path(path)
        if _norm(path) in self._known_dirs:
            self._go(path)
        elif not self.ASYNC_VALIDATE:
            self._navigate_sync(path)
        else:
            self._nav_token += 1
            self._set_busy(t("wird geladen …"))
            self._submit(self._nav_token, "nav", path, _classify, self.NAV_TIMEOUT_MS)

    def _set_busy(self, text):
        if text:
            self._busy.setText(text)
            self._busy.adjustSize()
            self._busy.move(12, 40)
            self._busy.show()
            self._busy.raise_()
        else:
            self._busy.hide()

    def _submit(self, token, kind, path, fn, timeout_ms):
        self._tokens[token] = (kind, path)
        self._fs.submit(token, fn, path)
        QTimer.singleShot(timeout_ms, lambda: self._on_timeout(token))

    def _on_fs_result(self, token, result, error):
        entry = self._tokens.pop(token, None)
        if entry is None:  # timed out: a late answer is dropped
            return
        kind, path = entry
        if kind == "preload":
            self._preload_busy = False
            if error is None and result:
                self._known_dirs.add(_norm(path))
                index = self.model.index(path)  # just proved reachable: cheap now
                if index.isValid():
                    self.model.fetchMore(index)  # warm the model for an instant first view
            QTimer.singleShot(self.PRELOAD_GAP_MS, self._preload_next)
            return
        if error is not None or result is None:
            if token == self._nav_token:
                self._set_busy(None)
            return
        folder = path if result == "dir" else os.path.dirname(path)
        self._known_dirs.add(_norm(folder))
        if token != self._nav_token:  # the user went elsewhere meanwhile
            return
        self._set_busy(None)
        self._go(folder)
        if result == "file":
            self.file_selected.emit(path)

    def _on_timeout(self, token):
        entry = self._tokens.pop(token, None)
        if entry is None:
            return
        if entry[0] == "preload":
            self._preload_busy = False
            QTimer.singleShot(self.PRELOAD_GAP_MS, self._preload_next)
        elif token == self._nav_token:
            self._set_busy(t("Keine Antwort – Laufwerk reagiert nicht"))

    def preload_roots(self, paths):
        """Warm the start page of each drive in the background: local disks first, one at a time."""
        queued = [p for p in self._preload_queue]
        for path in sorted(paths, key=drive_kind):
            if path not in queued and _norm(path) not in self._known_dirs:
                self._preload_queue.append(path)
        self._preload_next()

    def _preload_next(self):
        if self._preload_busy or not self._preload_queue:
            return
        path = self._preload_queue.pop(0)
        self._preload_busy = True
        self._preload_seq -= 1  # negative tokens: never confused with user navigations
        self._submit(self._preload_seq, "preload", path, _probe, self.PRELOAD_TIMEOUT_MS)

    def _navigate_sync(self, path: str):
        if os.path.isfile(path):
            # Datei-Pfad (z. B. aus Suche oder Adresszeile): Ordner öffnen
            # und die Datei anschließend markieren.
            folder = os.path.dirname(path)
            if folder and os.path.isdir(folder):
                self._navigate_sync(folder)
                self.file_selected.emit(path)
            return
        if not os.path.isdir(path):
            return
        self._go(path)

    def _go(self, path: str):
        """Switch the view; callers have established that *path* is a reachable folder."""
        for folder in (Path(path), *Path(path).parents):  # ancestors exist too: "up" is instant
            self._known_dirs.add(_norm(str(folder)))

        # History aktualisieren
        if self._current_path and self._current_path != path:
            # Vorwärts-History löschen
            self._history = self._history[:self._history_index + 1]
            self._history.append(path)
            self._history_index = len(self._history) - 1
        elif not self._history:
            self._history.append(path)
            self._history_index = 0

        self._current_path = path

        # QFileSystemModel loads directories asynchronously. index(path) alone
        # can point at a valid directory while its rows remain empty forever.
        source_index = self.model.setRootPath(path)
        proxy_index = self.proxy.mapFromSource(source_index)
        self.table.setRootIndex(proxy_index)

        self._update_file_count()
        # Nothing cached yet: say so until the (asynchronous) listing arrives.
        self._set_busy(t("wird geladen …") if self.model.rowCount(source_index) == 0 else None)

        # Signale senden
        self.folder_changed.emit(path)
        self.path_changed.emit(path)

    def go_back(self):
        """Geht einen Schritt zurück"""
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._current_path = path
            source_index = self.model.setRootPath(path)
            proxy_index = self.proxy.mapFromSource(source_index)
            self.table.setRootIndex(proxy_index)
            self._update_file_count()
            self.folder_changed.emit(path)
            self.path_changed.emit(path)

    def go_forward(self):
        """Geht einen Schritt vorwärts"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._current_path = path
            source_index = self.model.setRootPath(path)
            proxy_index = self.proxy.mapFromSource(source_index)
            self.table.setRootIndex(proxy_index)
            self._update_file_count()
            self.folder_changed.emit(path)
            self.path_changed.emit(path)

    def go_up(self):
        """Geht zum übergeordneten Ordner"""
        if self._current_path:
            parent = os.path.dirname(self._current_path)
            if parent and parent != self._current_path:
                self.navigate_to(parent)

    def refresh(self):
        """Aktualisiert die Ansicht"""
        if self._current_path:
            source_index = self.model.setRootPath(self._current_path)
            self.table.setRootIndex(self.proxy.mapFromSource(source_index))
            self._update_file_count()

    def set_icon_size(self, size: int):
        """Setzt die Größe der Dateisymbole (Einstellung "Symbolgröße")."""
        size = max(12, min(64, int(size)))
        self.table.setIconSize(QSize(size, size))
        self.table.verticalHeader().setDefaultSectionSize(
            max(size + 6, self.table.fontMetrics().height() + 6)
        )

    def set_show_hidden_files(self, show: bool):
        """Schaltet die Anzeige versteckter Dateien um."""
        filters = base_entry_filters()
        if show:
            filters |= QDir.Filter.Hidden
        self.model.setFilter(filters)
        self.refresh()

    def _on_item_clicked(self, index: QModelIndex):
        source_index = self.proxy.mapToSource(index)
        file_path = self.model.filePath(source_index)

        if os.path.isfile(file_path):
            self.file_selected.emit(file_path)

    def _on_item_double_clicked(self, index: QModelIndex):
        source_index = self.proxy.mapToSource(index)
        file_path = self.model.filePath(source_index)

        if os.path.isdir(file_path):
            self.navigate_to(file_path)
        else:
            # Prüfe ob Editor-Datei
            ext = Path(file_path).suffix.lower()
            if ext in EDITOR_EXTENSIONS:
                self._edit_file(file_path)
            else:
                self._open_file(file_path)

    def _show_context_menu(self, pos):
        """Zeigt das Kontextmenü"""
        index = self.table.indexAt(pos)

        menu = QMenu(self)

        if index.isValid():
            # A right click on another row must act on that row, not on an old selection.
            if not self.table.selectionModel().isRowSelected(index.row(), index.parent()):
                self.table.selectRow(index.row())
            source_index = self.proxy.mapToSource(index)
            file_path = self.model.filePath(source_index)
            is_file = os.path.isfile(file_path)
            ext = Path(file_path).suffix.lower() if is_file else ""

            # Öffnen
            open_action = QAction("📂 Öffnen", self)
            open_action.triggered.connect(lambda: self._open_file(file_path))
            menu.addAction(open_action)

            if is_file and ext in EDITOR_EXTENSIONS:
                edit_action = QAction("✏️ In Editor öffnen", self)
                edit_action.setShortcut("F4")
                edit_action.triggered.connect(lambda: self._edit_file(file_path))
                menu.addAction(edit_action)

            if is_file:
                checksum_action = QAction("🔑 Prüfsummen berechnen...", self)
                checksum_action.triggered.connect(lambda: self._show_checksums(file_path))
                menu.addAction(checksum_action)

            if is_file and ext == ".zip":
                archive_view_action = QAction("📦 Archiv durchsuchen...", self)
                archive_view_action.triggered.connect(lambda: self._view_archive(file_path))
                menu.addAction(archive_view_action)

                archive_extract_here_action = QAction("📦 Hier entpacken (in Unterordner)", self)
                archive_extract_here_action.triggered.connect(lambda: self._extract_archive_here(file_path))
                menu.addAction(archive_extract_here_action)

                archive_extract_action = QAction("📦 Entpacken nach...", self)
                archive_extract_action.triggered.connect(lambda: self._extract_archive(file_path))
                menu.addAction(archive_extract_action)

                archive_test_action = QAction("🧪 Integrität prüfen", self)
                archive_test_action.triggered.connect(lambda: self._test_archive_integrity(file_path))
                menu.addAction(archive_test_action)

            menu.addSeparator()

            # Index-Aktionen
            index_action = QAction("🔍 In Index suchen", self)
            index_action.triggered.connect(lambda: self._search_in_index(file_path))
            menu.addAction(index_action)

            meta_action = QAction("📊 Metadaten anzeigen", self)
            meta_action.triggered.connect(lambda: self._show_metadata(file_path))
            menu.addAction(meta_action)

            tags_action = QAction("🏷️ Tags bearbeiten", self)
            tags_action.triggered.connect(lambda: self._show_metadata(file_path, focus_tags=True))
            menu.addAction(tags_action)

            menu.addSeparator()

            # Sync
            sync_action = QAction("🔄 Synchronisieren", self)
            sync_action.triggered.connect(lambda: self._sync_path(file_path))
            menu.addAction(sync_action)

            prompt_action = QAction("📋 Pfad als Prompt speichern", self)
            prompt_action.triggered.connect(lambda: self._save_path_as_prompt(file_path))
            menu.addAction(prompt_action)

            menu.addSeparator()

            # Datenschutz
            privacy_action = QAction("🛡️ Datenschutz prüfen", self)
            privacy_action.triggered.connect(lambda: self._check_privacy(file_path))
            menu.addAction(privacy_action)

            blacklist_action = QAction("🔴 Zur Blacklist hinzufügen", self)
            blacklist_action.triggered.connect(lambda: self._add_to_blacklist(file_path))
            menu.addAction(blacklist_action)

            menu.addSeparator()

            # Standard-Aktionen
            selected = self.get_selected_files()
            if len(selected) > 1:
                batch_action = QAction("✏️ Mehrfach umbenennen...", self)
                batch_action.triggered.connect(lambda: self._show_batch_rename(selected))
                menu.addAction(batch_action)

            if len(selected) == 2:
                diff_action = QAction("⚖️ Dateien vergleichen (Diff)...", self)
                diff_action.triggered.connect(lambda: self._show_diff(selected[0], selected[1]))
                menu.addAction(diff_action)

            compress_action = QAction("📦 Zu ZIP-Archiv komprimieren...", self)
            compress_action.triggered.connect(lambda: self._compress_selection(selected if selected else [file_path]))
            menu.addAction(compress_action)

            copy_action = QAction("Kopieren", self)
            copy_action.setShortcut("Ctrl+C")
            copy_action.triggered.connect(self.copy_selection)
            menu.addAction(copy_action)

            delete_action = QAction("Löschen", self)
            delete_action.setShortcut("Delete")
            delete_action.triggered.connect(lambda: self.delete_selection(selected if selected else [file_path]))
            menu.addAction(delete_action)

            rename_action = QAction("Umbenennen", self)
            rename_action.setShortcut("F2")
            rename_action.triggered.connect(lambda: self.rename_selection(file_path))
            menu.addAction(rename_action)

            menu.addSeparator()

            copy_path_action = QAction("📋 Pfad kopieren", self)
            copy_path_action.setShortcut("Ctrl+Shift+C")
            copy_path_action.triggered.connect(lambda: self.copy_path_to_clipboard())
            menu.addAction(copy_path_action)

            if not is_file or os.path.isdir(file_path):
                term_action = QAction("💻 Im Terminal öffnen", self)
                term_action.triggered.connect(lambda: self.open_terminal(file_path))
                menu.addAction(term_action)

            prop_action = QAction("ℹ️ Eigenschaften...", self)
            prop_action.setShortcut("Alt+Enter")
            prop_action.triggered.connect(lambda: self.show_properties(file_path))
            menu.addAction(prop_action)

        else:
            # Leer-Bereich-Menü
            new_file = QAction("📄 Neue Datei...", self)
            new_file.triggered.connect(self.create_new_file)
            menu.addAction(new_file)

            new_folder = QAction("📁 Neuer Ordner", self)
            new_folder.triggered.connect(self.create_new_folder)
            menu.addAction(new_folder)

            diff_action = QAction("⚖️ Dateien vergleichen...", self)
            diff_action.triggered.connect(lambda: self._show_diff())
            menu.addAction(diff_action)

            compress_dir_action = QAction("📦 Ordnerinhalt als ZIP komprimieren...", self)
            compress_dir_action.triggered.connect(self._compress_current_folder)
            menu.addAction(compress_dir_action)

            extract_zip_action = QAction("📦 ZIP-Archiv hier entpacken...", self)
            extract_zip_action.triggered.connect(self._extract_zip_dialog)
            menu.addAction(extract_zip_action)

            menu.addSeparator()

            copy_dir_path_action = QAction("📋 Ordnerpfad kopieren", self)
            copy_dir_path_action.triggered.connect(lambda: self.copy_path_to_clipboard())
            menu.addAction(copy_dir_path_action)

            term_here_action = QAction("💻 Terminal hier öffnen", self)
            term_here_action.triggered.connect(lambda: self.open_terminal())
            menu.addAction(term_here_action)

            menu.addSeparator()

            paste_action = QAction("Einfügen", self)
            paste_action.setShortcut("Ctrl+V")
            paste_action.triggered.connect(self.paste_from_clipboard)
            menu.addAction(paste_action)

            menu.addSeparator()

            prop_dir_action = QAction("ℹ️ Eigenschaften...", self)
            prop_dir_action.setShortcut("Alt+Enter")
            prop_dir_action.triggered.connect(lambda: self.show_properties(self._current_path))
            menu.addAction(prop_dir_action)

            menu.addSeparator()

            refresh_action = QAction("Aktualisieren", self)
            refresh_action.setShortcut("F5")
            refresh_action.triggered.connect(self.refresh)
            menu.addAction(refresh_action)


        menu.exec(QCursor.pos())

    def _open_file(self, path: str):
        """Öffnet eine Datei/Ordner mit System-Standard"""
        if os.path.isdir(path):
            self.navigate_to(path)
            return

        try:
            open_path_with_system(path)
        except (OSError, subprocess.CalledProcessError) as exc:
            QMessageBox.warning(
                self,
                t("Datei öffnen"),
                t("Die Datei konnte nicht geöffnet werden:") + f"\n{path}\n\n{exc}"
            )

    def _edit_file(self, path: str):
        """Öffnet Datei im QuickEditor"""
        from modules.editor.quick_editor import QuickEditorDialog

        editor = QuickEditorDialog(path, self.window())
        editor.exec()

    def _show_metadata(self, path: str, focus_tags: bool = False):
        """Zeigt Metadaten/Tags im (ggf. ausgeblendeten) Vorschau-Panel des Hauptfensters."""
        main_win = self.window()
        if hasattr(main_win, "show_file_metadata"):
            main_win.show_file_metadata(path, focus_tags=focus_tags)
        else:
            self.file_selected.emit(path)

    def _show_checksums(self, path: str):
        """Öffnet den Prüfsummen-Dialog für eine Datei"""
        if not os.path.isfile(path):
            return
        from gui.checksum_dialog import ChecksumDialog

        dialog = ChecksumDialog(path, self.window())
        dialog.exec()

    def _check_privacy(self, path: str):
        """Prüft Datei auf sensible Daten"""
        if not os.path.isfile(path):
            return

        try:
            # Nur Text-Dateien prüfen
            ext = Path(path).suffix.lower()
            if ext not in EDITOR_EXTENSIONS and ext not in {'.csv', '.log'}:
                QMessageBox.information(
                    self, "Datenschutz",
                    "Datenschutz-Prüfung nur für Text-Dateien verfügbar."
                )
                return

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Max 50KB

            # PrivacyMonitor vom Hauptfenster holen
            main_window = self.window()
            if hasattr(main_window, 'privacy_monitor'):
                alert = main_window.privacy_monitor.check_text(content)

                if alert.detected_patterns:
                    QMessageBox.warning(
                        self, t("Datenschutz-Prüfung"),
                        t("Status: {status}").format(status=alert.status.value.upper()) + "\n\n"
                        + t("Erkannte Muster:") + "\n• "
                        + "\n• ".join(alert.detected_patterns)
                    )
                else:
                    QMessageBox.information(
                        self, "Datenschutz-Prüfung",
                        "✅ Keine sensiblen Daten erkannt."
                    )
        except Exception as e:
            QMessageBox.warning(
                self, t("Fehler"),
                t("Konnte Datei nicht prüfen: {error}").format(error=e)
            )

    @property
    def current_path(self) -> str:
        return self._current_path

    @property
    def file_count(self) -> int:
        return self._file_count

    def get_selected_files(self) -> list:
        """Gibt ausgewählte Dateien zurück"""
        selected = []
        for index in self.table.selectedIndexes():
            if index.column() == 0:
                source_index = self.proxy.mapToSource(index)
                path = self.model.filePath(source_index)
                selected.append(path)
        return selected

    def copy_selection(self) -> bool:
        """Kopiert ausgewählte Dateien/Ordner in die Zwischenablage."""
        paths = self.get_selected_files()
        if not paths:
            return False
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime_data.setText("\n".join(paths))
        QApplication.clipboard().setMimeData(mime_data)
        return True

    def copy_path_to_clipboard(self, relative: bool = False, name_only: bool = False) -> str:
        """Kopiert ausgewählte Dateipfade oder den aktuellen Ordnerpfad als Reintext in die Zwischenablage."""
        paths = self.get_selected_files()
        if not paths and self._current_path:
            paths = [self._current_path]
        if not paths:
            return ""

        if name_only:
            result_paths = [os.path.basename(p) for p in paths]
        elif relative and self._current_path:
            result_paths = [os.path.relpath(p, self._current_path) for p in paths]
        else:
            result_paths = paths

        text = "\n".join(result_paths)
        QApplication.clipboard().setText(text)
        return text

    def show_properties(self, target_path: str = None) -> bool:
        """Öffnet den detaillierten Eigenschaften-Dialog für Datei oder Ordner."""
        if not target_path:
            selected = self.get_selected_files()
            target_path = selected[0] if selected else self._current_path

        if not target_path or not os.path.exists(target_path):
            return False

        from gui.properties_dialog import FilePropertiesDialog
        dialog = FilePropertiesDialog(target_path, self.window())
        dialog.exec()
        return True

    def open_terminal(self, target_path: str = None) -> bool:
        """Öffnet ein Terminalfenster im angegebenen Verzeichnis oder aktuellen Ordner."""
        if not target_path:
            selected = self.get_selected_files()
            if selected and os.path.isdir(selected[0]):
                target_path = selected[0]
            else:
                target_path = self._current_path

        if not target_path or not os.path.exists(target_path):
            return False

        from core.platform_utils import open_terminal_in_directory
        try:
            open_terminal_in_directory(target_path)
            return True
        except Exception as exc:
            QMessageBox.warning(
                self,
                t("Terminal öffnen"),
                t("Konnte Terminal nicht öffnen:") + f"\n{exc}"
            )
            return False


    def paste_from_clipboard(self) -> bool:
        """Fügt Dateien/Ordner aus der Zwischenablage in den aktuellen Ordner ein."""
        if not self._current_path:
            return False
        mime_data = QApplication.clipboard().mimeData()
        if not mime_data or not mime_data.hasUrls():
            return False
        src_paths = [
            url.toLocalFile()
            for url in mime_data.urls()
            if url.isLocalFile()
        ]
        if not src_paths:
            return False
        self._do_file_drop(src_paths, self._current_path, move=False)
        return True

    def create_new_folder(self) -> bool:
        """Erstellt einen neuen Unterordner im aktuellen Verzeichnis."""
        if not self._current_path or not os.path.exists(self._current_path):
            return False
        name, ok = QInputDialog.getText(
            self, "Neuer Ordner", "Ordnername:"
        )
        if not ok or not name or not name.strip():
            return False
        name = name.strip()
        new_path = os.path.join(self._current_path, name)
        try:
            os.makedirs(new_path, exist_ok=False)
            self.refresh()
            return True
        except FileExistsError:
            QMessageBox.warning(
                self, t("Neuer Ordner"),
                t("Ein Ordner oder eine Datei mit dem Namen '{name}' existiert bereits.").format(name=name)
            )
            return False
        except OSError as exc:
            QMessageBox.warning(
                self, t("Neuer Ordner"),
                t("Konnte Ordner nicht erstellen:") + f"\n{exc}"
            )
            return False

    def create_new_file(self) -> bool:
        """Erstellt eine neue leere Datei im aktuellen Verzeichnis."""
        if not self._current_path or not os.path.exists(self._current_path):
            return False
        default_name = "neue_datei.txt"
        name, ok = QInputDialog.getText(
            self, "Neue Datei", "Dateiname:", text=default_name
        )
        if not ok or not name or not name.strip():
            return False
        name = name.strip()
        new_path = os.path.join(self._current_path, name)
        try:
            # Datei atomar mit Modus 'x' anlegen (verhindert Überschreiben)
            with open(new_path, "x", encoding="utf-8"):
                pass
            self.refresh()
            self.file_selected.emit(new_path)
            return True
        except FileExistsError:
            QMessageBox.warning(
                self, t("Neue Datei"),
                t("Ein Element namens '{name}' existiert bereits in diesem Verzeichnis.").format(name=name)
            )
            return False
        except OSError as exc:
            QMessageBox.warning(
                self, t("Neue Datei"),
                t("Konnte Datei nicht erstellen:") + f"\n{exc}"
            )
            return False

    def rename_selection(self, target_path: str = None) -> bool:
        """Benennt die ausgewählte Datei oder den ausgewählten Ordner um."""
        selected = self.get_selected_files()
        if not target_path and len(selected) > 1:
            return self._show_batch_rename(selected)

        if not target_path:
            if not selected:
                return False
            target_path = selected[0]

        if not os.path.exists(target_path):
            return False

        old_name = os.path.basename(target_path)
        parent_dir = os.path.dirname(target_path)

        new_name, ok = QInputDialog.getText(
            self, "Umbenennen", "Neuer Name:", text=old_name
        )
        if not ok or not new_name or not new_name.strip() or new_name.strip() == old_name:
            return False

        new_name = new_name.strip()
        new_path = os.path.join(parent_dir, new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(
                self, t("Umbenennen"),
                t("Ein Element namens '{name}' existiert bereits in diesem Verzeichnis.").format(name=new_name)
            )
            return False

        try:
            os.rename(target_path, new_path)
            self.refresh()
            return True
        except OSError as exc:
            QMessageBox.warning(
                self, t("Umbenennen"),
                t("Konnte Element nicht umbenennen:") + f"\n{exc}"
            )
            return False

    def _show_batch_rename(self, file_paths: list = None) -> bool:
        """Öffnet den Batch-Rename-Dialog."""
        if not file_paths:
            file_paths = self.get_selected_files()
        if not file_paths:
            QMessageBox.information(
                self, "Mehrfach umbenennen",
                "Bitte wählen Sie mindestens eine Datei zum Umbenennen aus."
            )
            return False
        from gui.batch_rename_dialog import BatchRenameDialog
        dialog = BatchRenameDialog(file_paths, self.window())
        res = dialog.exec()
        self.refresh()
        return res == QDialog.DialogCode.Accepted

    def _show_diff(self, file1: str = "", file2: str = ""):
        """Öffnet den Datei-Vergleichs-Dialog."""
        from gui.diff_dialog import DiffDialog
        dialog = DiffDialog(file1, file2, self.window())
        dialog.exec()

    def delete_selection(self, target_paths: list = None) -> bool:
        """Delete selected entries, using the trash when confirmation is disabled."""
        from core.delete_service import delete_path, move_to_trash
        from core.settings_manager import SettingsManager

        if not target_paths:
            target_paths = self.get_selected_files()
        if not target_paths:
            return False

        count = len(target_paths)
        if count == 1:
            msg = t("Möchten Sie '{name}' wirklich unwiderruflich löschen?").format(
                name=os.path.basename(target_paths[0])
            )
        else:
            preview = "\n".join(f"• {os.path.basename(p)}" for p in target_paths[:5])
            if count > 5:
                preview += "\n" + t("... und {count} weitere").format(count=count - 5)
            msg = t("Möchten Sie diese {count} Elemente wirklich unwiderruflich löschen?").format(
                count=count
            ) + f"\n\n{preview}"

        confirm_delete = SettingsManager.instance().get("general", "confirm_delete", True) is not False
        if confirm_delete:
            reply = QMessageBox.question(
                self,
                t("Löschen bestätigen"),
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        errors = []
        delete_item = delete_path if confirm_delete else move_to_trash
        for path in target_paths:
            if not os.path.lexists(path):
                continue
            try:
                delete_item(path)
            except OSError as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

        self.refresh()
        if errors:
            QMessageBox.warning(
                self, t("Fehler beim Löschen"),
                t("Folgende Elemente konnten nicht gelöscht werden:") + "\n\n" + "\n".join(errors)
            )
            return False
        return True

    def _search_in_index(self, path: str):
        """Sucht nach dem Dateinamen im Index."""
        filename = os.path.basename(path)
        main_win = self.window()
        if hasattr(main_win, 'toolbar') and hasattr(main_win.toolbar, 'search_edit'):
            main_win.toolbar.search_edit.setText(filename)
            if hasattr(main_win, '_on_search'):
                main_win._on_search(filename)
            elif hasattr(main_win.toolbar, 'search_requested'):
                main_win.toolbar.search_requested.emit(filename)

    def _save_path_as_prompt(self, path: str):
        """Speichert den Pfad als Prompt in der Bibliothek oder im Clipboard."""
        main_win = self.window()
        filename = os.path.basename(path)
        is_file = os.path.isfile(path)
        content = (
            t("Analysiere bitte folgende Datei:") if is_file else t("Analysiere bitte folgenden Ordner:")
        ) + f"\n{path}"
        title = t("Pfad: {name}").format(name=filename)

        if hasattr(main_win, 'sidebar') and hasattr(main_win.sidebar, 'prompts_panel'):
            prompts_panel = main_win.sidebar.prompts_panel
            from modules.prompts.prompts_panel import Prompt
            category = "Code" if Path(path).suffix.lower() in EDITOR_EXTENSIONS else "Allgemein"
            p = Prompt(id="", title=title, content=content, category=category, tags=["pfad", "analyse"])
            prompts_panel.prompts.append(p)
            prompts_panel._save_prompts()
            prompts_panel._refresh_list()
            if hasattr(main_win, 'show_prompts_panel'):
                main_win.show_prompts_panel()
            QMessageBox.information(
                self, t("Prompt gespeichert"),
                t("Prompt für '{name}' wurde in der Bibliothek gespeichert.").format(name=filename)
            )
        else:
            QApplication.clipboard().setText(content)
            QMessageBox.information(
                self, t("Prompt in Zwischenablage"),
                t("Prompt-Vorlage für '{name}' in die Zwischenablage kopiert.").format(name=filename)
            )

    def _add_to_blacklist(self, path: str):
        """Fügt den Dateinamen zur Datenschutz-Blacklist hinzu."""
        filename = os.path.basename(path)
        main_win = self.window()
        if hasattr(main_win, 'privacy_monitor') and main_win.privacy_monitor:
            main_win.privacy_monitor.add_to_blacklist(filename)
            QMessageBox.information(
                self, t("Datenschutz"),
                t("'{name}' wurde zur Datenschutz-Blacklist hinzugefügt.").format(name=filename)
                + "\n\n" + t("Die Liste kann über einen Klick auf die Datenschutz-Ampel bearbeitet werden.")
            )
        else:
            QMessageBox.information(
                self, t("Datenschutz"),
                t("'{name}' konnte nicht hinzugefügt werden: Datenschutz-Monitor nicht initialisiert.").format(
                    name=filename
                )
            )

    def _sync_path(self, path: str):
        """Öffnet das Sync-Panel und legt ein Sync-Paar mit dem Pfad als Quelle an."""
        main_win = self.window()
        if hasattr(main_win, 'show_sync_panel'):
            main_win.show_sync_panel()
        sidebar = getattr(main_win, 'sidebar', None)
        if sidebar is not None and hasattr(sidebar, 'sync_panel'):
            sidebar.sync_panel.add_pair_for_path(path)

    # ------------------------------------------------------------------ #
    # Drag-and-Drop                                                        #
    # ------------------------------------------------------------------ #

    def dragEnterEvent(self, event):
        """Akzeptiert externe URL-Drops auf dem Widget-Randbereich."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Hält den Drop-Vorgang aktiv solange URLs erkannt werden."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Verarbeitet eingehende Drops auf dem Widget-Randbereich."""
        self._handle_url_drop(event)

    def _handle_url_drop(self, event):
        """Gemeinsamer Handler für URL-Drops (Tabelle und Widget-Rand).

        Wird von _DnDTableView.dropEvent und FileBrowser.dropEvent aufgerufen.
        """
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        if not self._current_path:
            event.ignore()
            return

        src_paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]
        if not src_paths:
            event.ignore()
            return

        move = (event.proposedAction() == Qt.DropAction.MoveAction)
        self._do_file_drop(src_paths, self._current_path, move=move)
        event.acceptProposedAction()

    def _start_drag_files(self, supported_actions):
        """Initiiert einen Drag-out mit den aktuell ausgewählten Dateien.

        Wird von _DnDTableView.startDrag aufgerufen.
        """
        paths = self.get_selected_files()
        if not paths:
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(p) for p in paths])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

    def _do_file_drop(self, src_paths: list, target_dir: str, move: bool = False):
        """Kopiert oder verschiebt Dateien in den Zielordner ohne Überschreiben."""
        errors = []
        target_real = os.path.normcase(os.path.realpath(target_dir))

        for src in src_paths:
            src = os.path.normpath(src)
            if not os.path.exists(src):
                errors.append(t("Quelle nicht gefunden: {path}").format(path=src))
                continue

            src_real = os.path.normcase(os.path.realpath(src))
            if os.path.isdir(src):
                try:
                    target_is_within_source = (
                        os.path.commonpath([src_real, target_real]) == src_real
                    )
                except ValueError:
                    target_is_within_source = False
                if target_is_within_source:
                    errors.append(
                        f"{os.path.basename(src)}: "
                        + t("Ordner kann nicht in seinen eigenen Unterordner kopiert oder verschoben werden.")
                    )
                    continue
            elif os.path.normcase(os.path.realpath(os.path.dirname(src))) == target_real:
                continue

            name = os.path.basename(src)
            base, ext = os.path.splitext(name)
            dest = os.path.join(target_dir, name)
            collision_index = 0
            while os.path.exists(dest):
                collision_index += 1
                suffix = "_copy" if collision_index == 1 else f"_copy_{collision_index}"
                dest = os.path.join(target_dir, f"{base}{suffix}{ext}")

            try:
                if move:
                    shutil.move(src, dest)
                elif os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            except (OSError, shutil.Error) as exc:
                errors.append(f"{name}: {exc}")

        self.refresh()

        if errors:
            QMessageBox.warning(
                self,
                t("Drag & Drop"),
                t("Einige Dateien konnten nicht übertragen werden:") + "\n\n"
                + "\n".join(errors),
            )

    def _compress_selection(self, paths: list = None):
        """Öffnet den Dialog zum Komprimieren ausgewählter Dateien/Ordner."""
        selected = paths or self.get_selected_files()
        if not selected and self._current_path:
            selected = [self._current_path]
        if not selected:
            return
        from gui.archive_dialog import ArchiveCompressDialog
        dlg = ArchiveCompressDialog(selected, current_dir=self._current_path, parent=self.window())
        if dlg.exec():
            self.refresh()

    def _compress_current_folder(self):
        """Komprimiert den aktuellen Ordner als ZIP-Archiv."""
        if not self._current_path or not os.path.isdir(self._current_path):
            return
        from gui.archive_dialog import ArchiveCompressDialog
        dlg = ArchiveCompressDialog(
            [self._current_path],
            current_dir=os.path.dirname(self._current_path),
            parent=self.window()
        )
        if dlg.exec():
            self.refresh()

    def _extract_archive(self, zip_path: str):
        """Öffnet den Dialog zum Entpacken des gewählten Archivs."""
        if not os.path.isfile(zip_path):
            return
        from gui.archive_dialog import ArchiveExtractDialog
        dlg = ArchiveExtractDialog(
            zip_path,
            default_target_dir=self._current_path,
            parent=self.window()
        )
        if dlg.exec():
            self.refresh()

    def _extract_archive_here(self, zip_path: str):
        """Entpackt das Archiv direkt in einen gleichnamigen Unterordner am aktuellen Ort."""
        if not os.path.isfile(zip_path):
            return
        from core.archive_service import ArchiveExtractWorker
        stem = Path(zip_path).stem
        target_dir = os.path.join(self._current_path, stem)

        worker = ArchiveExtractWorker(zip_path, target_dir, parent=self)
        worker.start()
        worker.wait()
        self.refresh()
        QMessageBox.information(
            self,
            "Archiv entpackt",
            f"Archiv wurde erfolgreich entpackt nach:\n{target_dir}"
        )

    def _view_archive(self, zip_path: str):
        """Öffnet den Archiv-Inspektor für die gewählte ZIP-Datei."""
        if not os.path.isfile(zip_path):
            return
        from gui.archive_dialog import ArchiveViewerDialog
        dlg = ArchiveViewerDialog(zip_path, parent=self.window())
        dlg.exec()

    def _test_archive_integrity(self, zip_path: str):
        """Prüft die CRC-Integrität der gewählten ZIP-Datei."""
        if not os.path.isfile(zip_path):
            return
        from core.archive_service import check_zip_integrity
        is_valid, msg = check_zip_integrity(zip_path)
        if is_valid:
            QMessageBox.information(
                self,
                "Integritätsprüfung",
                f"✅ Die Archiv-Integrität ist intakt:\n{os.path.basename(zip_path)}"
            )
        else:
            QMessageBox.warning(
                self,
                "Integritätsprüfung",
                f"❌ Archiv-Integritätsfehler:\n{msg}"
            )

    def _extract_zip_dialog(self):
        """Öffnet einen Dateidialog zur Auswahl eines zu entpackenden Archivs."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            "ZIP-Archiv zum Entpacken wählen",
            self._current_path,
            "ZIP-Archive (*.zip);;Alle Dateien (*.*)"
        )
        if path:
            self._extract_archive(path)
