#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_checksum_service.py - Unit- und Integrationstests für den ChecksumService
"""

import hashlib
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from core.checksum_service import (
    compute_file_hashes,
    verify_hash,
    ChecksumWorker,
    SUPPORTED_ALGORITHMS,
)


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_compute_file_hashes_all_algorithms(tmp_path: Path):
    """Prüft, dass alle unterstützten Algorithmen korrekte Hashes liefern."""
    assert "sha256" in SUPPORTED_ALGORITHMS
    test_file = tmp_path / "sample.txt"
    data = "ExplorerPro Prüfsummen-Testinhalt mit Umlauten: äöüß 1234567890".encode("utf-8")
    test_file.write_bytes(data)

    results = compute_file_hashes(
        str(test_file),
        algorithms=("md5", "sha1", "sha256", "sha512")
    )

    assert results["md5"] == hashlib.md5(data).hexdigest()
    assert results["sha1"] == hashlib.sha1(data).hexdigest()
    assert results["sha256"] == hashlib.sha256(data).hexdigest()
    assert results["sha512"] == hashlib.sha512(data).hexdigest()


def test_compute_file_hashes_empty_file(tmp_path: Path):
    """Prüft Hash-Berechnung einer leeren Datei."""
    empty_file = tmp_path / "empty.bin"
    empty_file.write_bytes(b"")

    results = compute_file_hashes(str(empty_file))
    assert results["sha256"] == hashlib.sha256(b"").hexdigest()
    assert results["md5"] == hashlib.md5(b"").hexdigest()


def test_compute_file_hashes_multi_chunk(tmp_path: Path):
    """Prüft Hash-Berechnung mit mehreren Chunks."""
    large_file = tmp_path / "large.bin"
    # 200 KB Datei (Chunk-Größe 64 KB -> mindestens 4 Chunks)
    payload = b"A" * (200 * 1024)
    large_file.write_bytes(payload)

    progress_calls = []

    def on_progress(read_bytes, total_bytes):
        progress_calls.append((read_bytes, total_bytes))

    results = compute_file_hashes(
        str(large_file),
        algorithms=("sha256",),
        chunk_size=32 * 1024,
        progress_callback=on_progress,
    )

    assert results["sha256"] == hashlib.sha256(payload).hexdigest()
    assert len(progress_calls) > 1
    assert progress_calls[-1] == (len(payload), len(payload))


def test_compute_file_hashes_cancellation(tmp_path: Path):
    """Prüft vorzeitigen Abbruch der Hash-Berechnung."""
    large_file = tmp_path / "cancel.bin"
    large_file.write_bytes(b"B" * (256 * 1024))

    call_count = [0]

    def cancel_check():
        call_count[0] += 1
        return call_count[0] >= 2

    results = compute_file_hashes(
        str(large_file),
        chunk_size=16 * 1024,
        is_cancelled=cancel_check,
    )

    assert results == {}


def test_compute_file_hashes_non_existent_file():
    """Prüft FileNotFoundError bei ungültigem Pfad."""
    with pytest.raises(FileNotFoundError):
        compute_file_hashes("C:/ungueltiger/pfad/datei_gibts_nicht.xyz")


def test_verify_hash_matches():
    """Prüft Hash-Verifikation bei exakter, groß-/kleingeschriebener und präfixierter Eingabe."""
    hashes = {
        "md5": "098f6bcd4621d373cade4e832627b4f6",
        "sha1": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
        "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    }

    # Exakter Match
    assert verify_hash(hashes, "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08") == (
        "sha256",
        hashes["sha256"],
    )

    # Uppercase
    assert verify_hash(hashes, "9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08") == (
        "sha256",
        hashes["sha256"],
    )

    # Mit Whitespace
    assert verify_hash(hashes, "  098f6bcd4621d373cade4e832627b4f6  \n") == (
        "md5",
        hashes["md5"],
    )

    # Mit Präfix
    assert verify_hash(hashes, "sha1: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3") == (
        "sha1",
        hashes["sha1"],
    )

    # Keine Übereinstimmung
    assert verify_hash(hashes, "invalid_hash_value_12345") is None
    assert verify_hash(hashes, "") is None


def test_checksum_worker_run(tmp_path: Path):
    """Prüft Ausführung des ChecksumWorker im Thread."""
    _ensure_app()
    sample = tmp_path / "worker_test.txt"
    sample.write_text("Thread-Worker-Test", encoding="utf-8")

    worker = ChecksumWorker(str(sample), algorithms=("md5", "sha256"))
    done_results = []
    worker.finished.connect(lambda res: done_results.append(res))

    worker.run()

    assert len(done_results) == 1
    assert "sha256" in done_results[0]
    assert "md5" in done_results[0]
