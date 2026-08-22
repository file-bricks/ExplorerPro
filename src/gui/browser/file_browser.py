#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileBrowser - Dateilisten-Ansicht mit QuickEditor-Integration
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView,
    QMenu, QAbstractItemView, QMessageBox, QFileSystemModel,
    QApplication, QInputDialog
)
from PySide6.QtCore import (
    Qt, Signal, QDir, QModelIndex, QSortFilterProxyModel,
    QStandardPaths, QUrl, QMimeData, QSize
)
from PySide6.QtGui import QAction, QCursor, QDrag, QKeySequence
import os
import subprocess
import shutil
from pathlib import Path

from core.platform_utils import open_path_with_system

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._fb.delete_selection()
            event.accept()
        elif event.key() == Qt.Key.Key_F2:
            self._fb.rename_selection()
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

    # Signale
    file_selected = Signal(str)
    folder_changed = Signal(str)
    path_changed = Signal(str)          # Für Toolbar & StatusBar
    selection_changed = Signal(int)     # Anzahl ausgewählter Dateien
    file_double_clicked = Signal(str)
    edit_requested = Signal(str)        # Datei im Editor öffnen

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""
        self._history = []
        self._history_index = -1
        self._file_count = 0
        self._setup_ui()

        # Startverzeichnis
        home = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.HomeLocation
        )
        self.navigate_to(home)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Datei-System-Model
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(
            QDir.Filter.AllEntries |
            QDir.Filter.NoDotAndDotDot
        )
        self.model.directoryLoaded.connect(self._on_directory_loaded)

        # Sortier-Proxy
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # Tabellen-View (DnD-fähige Unterklasse für startDrag-Override)
        self.table = _DnDTableView(self)
        self.table.setModel(self.proxy)
        self.table.setRootIndex(self.proxy.mapFromSource(
            self.model.index(QDir.rootPath())
        ))

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

        # Header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

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

    def _on_directory_loaded(self, path: str):
        """Handler wenn Verzeichnis geladen wurde"""
        if path == self._current_path:
            self._update_file_count()

    def _update_file_count(self):
        """Aktualisiert die Datei-Anzahl"""
        if self._current_path:
            try:
                entries = list(Path(self._current_path).iterdir())
                self._file_count = len(entries)
            except (OSError, PermissionError):
                self._file_count = 0

    def _on_selection_changed(self):
        """Handler für Auswahl-Änderungen"""
        selected = len(self.get_selected_files())
        self.selection_changed.emit(selected)

    def navigate_to(self, path: str):
        """Navigiert zu einem Pfad"""
        if not os.path.exists(path):
            return

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

        source_index = self.model.index(path)
        proxy_index = self.proxy.mapFromSource(source_index)
        self.table.setRootIndex(proxy_index)

        self._update_file_count()

        # Signale senden
        self.folder_changed.emit(path)
        self.path_changed.emit(path)

    def go_back(self):
        """Geht einen Schritt zurück"""
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._current_path = path
            source_index = self.model.index(path)
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
            source_index = self.model.index(path)
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
            self.model.setRootPath("")
            self.model.setRootPath(self._current_path)
            self._update_file_count()

    def set_show_hidden_files(self, show: bool):
        """Schaltet die Anzeige versteckter Dateien um."""
        filters = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
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
            source_index = self.proxy.mapToSource(index)
            file_path = self.model.filePath(source_index)
            is_file = os.path.isfile(file_path)
            ext = Path(file_path).suffix.lower() if is_file else ""

            # Öffnen
            open_action = QAction("📂 Öffnen", self)
            open_action.triggered.connect(lambda: self._open_file(file_path))
            menu.addAction(open_action)

            # In Editor öffnen (nur für Code-Dateien)
            if is_file and ext in EDITOR_EXTENSIONS:
                edit_action = QAction("✏️ In Editor öffnen", self)
                edit_action.setShortcut("F4")
                edit_action.triggered.connect(lambda: self._edit_file(file_path))
                menu.addAction(edit_action)

            menu.addSeparator()

            # Index-Aktionen
            index_action = QAction("🔍 In Index suchen", self)
            index_action.triggered.connect(lambda: self._search_in_index(file_path))
            menu.addAction(index_action)

            meta_action = QAction("📊 Metadaten anzeigen", self)
            meta_action.triggered.connect(lambda: self.file_selected.emit(file_path))
            menu.addAction(meta_action)

            tags_action = QAction("🏷️ Tags bearbeiten", self)
            tags_action.triggered.connect(lambda: self.file_selected.emit(file_path))
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
            copy_action = QAction("Kopieren", self)
            copy_action.setShortcut("Ctrl+C")
            copy_action.triggered.connect(self.copy_selection)
            menu.addAction(copy_action)

            delete_action = QAction("Löschen", self)
            delete_action.setShortcut("Delete")
            delete_action.triggered.connect(lambda: self.delete_selection([file_path]))
            menu.addAction(delete_action)

            rename_action = QAction("Umbenennen", self)
            rename_action.setShortcut("F2")
            rename_action.triggered.connect(lambda: self.rename_selection(file_path))
            menu.addAction(rename_action)

        else:
            # Leer-Bereich-Menü
            new_folder = QAction("📁 Neuer Ordner", self)
            new_folder.triggered.connect(self.create_new_folder)
            menu.addAction(new_folder)

            paste_action = QAction("Einfügen", self)
            paste_action.setShortcut("Ctrl+V")
            paste_action.triggered.connect(self.paste_from_clipboard)
            menu.addAction(paste_action)

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
                "Datei öffnen",
                f"Die Datei konnte nicht geöffnet werden:\n{path}\n\n{exc}"
            )

    def _edit_file(self, path: str):
        """Öffnet Datei im QuickEditor"""
        from modules.editor.quick_editor import QuickEditorDialog

        editor = QuickEditorDialog(path, self.window())
        editor.exec()

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
                        self, "Datenschutz-Prüfung",
                        f"Status: {alert.status.value.upper()}\n\n"
                        f"Erkannte Muster:\n• " +
                        "\n• ".join(alert.detected_patterns)
                    )
                else:
                    QMessageBox.information(
                        self, "Datenschutz-Prüfung",
                        "✅ Keine sensiblen Daten erkannt."
                    )
        except Exception as e:
            QMessageBox.warning(
                self, "Fehler",
                f"Konnte Datei nicht prüfen: {e}"
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
                self, "Neuer Ordner",
                f"Ein Ordner oder eine Datei mit dem Namen '{name}' existiert bereits."
            )
            return False
        except OSError as exc:
            QMessageBox.warning(
                self, "Neuer Ordner",
                f"Konnte Ordner nicht erstellen:\n{exc}"
            )
            return False

    def rename_selection(self, target_path: str = None) -> bool:
        """Benennt die ausgewählte Datei oder den ausgewählten Ordner um."""
        if not target_path:
            selected = self.get_selected_files()
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
                self, "Umbenennen",
                f"Ein Element namens '{new_name}' existiert bereits in diesem Verzeichnis."
            )
            return False

        try:
            os.rename(target_path, new_path)
            self.refresh()
            return True
        except OSError as exc:
            QMessageBox.warning(
                self, "Umbenennen",
                f"Konnte Element nicht umbenennen:\n{exc}"
            )
            return False

    def delete_selection(self, target_paths: list = None) -> bool:
        """Löscht ausgewählte Dateien oder Ordner nach Bestätigung."""
        if not target_paths:
            target_paths = self.get_selected_files()
        if not target_paths:
            return False

        count = len(target_paths)
        if count == 1:
            msg = f"Möchten Sie '{os.path.basename(target_paths[0])}' wirklich unwiderruflich löschen?"
        else:
            preview = "\n".join(f"• {os.path.basename(p)}" for p in target_paths[:5])
            if count > 5:
                preview += f"\n... und {count - 5} weitere"
            msg = f"Möchten Sie diese {count} Elemente wirklich unwiderruflich löschen?\n\n{preview}"

        reply = QMessageBox.question(
            self,
            "Löschen bestätigen",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return False

        errors = []
        for path in target_paths:
            if not os.path.exists(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

        self.refresh()
        if errors:
            QMessageBox.warning(
                self, "Fehler beim Löschen",
                "Folgende Elemente konnten nicht gelöscht werden:\n\n" + "\n".join(errors)
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
        content = f"Analysiere bitte folgende Datei:\n{path}" if is_file else f"Analysiere bitte folgenden Ordner:\n{path}"
        title = f"Pfad: {filename}"

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
                self, "Prompt gespeichert",
                f"Prompt für '{filename}' wurde in der Bibliothek gespeichert."
            )
        else:
            QApplication.clipboard().setText(content)
            QMessageBox.information(
                self, "Prompt in Zwischenablage",
                f"Prompt-Vorlage für '{filename}' in die Zwischenablage kopiert."
            )

    def _add_to_blacklist(self, path: str):
        """Fügt den Dateinamen zur Datenschutz-Blacklist hinzu."""
        filename = os.path.basename(path)
        main_win = self.window()
        if hasattr(main_win, 'privacy_monitor') and main_win.privacy_monitor:
            main_win.privacy_monitor.add_to_blacklist(filename)
            QMessageBox.information(
                self, "Datenschutz",
                f"'{filename}' wurde zur Datenschutz-Blacklist hinzugefügt."
            )
        else:
            QMessageBox.information(
                self, "Datenschutz",
                f"'{filename}' konnte nicht hinzugefügt werden: Datenschutz-Monitor nicht initialisiert."
            )

    def _sync_path(self, path: str):
        """Öffnet das Sync-Panel für den Pfad."""
        main_win = self.window()
        if hasattr(main_win, 'show_sync_panel'):
            main_win.show_sync_panel()

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
                errors.append(f"Quelle nicht gefunden: {src}")
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
                        f"{os.path.basename(src)}: Ordner kann nicht in seinen "
                        "eigenen Unterordner kopiert oder verschoben werden."
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
                "Drag & Drop",
                "Einige Dateien konnten nicht übertragen werden:\n\n"
                + "\n".join(errors),
            )
