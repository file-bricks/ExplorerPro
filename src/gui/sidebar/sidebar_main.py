#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sidebar - Seitenleiste mit Ordnerbaum, Favoriten, Suche, Apps, Prompts, Sync
Phase 5: Vollständige Integration
"""

import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QToolButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, Slot, QDir, QStandardPaths, QSize, QTimer
import os

# Module importieren - absolute Imports
from core.cloud_locations import find_cloud_locations
from core.async_fs import AsyncFs, list_subfolders
from core.file_icon_helper import generic_icon
from gui.sidebar.search_panel import SearchPanel as AdvancedSearchPanel
from modules.launcher import AppsPanel
from modules.prompts import PromptsPanel
from modules.sync import SyncPanel
from core.drive_usage import (
    read_drive_usage_bounded as read_drive_usage, load_usage_cache, save_usage_cache,
)
from gui.sidebar.drive_capacity import DriveCapacityWidget, capacity_executor
from translator import t


class TreePanel(QWidget):
    """Ordnerbaum-Panel

    Nothing that can block on a slow drive runs in the GUI thread: folder
    listings, cloud discovery and capacity reads run in workers and come back
    as signals. The last known state is shown at once and replaced only when
    the fresh one is complete.
    """

    folder_selected = Signal(str)
    _usage_ready = Signal(str, object)

    LIST_TIMEOUT_MS = 15000        # give up on one folder listing
    USAGE_MIN_INTERVAL_S = 60      # automatic capacity refresh per drive
    _dir_cache = {}                # path -> [(name, path)], shared, last known listing

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drive_rows = {}
        self._usage_requests = {}
        self._usage_cache = load_usage_cache()
        self._usage_checked = {}   # path -> monotonic time of last finished read
        self._usage_ready.connect(self._on_drive_usage)
        self._fs = AsyncFs(self)
        self._fs.finished.connect(self._on_fs_result)
        self._pending = {}         # token -> (kind, item)
        self._inflight = {}        # token -> path, until the worker really returned
        self._token = 0
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._resize_drive_rows)
        self._setup_ui()
        self._populate()
        self.refresh_drive_usage()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setAnimated(True)
        self.tree.setAccessibleName("Ordnerbaum")
        self.tree.setAccessibleDescription(
            "Hierarchische Struktur aller lokalen Laufwerke und Schnellzugriff-Verzeichnisse."
        )
        self.tree.setToolTip("Ordnerbaum zur Dateinavigation")
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)

        layout.addWidget(self.tree)
        self.refresh_drives_button = QPushButton(t("Laufwerksbelegung aktualisieren"))
        self.refresh_drives_button.clicked.connect(lambda: self.refresh_drive_usage(force=True))
        layout.addWidget(self.refresh_drives_button)

    def _populate(self):
        """Füllt den Baum mit Schnellzugriff, Cloud-Speichern und Laufwerken"""
        # Schnellzugriff
        quick_access = QTreeWidgetItem(["⭐ " + t("Schnellzugriff")])
        quick_access.setFlags(quick_access.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        locations = [
            (t("Persönlicher Ordner"), QStandardPaths.StandardLocation.HomeLocation),
            (t("Desktop"), QStandardPaths.StandardLocation.DesktopLocation),
            (t("Dokumente"), QStandardPaths.StandardLocation.DocumentsLocation),
            (t("Downloads"), QStandardPaths.StandardLocation.DownloadLocation),
            (t("Bilder"), QStandardPaths.StandardLocation.PicturesLocation),
            (t("Musik"), QStandardPaths.StandardLocation.MusicLocation),
            (t("Videos"), QStandardPaths.StandardLocation.MoviesLocation),
        ]

        seen = set()
        for name, location in locations:
            path = QStandardPaths.writableLocation(location)
            if not path or not os.path.isdir(path):
                continue
            key = os.path.normcase(os.path.normpath(path))
            if key in seen:
                continue
            seen.add(key)
            quick_access.addChild(self._folder_item(name, path))

        self.tree.addTopLevelItem(quick_access)
        quick_access.setExpanded(True)

        # Cloud-Speicher (OneDrive, Dropbox, Google Drive, iCloud, ...): probing
        # these paths can hang on stream drives, so the node appears when ready.
        self.cloud_item = None
        self._submit("cloud", None, find_cloud_locations)

        # Laufwerke
        drives_item = QTreeWidgetItem(["💾 " + t("Laufwerke")])
        drives_item.setFlags(drives_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.tree.addTopLevelItem(drives_item)

        for drive in QDir.drives():
            path = drive.absolutePath()
            # The embedded widget paints the title; duplicate tree text would
            # otherwise show through between its labels and progress bar.
            item = QTreeWidgetItem([""])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setData(0, Qt.ItemDataRole.AccessibleTextRole, path)
            item.setIcon(0, generic_icon("drive"))
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            drives_item.addChild(item)
            capacity = DriveCapacityWidget(path)
            self.tree.setItemWidget(item, 0, capacity)
            item.setSizeHint(0, capacity.sizeHint())
            self._drive_rows[path] = (item, capacity)
            if path in self._usage_cache:
                capacity.set_usage(self._usage_cache[path])
                item.setToolTip(0, capacity.toolTip())
                item.setSizeHint(0, capacity.sizeHint())

        drives_item.setExpanded(True)

    def refresh_drive_usage(self, force=False):
        """One request per drive; automatic calls are throttled, the button forces."""
        now = time.monotonic()
        for path, (item, capacity) in self._drive_rows.items():
            if path in self._usage_requests:
                continue
            if not force and now - self._usage_checked.get(path, -1e9) < self.USAGE_MIN_INTERVAL_S:
                continue
            if not capacity.has_usage:  # nothing stale to show yet
                capacity.set_loading()
                item.setSizeHint(0, capacity.sizeHint())
            future = capacity_executor().submit(read_drive_usage, path)
            self._usage_requests[path] = future
            future.add_done_callback(lambda f, p=path: self._usage_done(p, f))

    def _usage_done(self, path, future):
        """Runs in the pool thread: only forward the data as a queued signal."""
        try:
            usage = future.result()
        except BaseException:  # cancelled, OSError, helper failure: all mean "unavailable"
            usage = None
        try:
            self._usage_ready.emit(path, usage)
        except RuntimeError:  # panel destroyed
            pass

    @Slot(str, object)
    def _on_drive_usage(self, path, usage):
        self._usage_requests.pop(path, None)  # always released, also after errors
        self._usage_checked[path] = time.monotonic()
        if usage is not None:
            self._usage_cache[path] = usage
            save_usage_cache(self._usage_cache)
        row = self._drive_rows.get(path)
        if row is not None:
            item, capacity = row
            capacity.set_usage(usage)
            item.setToolTip(0, capacity.toolTip())
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, capacity.accessibleDescription())
            item.setSizeHint(0, capacity.sizeHint())
            self._resize_drive_rows()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_drive_usage()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(0)

    @Slot()
    def _resize_drive_rows(self):
        """Wrapped labels need taller rows when the sidebar becomes narrow."""
        for item, capacity in self._drive_rows.values():
            height = capacity.layout().totalHeightForWidth(capacity.width())
            item.setSizeHint(0, QSize(0, max(height, capacity.sizeHint().height())))
        self.tree.doItemsLayout()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.folder_selected.emit(path)

    @staticmethod
    def _folder_item(name: str, path: str) -> QTreeWidgetItem:
        """Erzeugt einen aufklappbaren Ordner-Eintrag (Unterordner werden lazy geladen)."""
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setIcon(0, generic_icon("folder"))
        item.setToolTip(0, path)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return item

    def _submit(self, kind, target, fn, *args):
        self._token += 1
        token = self._token
        self._pending[token] = (kind, target)
        if kind == "list":
            self._inflight[token] = args[0]
        self._fs.submit(token, fn, *args)
        if kind == "list":
            QTimer.singleShot(self.LIST_TIMEOUT_MS, lambda: self._on_list_timeout(token))

    @staticmethod
    def _alive(item):
        try:
            return item.treeWidget() is not None
        except RuntimeError:
            return False

    @staticmethod
    def _is_real(child):
        return bool(child.data(0, Qt.ItemDataRole.UserRole))

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Lazy loading: the listing runs in a worker; the last known one shows at once."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        if item.childCount() > 0 and self._is_real(item.child(0)):
            return
        if any(kind == "list" and target is item for kind, target in self._pending.values()):
            return

        item.takeChildren()  # drops any earlier placeholder, so there is never a second one
        cached = self._dir_cache.get(path)
        if cached is not None:
            self._fill(item, cached)
        else:
            placeholder = QTreeWidgetItem([t("wird geladen …")])
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            item.addChild(placeholder)
        if path in self._inflight.values():
            # An earlier request for this path still hangs: no further thread, just the hint.
            if cached is None:
                placeholder.setText(0, t("Keine Antwort – später erneut aufklappen"))
            return
        self._submit("list", item, list_subfolders, path)

    def _fill(self, item, entries):
        """Swap the children in one go, so the user never sees a half-built list."""
        children = [self._folder_item(name, full) for name, full in entries]
        item.takeChildren()
        item.addChildren(children)
        item.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator if children
            else QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless
        )

    @Slot(object, object, object)
    def _on_fs_result(self, token, result, error):
        self._inflight.pop(token, None)  # the worker is done, whatever we do with the answer
        entry = self._pending.pop(token, None)
        if entry is None:  # timed out: stale answer
            return
        kind, item = entry
        if kind == "cloud":
            self._show_cloud([] if error else result)
            return
        if not self._alive(item) or not item.isExpanded():
            return  # node vanished or was closed meanwhile; re-expanding asks again
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if error is not None:
            if path not in self._dir_cache:  # nothing stale worth keeping
                self._fill(item, [])
            return
        previous = self._dir_cache.get(path)
        self._dir_cache[path] = result
        showing = item.childCount() > 0 and self._is_real(item.child(0))
        if previous != result or not showing:
            self._fill(item, result)

    def _on_list_timeout(self, token):
        entry = self._pending.pop(token, None)  # a late answer is dropped
        if entry is None:
            return
        item = entry[1]
        if self._alive(item) and item.childCount() == 1 and not self._is_real(item.child(0)):
            item.child(0).setText(0, t("Keine Antwort – später erneut aufklappen"))

    def _show_cloud(self, cloud_locations):
        if not cloud_locations:
            return
        self.cloud_item = QTreeWidgetItem(["☁️ " + t("Cloud-Speicher")])
        self.cloud_item.setFlags(self.cloud_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        for location in cloud_locations:
            child = self._folder_item(location.label, location.path)
            child.setToolTip(0, location.path)
            self.cloud_item.addChild(child)
        self.tree.insertTopLevelItem(1, self.cloud_item)  # between quick access and drives
        self.cloud_item.setExpanded(True)


class FavoritesPanel(QWidget):
    """Favoriten-Panel"""

    favorite_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        header.addWidget(QLabel("Favoriten"))

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(24, 24)
        self.add_btn.setToolTip("Aktuellen Ordner zu Favoriten hinzufügen")
        self.add_btn.setAccessibleName("Zu Favoriten hinzufügen")
        self.add_btn.setAccessibleDescription("Fügt den aktuellen Ordnerpfad zur Favoritenliste hinzu.")
        header.addWidget(self.add_btn)

        layout.addLayout(header)

        self.list = QListWidget()
        self.list.setAccessibleName("Favoritenliste")
        self.list.setAccessibleDescription("Liste der gespeicherten Schnellzugriff-Favoriten.")
        self.list.setToolTip("Favoritenliste")
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list)

    def add_favorite(self, path: str, name: str = None):
        if name is None:
            name = os.path.basename(path) or path

        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.favorite_selected.emit(path)


class Sidebar(QWidget):
    """
    Haupt-Sidebar mit Tab-Navigation:
    - 📁 Ordnerbaum
    - ⭐ Favoriten
    - 🔍 Suche
    - 🚀 Apps
    - 📋 Prompts
    - 🔄 Sync
    """

    folder_selected = Signal(str)
    favorite_selected = Signal(str)
    app_launched = Signal(str)
    prompt_copied = Signal(str)
    sync_finished = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab-Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 4, 4, 4)
        btn_layout.setSpacing(2)

        self.btn_group = QButtonGroup(self)
        self.btn_group.buttonClicked.connect(self._on_tab_clicked)

        tabs = [
            ("📁", "Ordner", "Ordner", "Wechselt zur Seitenleiste mit Laufwerken und Schnellzugriff.", 0),
            ("⭐", "Favoriten", "Favoriten", "Wechselt zur Seitenleiste mit gespeicherten Favoritenordnern.", 1),
            ("🔍", "Suche", "Suche", "Wechselt zur Seitenleiste für die Volltext- und Dateisuche.", 2),
            ("🚀", "Apps", "Apps", "Wechselt zur Seitenleiste mit häufig genutzten Programmen.", 3),
            ("📋", "Prompts", "Prompts", "Wechselt zur Seitenleiste mit lokalen Prompt-Vorlagen.", 4),
            ("🔄", "Sync", "Sync", "Wechselt zur Seitenleiste für den Ordnerabgleich.", 5),
        ]

        for icon, tooltip, accessible_name, accessible_description, idx in tabs:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.setStatusTip(accessible_description)
            btn.setAccessibleName(accessible_name)
            btn.setAccessibleDescription(accessible_description)
            btn.setObjectName(f"sidebar_tab_{idx}")
            btn.setCheckable(True)
            btn.setFixedSize(36, 36)
            self.btn_group.addButton(btn, idx)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Stacked Widget für Panels
        self.stack = QStackedWidget()

        # 0: Ordner-Panel
        self.tree_panel = TreePanel()
        self.tree_panel.folder_selected.connect(self.folder_selected)
        self.stack.addWidget(self.tree_panel)

        # 1: Favoriten-Panel
        self.favorites_panel = FavoritesPanel()
        self.favorites_panel.favorite_selected.connect(self.favorite_selected)
        self.stack.addWidget(self.favorites_panel)

        # 2: Such-Panel
        self.search_panel = AdvancedSearchPanel()
        self.search_panel.result_selected.connect(self.folder_selected)
        self.search_panel.result_activated.connect(self._on_search_result_activated)
        self.stack.addWidget(self.search_panel)

        # 3: Apps-Panel (SoftwareCenter-Integration)
        self.apps_panel = AppsPanel()
        self.apps_panel.app_launched.connect(self.app_launched)
        self.stack.addWidget(self.apps_panel)

        # 4: Prompts-Panel (ProfiPrompt-Integration)
        self.prompts_panel = PromptsPanel()
        self.prompts_panel.prompt_copied.connect(self.prompt_copied)
        self.stack.addWidget(self.prompts_panel)

        # 5: Sync-Panel (ProSync-Integration)
        self.sync_panel = SyncPanel()
        self.sync_panel.sync_finished.connect(self.sync_finished)
        self.stack.addWidget(self.sync_panel)

        layout.addWidget(self.stack)

        # Ersten Tab aktivieren
        self.btn_group.button(0).setChecked(True)

    def _on_tab_clicked(self, button):
        idx = self.btn_group.id(button)
        self.stack.setCurrentIndex(idx)

    def _on_search_result_activated(self, path: str):
        """Öffnet Suchergebnis"""
        if os.path.isfile(path):
            folder = os.path.dirname(path)
            self.folder_selected.emit(folder)
        else:
            self.folder_selected.emit(path)

    def set_file_index(self, file_index):
        """Setzt den Datei-Index für die Suche"""
        self.search_panel.set_index(file_index)

    def switch_to_tab(self, index: int):
        """Wechselt zum angegebenen Tab"""
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            btn = self.btn_group.button(index)
            if btn:
                btn.setChecked(True)

    def switch_to_search(self):
        """Wechselt zum Such-Tab"""
        self.switch_to_tab(2)

    def switch_to_apps(self):
        """Wechselt zum Apps-Tab"""
        self.switch_to_tab(3)

    def switch_to_prompts(self):
        """Wechselt zum Prompts-Tab"""
        self.switch_to_tab(4)

    def switch_to_sync(self):
        """Wechselt zum Sync-Tab"""
        self.switch_to_tab(5)
