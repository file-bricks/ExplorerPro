#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_diff_service_perf.py - Tests für High-End Performance-Optimierungen im diff_service.
"""

from __future__ import annotations

from pathlib import Path

from core.diff_service import (
    _quick_prefix_differs,
    compare_files,
    compute_sha256,
)


def test_quick_prefix_differs_detects_mismatch(tmp_path: Path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"A" * 8192 + b"SUFFIX")
    f2.write_bytes(b"B" * 8192 + b"SUFFIX")

    assert _quick_prefix_differs(str(f1), str(f2), sample_size=8192) is True


def test_quick_prefix_differs_detects_match(tmp_path: Path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"SAME_HEADER" * 500)
    f2.write_bytes(b"SAME_HEADER" * 500)

    assert _quick_prefix_differs(str(f1), str(f2), sample_size=8192) is False


def test_diff_size_mismatch_early_exit(tmp_path: Path):
    f1 = tmp_path / "small.txt"
    f2 = tmp_path / "large.txt"
    f1.write_text("Hello", encoding="utf-8")
    f2.write_text("Hello World and more", encoding="utf-8")

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is False
    assert result.file1_size != result.file2_size
    assert len(result.file1_hash) == 64
    assert len(result.file2_hash) == 64


def test_diff_empty_files_identical(tmp_path: Path):
    f1 = tmp_path / "empty1.txt"
    f2 = tmp_path / "empty2.txt"
    f1.write_bytes(b"")
    f2.write_bytes(b"")

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is True
    assert result.file1_size == 0
    assert result.file2_size == 0


def test_diff_same_size_different_prefix(tmp_path: Path):
    f1 = tmp_path / "f1.dat"
    f2 = tmp_path / "f2.dat"
    # Gleiche Größe (10.000 Bytes), unterschiedlicher Prefix
    f1.write_bytes(b"PREFIX_A" + b"X" * 9992)
    f2.write_bytes(b"PREFIX_B" + b"X" * 9992)

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is False
    assert result.file1_size == result.file2_size


def test_diff_same_size_same_content(tmp_path: Path):
    f1 = tmp_path / "f1.dat"
    f2 = tmp_path / "f2.dat"
    payload = b"IDENTICAL_CONTENT" * 1000
    f1.write_bytes(payload)
    f2.write_bytes(payload)

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is True
    assert result.file1_hash == result.file2_hash


def test_compute_sha256_buffer_size(tmp_path: Path):
    f = tmp_path / "test.bin"
    data = b"\xaa\xbb\xcc\xdd" * 100000
    f.write_bytes(data)

    hash_default = compute_sha256(str(f))
    hash_custom = compute_sha256(str(f), chunk_size=65536)
    assert hash_default == hash_custom
    assert len(hash_default) == 64
