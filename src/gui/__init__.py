#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro GUI Module

HINWEIS: Lazy Imports verwendet um Access Violation beim Start zu vermeiden.
Module werden bei Bedarf importiert, nicht beim Package-Load.
"""

__all__ = [
    'MainWindow',
    'SearchToolBar',
    'PrivacySettingsDialog',
    'Sidebar',
    'StatusBarWidget',
    'PrivacyIndicator',
    'FileBrowser',
    'PreviewPanel'
]

def __getattr__(name):
    """Lazy loading für GUI-Komponenten"""
    if name == 'MainWindow':
        from .main_window import MainWindow
        return MainWindow
    elif name == 'SearchToolBar':
        from .main_window import SearchToolBar
        return SearchToolBar
    elif name == 'PrivacySettingsDialog':
        from .main_window import PrivacySettingsDialog
        return PrivacySettingsDialog
    elif name == 'Sidebar':
        from .sidebar import Sidebar
        return Sidebar
    elif name == 'StatusBarWidget':
        from .status_bar import StatusBarWidget
        return StatusBarWidget
    elif name == 'PrivacyIndicator':
        from .status_bar import PrivacyIndicator
        return PrivacyIndicator
    elif name == 'FileBrowser':
        from .browser.file_browser import FileBrowser
        return FileBrowser
    elif name == 'PreviewPanel':
        from .preview.preview_panel import PreviewPanel
        return PreviewPanel
    raise AttributeError(f"module 'gui' has no attribute '{name}'")
