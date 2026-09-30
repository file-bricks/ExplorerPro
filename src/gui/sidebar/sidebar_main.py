#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sidebar - Seitenleiste mit Ordnerbaum, Favoriten, Suche, Apps, Prompts, Sync
Phase 5: Vollständige Integration
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFrame, QToolButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, Slot, QDir, QStandardPaths, QSize, QTimer
import os

# Module importieren - absolute Imports
from core.file_icon_helper import get_file_icon
from gui.sidebar.search_panel import SearchPanel as AdvancedSearchPanel
from modules.launcher import AppsPanel
from modules.prompts import PromptsPanel
from modules.sync import SyncPanel
from gui.sidebar.drive_capacity import DriveCapacityWidget, UsageRequest, capacity_pool
from translator import t


class TreePanel(QWidget):
    """Ordnerbaum-Panel"""

    folder_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drive_rows = {}
        self._usage_requests = {}
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
        self.refresh_drives_button.clicked.connect(self.refresh_drive_usage)
        layout.addWidget(self.refresh_drives_button)

    def _populate(self):
        """Füllt den Baum mit Laufwerken und Schnellzugriff"""
        # Schnellzugriff
        quick_access = QTreeWidgetItem(["⭐ Schnellzugriff"])
        quick_access.setFlags(quick_access.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        locations = [
            ("Desktop", QStandardPaths.StandardLocation.DesktopLocation),
            ("Dokumente", QStandardPaths.StandardLocation.DocumentsLocation),
            ("Downloads", QStandardPaths.StandardLocation.DownloadLocation),
            ("Bilder", QStandardPaths.StandardLocation.PicturesLocation),
            ("Musik", QStandardPaths.StandardLocation.MusicLocation),
        ]

        for name, location in locations:
            path = QStandardPaths.writableLocation(location)
            if path and os.path.exists(path):
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                child.setIcon(0, get_file_icon(path))
                quick_access.addChild(child)

        self.tree.addTopLevelItem(quick_access)
        quick_access.setExpanded(True)

        # Laufwerke
        drives_item = QTreeWidgetItem(["💾 Laufwerke"])
        drives_item.setFlags(drives_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.tree.addTopLevelItem(drives_item)

        for drive in QDir.drives():
            path = drive.absolutePath()
            # The embedded widget paints the title; duplicate tree text would
            # otherwise show through between its labels and progress bar.
            item = QTreeWidgetItem([""])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setData(0, Qt.ItemDataRole.AccessibleTextRole, path)
            item.setIcon(0, get_file_icon(path))
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            drives_item.addChild(item)
            capacity = DriveCapacityWidget(path)
            self.tree.setItemWidget(item, 0, capacity)
            item.setSizeHint(0, capacity.sizeHint())
            self._drive_rows[path] = (item, capacity)

        drives_item.setExpanded(True)

    def refresh_drive_usage(self):
        """One request per drive; repeat clicks cannot queue duplicate queries."""
        for path, (item, capacity) in self._drive_rows.items():
            if path in self._usage_requests:
                continue
            capacity.set_loading()
            item.setSizeHint(0, capacity.sizeHint())
            request = UsageRequest(path)
            request.signals.ready.connect(self._on_drive_usage, Qt.ConnectionType.QueuedConnection)
            self._usage_requests[path] = request
            capacity_pool().start(request)

    @Slot(str, object)
    def _on_drive_usage(self, path, usage):
        self._usage_requests.pop(path, None)
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

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Lazy Loading für Unterordner"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return

        if item.childCount() > 0 and item.child(0).data(0, Qt.ItemDataRole.UserRole):
            return

        item.takeChildren()

        try:
            for name in os.listdir(path):
                full_path = os.path.join(path, name)
                if os.path.isdir(full_path) and not name.startswith('.'):
                    child = QTreeWidgetItem([name])
                    child.setData(0, Qt.ItemDataRole.UserRole, full_path)
                    child.setIcon(0, get_file_icon(full_path))
                    child.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                    item.addChild(child)
        except OSError:
            pass


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
