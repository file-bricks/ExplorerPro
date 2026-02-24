#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro Core Module

HINWEIS: Lazy Imports verwendet um Access Violation beim Start zu vermeiden.
Module werden bei Bedarf importiert, nicht beim Package-Load.
"""

# Keine automatischen Imports hier - Module werden direkt importiert wo sie gebraucht werden
# Beispiel: from core.file_index import FileIndex

__all__ = [
    'FileIndex',
    'IndexWorker', 
    'SettingsManager',
    'EventBus'
]

def __getattr__(name):
    """Lazy loading für Module"""
    if name == 'FileIndex':
        from .file_index import FileIndex
        return FileIndex
    elif name == 'IndexWorker':
        from .file_index import IndexWorker
        return IndexWorker
    elif name == 'SettingsManager':
        from .settings_manager import SettingsManager
        return SettingsManager
    elif name == 'EventBus':
        from .event_bus import EventBus
        return EventBus
    raise AttributeError(f"module 'core' has no attribute '{name}'")
