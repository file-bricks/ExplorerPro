#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExplorerPro Modules

HINWEIS: Lazy Imports verwendet um Access Violation beim Start zu vermeiden.
"""

__all__ = [
    'AppsPanel',
    'PromptsPanel', 
    'SyncPanel',
    'PrivacyMonitor',
    'QuickEditor'
]

def __getattr__(name):
    """Lazy loading für Module"""
    if name == 'AppsPanel':
        from .launcher import AppsPanel
        return AppsPanel
    elif name == 'PromptsPanel':
        from .prompts import PromptsPanel
        return PromptsPanel
    elif name == 'SyncPanel':
        from .sync import SyncPanel
        return SyncPanel
    elif name == 'PrivacyMonitor':
        from .privacy.privacy_monitor import PrivacyMonitor
        return PrivacyMonitor
    elif name == 'QuickEditor':
        from .editor import QuickEditor
        return QuickEditor
    raise AttributeError(f"module 'modules' has no attribute '{name}'")
