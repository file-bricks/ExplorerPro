#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sidebar Module

HINWEIS: Lazy Imports verwendet um Access Violation beim Start zu vermeiden.
"""

__all__ = [
    'Sidebar',
    'TreePanel',
    'FavoritesPanel',
    'SearchPanel',
    'SearchResult',
    'SearchResultItem',
    'AdvancedSearchDialog'
]

def __getattr__(name):
    """Lazy loading für Sidebar-Komponenten"""
    if name == 'Sidebar':
        from .sidebar_main import Sidebar
        return Sidebar
    elif name == 'TreePanel':
        from .sidebar_main import TreePanel
        return TreePanel
    elif name == 'FavoritesPanel':
        from .sidebar_main import FavoritesPanel
        return FavoritesPanel
    elif name == 'SearchPanel':
        from .search_panel import SearchPanel
        return SearchPanel
    elif name == 'SearchResult':
        from .search_panel import SearchResult
        return SearchResult
    elif name == 'SearchResultItem':
        from .search_panel import SearchResultItem
        return SearchResultItem
    elif name == 'AdvancedSearchDialog':
        from .advanced_search_dialog import AdvancedSearchDialog
        return AdvancedSearchDialog
    raise AttributeError(f"module 'gui.sidebar' has no attribute '{name}'")
