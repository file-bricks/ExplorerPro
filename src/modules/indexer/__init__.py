#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indexer Module - Datei-Indizierung und Duplikate-Finder
"""

from .duplicate_finder import DuplicateFinderDialog, DuplicateScanWorker

__all__ = [
    'DuplicateFinderDialog',
    'DuplicateScanWorker'
]
