"""
Contract and performance-hardening tests for DuplicateScanWorker and FileIndex duplicate detection.
Verifies:
1. Two-phase hashing: Correctly detects duplicates for small (<= 32 KB) and large (> 32 KB) files.
2. Optimization: Files with same size but differing headers/samples are filtered early without unnecessary full hashing.
3. Cancellation safety: Worker stops cooperatively when cancelled.
4. Index-based duplicate scan: Filters by size, handles multiple duplicates, and counts total files accurately.
5. FileIndex.find_duplicates: min_size parameter filtering.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])

from core.file_index import FileIndex
from modules.indexer.duplicate_finder import DuplicateScanWorker


def test_duplicate_scan_directory_small_and_large_files(tmp_path):
    """Prüft, dass Zwei-Phasen-Hashing sowohl kleine als auch große Dateien korrekt als Duplikate erkennt."""
    scan_dir = tmp_path / "scan_area"
    scan_dir.mkdir()

    # Kleine Dateien (<= 32 KB)
    small_orig = scan_dir / "small_orig.txt"
    small_dup = scan_dir / "small_dup.txt"
    small_orig.write_bytes(b"Small content data " * 100)
    small_dup.write_bytes(b"Small content data " * 100)

    # Große Dateien (> 32 KB, z.B. 64 KB)
    large_payload = b"Large unique payload " * 3200
    large_orig = scan_dir / "large_orig.bin"
    large_dup = scan_dir / "large_dup.bin"
    large_orig.write_bytes(large_payload)
    large_dup.write_bytes(large_payload)

    # Datei mit gleicher Größe wie large_orig, aber anderem Inhalt
    diff_payload = b"Different content!!! " * 3200
    assert len(diff_payload) == len(large_payload)
    large_different = scan_dir / "large_diff.bin"
    large_different.write_bytes(diff_payload)

    worker = DuplicateScanWorker(scan_path=str(scan_dir), min_size=10, use_index=False)
    results = []
    finished_args = []
    worker.duplicates_found.connect(lambda d: results.append(d))
    worker.finished_scan.connect(lambda total, groups: finished_args.append((total, groups)))

    worker.run()

    assert len(results) == 1
    found = results[0]
    # Es müssen genau 2 Duplikat-Gruppen gefunden werden (small + large)
    assert len(found) == 2

    # Große unterschiedliche Datei darf NICHT in einer Duplikat-Gruppe landen
    all_duplicate_files = [p for paths in found.values() for p in paths]
    assert str(large_different) not in all_duplicate_files
    assert str(large_orig) in all_duplicate_files
    assert str(large_dup) in all_duplicate_files
    assert str(small_orig) in all_duplicate_files
    assert str(small_dup) in all_duplicate_files

    # finished_scan sollte alle 5 gescannten Dateien melden
    assert len(finished_args) == 1
    total_scanned, dup_groups = finished_args[0]
    assert total_scanned == 5
    assert dup_groups == 2


def test_duplicate_scan_skips_full_hash_when_sample_differs(tmp_path):
    """Prüft, dass Dateien mit gleicher Größe aber unterschiedlichem Sample-Hash nicht voll gehasht werden."""
    scan_dir = tmp_path / "sample_test"
    scan_dir.mkdir()

    # Zwei 64 KB Dateien mit unterschiedlichem Anfang
    f1 = scan_dir / "file1.bin"
    f2 = scan_dir / "file2.bin"
    f1.write_bytes(b"A" * 65536)
    f2.write_bytes(b"B" * 65536)

    worker = DuplicateScanWorker(scan_path=str(scan_dir), min_size=10, use_index=False)

    full_hash_calls = []
    orig_compute_hash = worker._compute_hash

    def spy_compute_hash(path, block_size=65536):
        full_hash_calls.append(path)
        return orig_compute_hash(path, block_size)

    worker._compute_hash = spy_compute_hash

    results = []
    worker.duplicates_found.connect(lambda d: results.append(d))
    worker.run()

    assert len(results) == 1
    assert len(results[0]) == 0  # Keine Duplikate
    # _compute_hash darf für f1 und f2 nicht aufgerufen worden sein,
    # weil der Sample-Hash die beiden bereits in Phase 2 getrennt hat!
    assert len(full_hash_calls) == 0


def test_duplicate_scan_cooperative_cancellation(tmp_path):
    """Prüft, dass DuplicateScanWorker bei cancel() vorzeitig und sauber abbricht."""
    scan_dir = tmp_path / "cancel_test"
    scan_dir.mkdir()

    for i in range(10):
        f = scan_dir / f"file_{i}.bin"
        f.write_bytes(b"Same content for test" * 100)

    worker = DuplicateScanWorker(scan_path=str(scan_dir), min_size=10, use_index=False)

    # Beim ersten Progress direkt abbrechen
    def on_progress(curr, total, name):
        worker.cancel()

    worker.progress.connect(on_progress)
    results = []
    worker.duplicates_found.connect(lambda d: results.append(d))
    worker.run()

    # Nach Abbruch darf keine Duplikat-Gruppe emittiert werden
    assert len(results) == 0


def test_duplicate_scan_index_with_size_filtering(tmp_path):
    """Prüft, dass die Index-basierte Duplikat-Suche min_size filtert und die Gesamtanzahl meldet."""
    db_file = tmp_path / "indexed_duplicates.db"
    idx = FileIndex(str(db_file))

    # Datei 1 und 2: identisch, Größe 500 Bytes
    f1 = tmp_path / "doc1.txt"
    f2 = tmp_path / "doc2.txt"
    f1.write_text("A" * 500, encoding="utf-8")
    f2.write_text("A" * 500, encoding="utf-8")

    # Datei 3 und 4: identisch, Größe 50 Bytes
    f3 = tmp_path / "tiny1.txt"
    f4 = tmp_path / "tiny2.txt"
    f3.write_text("B" * 50, encoding="utf-8")
    f4.write_text("B" * 50, encoding="utf-8")

    # Datei 5: einzigartig
    f5 = tmp_path / "unique.txt"
    f5.write_text("Unique content 123", encoding="utf-8")

    for f in (f1, f2, f3, f4, f5):
        idx.index_file(str(f), calculate_hash=True)

    # Scan mit min_size=200 Bytes: nur doc1 und doc2 sollen gefunden werden
    worker = DuplicateScanWorker(file_index=idx, min_size=200, use_index=True)
    results = []
    finished_info = []
    worker.duplicates_found.connect(lambda d: results.append(d))
    worker.finished_scan.connect(lambda total, groups: finished_info.append((total, groups)))

    worker.run()

    assert len(results) == 1
    found = results[0]
    assert len(found) == 1
    hash_val = list(found.keys())[0]
    assert sorted(found[hash_val]) == sorted([str(f1), str(f2)])

    # finished_scan meldet Gesamtdateien >= 200 Bytes (doc1, doc2) und 1 Duplikat-Gruppe
    assert len(finished_info) == 1
    assert finished_info[0] == (2, 1)


def test_file_index_find_duplicates_min_size(tmp_path):
    """Prüft FileIndex.find_duplicates mit min_size Parameter."""
    db_file = tmp_path / "find_dup_test.db"
    idx = FileIndex(str(db_file))

    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"X" * 1000)
    f2.write_bytes(b"X" * 1000)

    idx.index_file(str(f1), calculate_hash=True)
    idx.index_file(str(f2), calculate_hash=True)

    # Mit min_size=500 gefunden
    dups = idx.find_duplicates(min_size=500)
    assert len(dups) == 1
    assert len(dups[0][1]) == 2

    # Mit min_size=2000 nicht gefunden
    dups_large = idx.find_duplicates(min_size=2000)
    assert len(dups_large) == 0
