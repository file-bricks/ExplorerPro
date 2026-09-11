#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_diff_service.py - Tests für den Datei-Vergleichsdienst (TW-EP-10)
"""

import pytest
from pathlib import Path

from core.diff_service import (
    is_binary_file,
    compute_sha256,
    compare_files,
    generate_unified_diff_text,
)


def test_is_binary_file(tmp_path: Path):
    text_file = tmp_path / "plain.txt"
    text_file.write_text("Hello World\nLine 2\n", encoding="utf-8")
    assert not is_binary_file(str(text_file))

    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"GIF89a\x00\x01\x00\x01\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04")
    assert is_binary_file(str(bin_file))

    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    assert not is_binary_file(str(empty_file))


def test_compute_sha256(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("ExplorerPro SHA Test", encoding="utf-8")
    sha = compute_sha256(str(f))
    assert len(sha) == 64
    assert sha == compute_sha256(str(f))


def test_compare_files_identical(tmp_path: Path):
    f1 = tmp_path / "doc1.txt"
    f2 = tmp_path / "doc2.txt"
    content = "Line 1\nLine 2\nLine 3\n"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is True
    assert result.is_binary is False
    assert result.stats["added"] == 0
    assert result.stats["deleted"] == 0
    assert result.stats["identical"] == 3
    assert len(result.lines) == 3
    assert all(line_item.tag == "equal" for line_item in result.lines)


def test_compare_files_with_differences(tmp_path: Path):
    f1 = tmp_path / "v1.txt"
    f2 = tmp_path / "v2.txt"
    f1.write_text("Alpha\nBeta\nGamma\n", encoding="utf-8")
    f2.write_text("Alpha\nBeta Modified\nGamma\nDelta\n", encoding="utf-8")

    result = compare_files(str(f1), str(f2))
    assert result.is_identical is False
    assert result.is_binary is False
    assert result.stats["added"] > 0
    assert result.stats["deleted"] > 0
    assert result.stats["identical"] == 2  # Alpha and Gamma

    # Verify tags
    tags = [line_item.tag for line_item in result.lines]
    assert "equal" in tags
    assert "delete" in tags
    assert "insert" in tags


def test_compare_binary_files(tmp_path: Path):
    b1 = tmp_path / "bin1.dat"
    b2 = tmp_path / "bin2.dat"
    b1.write_bytes(b"\x00\x01\x02\x03")
    b2.write_bytes(b"\x00\x01\x02\x04")

    res = compare_files(str(b1), str(b2))
    assert res.is_binary is True
    assert res.is_identical is False
    assert len(res.lines) == 1
    assert res.lines[0].tag == "info"

    # Same binary
    b3 = tmp_path / "bin3.dat"
    b3.write_bytes(b"\x00\x01\x02\x03")
    res_same = compare_files(str(b1), str(b3))
    assert res_same.is_binary is True
    assert res_same.is_identical is True


def test_compare_nonexistent_files():
    with pytest.raises(FileNotFoundError):
        compare_files("nonexistent_left.txt", "nonexistent_right.txt")


def test_generate_unified_diff_text(tmp_path: Path):
    f1 = tmp_path / "orig.txt"
    f2 = tmp_path / "mod.txt"
    f1.write_text("Apple\nBanana\nCherry\n", encoding="utf-8")
    f2.write_text("Apple\nBlueberry\nCherry\nDate\n", encoding="utf-8")

    diff_text = generate_unified_diff_text(str(f1), str(f2))
    assert "---" in diff_text
    assert "+++" in diff_text
    assert "-Banana" in diff_text
    assert "+Blueberry" in diff_text
    assert "+Date" in diff_text
