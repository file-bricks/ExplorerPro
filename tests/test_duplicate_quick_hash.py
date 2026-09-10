#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_duplicate_quick_hash.py - Prüft die zweistufige Chunk-Hash-Optimierung im DuplicateScanWorker
"""

import hashlib
from pathlib import Path
from PySide6.QtWidgets import QApplication

from modules.indexer.duplicate_finder import DuplicateScanWorker


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_duplicate_quick_hash_calculation(tmp_path: Path):
    """Prüft, dass _compute_quick_hash den SHA-256 der ersten 64 KB liefert."""
    _ensure_app()
    worker = DuplicateScanWorker(scan_path=str(tmp_path), min_size=1)

    file_a = tmp_path / "file_a.bin"
    content = b"H" * (128 * 1024)
    file_a.write_bytes(content)

    expected_quick = hashlib.sha256(content[:65536]).hexdigest()
    assert worker._compute_quick_hash(str(file_a)) == expected_quick


def test_duplicate_scan_filters_different_prefixes(tmp_path: Path):
    """Dateien mit gleicher Größe, aber unterschiedlichen Headern werden schnell aussortiert."""
    _ensure_app()
    folder = tmp_path / "scan_folder"
    folder.mkdir()

    # Zwei 100 KB Dateien mit unterschiedlichem Anfang
    f1 = folder / "f1.bin"
    f2 = folder / "f2.bin"

    f1.write_bytes(b"PREFIX_1" + (b"X" * (100 * 1024 - 8)))
    f2.write_bytes(b"PREFIX_2" + (b"X" * (100 * 1024 - 8)))

    worker = DuplicateScanWorker(scan_path=str(folder), min_size=1)
    results = worker._scan_directory()

    # Keine Duplikate gefunden
    assert len(results) == 0


def test_duplicate_scan_detects_identical_files(tmp_path: Path):
    """Identische Dateien über 64 KB werden zuverlässig gefunden."""
    _ensure_app()
    folder = tmp_path / "scan_folder_identical"
    folder.mkdir()

    payload = b"SAME_PREFIX_" + (b"Y" * (120 * 1024))
    f1 = folder / "f1.bin"
    f2 = folder / "f2.bin"
    f1.write_bytes(payload)
    f2.write_bytes(payload)

    worker = DuplicateScanWorker(scan_path=str(folder), min_size=1)
    results = worker._scan_directory()

    assert len(results) == 1
    expected_hash = hashlib.sha256(payload).hexdigest()
    assert expected_hash in results
    assert len(results[expected_hash]) == 2
