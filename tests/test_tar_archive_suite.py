#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_tar_archive_suite.py - Umfassende Vertragstests für die TAR- & Universal-Archiv-Suite
===========================================================================================
Testet:
- ArchiveService: TAR-Inspektion (uncompressed, gz, bz2, xz)
- Tar-Slip-Sicherheitsabwehr (Path Traversal Detection)
- Integritätsprüfungen für TAR-Archive
- Sichere und atomare Extraktion
- Universelle Einstiegspunkte (is_archive, inspect_archive, extract_archive, check_archive_integrity)
- Asynchrone QThread-Worker für TAR-Dateien
"""

import io
from pathlib import Path
import tarfile
import time
import zipfile
import pytest

from core.archive_service import (
    ArchiveCompressWorker,
    ArchiveExtractWorker,
    ArchiveTestWorker,
    ArchiveSummary,
    ArchiveEntry,
    ZipSlipSecurityError,
    TarSlipSecurityError,
    check_archive_integrity,
    check_tar_integrity,
    create_archive,
    create_tar_archive,
    create_zip_archive,
    extract_archive,
    extract_tar_archive,
    inspect_archive,
    inspect_tar,
    inspect_zip,
    is_archive,
    sanitize_archive_member_path,
)


def test_create_and_inspect_tar_uncompressed(tmp_path: Path):
    src_dir = tmp_path / "sample_folder"
    src_dir.mkdir()
    f1 = src_dir / "text1.txt"
    f1.write_text("Hello World! This is an uncompressed tar test." * 5, encoding="utf-8")
    sub_dir = src_dir / "nested"
    sub_dir.mkdir()
    f2 = sub_dir / "doc.md"
    f2.write_text("# Markdown\nContent here.", encoding="utf-8")

    out_tar = tmp_path / "output.tar"
    count, total_bytes = create_tar_archive([src_dir], out_tar, mode="w")
    assert count == 2
    assert total_bytes > 0
    assert out_tar.is_file()

    summary, entries = inspect_tar(out_tar)
    assert summary.total_files == 2
    assert summary.total_folders >= 1
    assert summary.uncompressed_size == total_bytes
    assert summary.compressed_size == out_tar.stat().st_size
    assert len(entries) >= 2


def test_create_and_inspect_tar_gz(tmp_path: Path):
    src_dir = tmp_path / "gz_folder"
    src_dir.mkdir()
    for i in range(5):
        (src_dir / f"file_{i}.txt").write_text(f"Line content {i}\n" * 50, encoding="utf-8")

    out_tgz = tmp_path / "output.tar.gz"
    count, total_bytes = create_tar_archive([src_dir], out_tgz, mode="w:gz")
    assert count == 5
    assert total_bytes > 0
    assert out_tgz.is_file()

    summary, entries = inspect_archive(out_tgz)
    assert summary.total_files == 5
    assert summary.compressed_size < summary.uncompressed_size
    assert summary.overall_ratio > 0.0


def test_create_and_inspect_tar_bz2(tmp_path: Path):
    src_dir = tmp_path / "bz2_folder"
    src_dir.mkdir()
    (src_dir / "sample.log").write_text("Log message content\n" * 100, encoding="utf-8")

    out_tbz = tmp_path / "output.tar.bz2"
    count, total_bytes = create_archive([src_dir], out_tbz)
    assert count == 1
    assert out_tbz.is_file()

    summary, entries = inspect_archive(out_tbz)
    assert summary.total_files == 1
    assert len(entries) >= 1


def test_create_and_inspect_tar_xz(tmp_path: Path):
    src_dir = tmp_path / "xz_folder"
    src_dir.mkdir()
    (src_dir / "data.json").write_text('{"key": "value"}\n' * 50, encoding="utf-8")

    out_txz = tmp_path / "output.tar.xz"
    count, total_bytes = create_archive([src_dir], out_txz)
    assert count == 1
    assert out_txz.is_file()

    summary, entries = inspect_archive(out_txz)
    assert summary.total_files == 1


def test_extract_tar_archive_safe(tmp_path: Path):
    src_file = tmp_path / "testfile.txt"
    test_content = "Crucial test file content with utf-8: Überprüfungen & Zeichen."
    src_file.write_text(test_content, encoding="utf-8")

    out_tar = tmp_path / "test.tar.gz"
    create_tar_archive([src_file], out_tar, mode="w:gz")

    extract_dest = tmp_path / "extracted_dir"
    count, bytes_out = extract_tar_archive(out_tar, extract_dest)
    assert count == 1
    assert bytes_out == len(test_content.encode("utf-8"))

    restored_file = extract_dest / "testfile.txt"
    assert restored_file.is_file()
    assert restored_file.read_text(encoding="utf-8") == test_content


def test_extract_tar_selected_members(tmp_path: Path):
    src_dir = tmp_path / "multi_files"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep this", encoding="utf-8")
    (src_dir / "ignore.txt").write_text("ignore this", encoding="utf-8")

    out_tar = tmp_path / "selection.tar"
    create_tar_archive([src_dir], out_tar, mode="w")

    extract_dest = tmp_path / "selective_extracted"
    count, _ = extract_tar_archive(out_tar, extract_dest, members=["multi_files/keep.txt"])
    assert count == 1
    assert (extract_dest / "multi_files" / "keep.txt").is_file()
    assert not (extract_dest / "multi_files" / "ignore.txt").exists()


def test_tar_slip_defense_blocks_path_traversal(tmp_path: Path):
    # Künstlich bösartiges TAR mit Path Traversal erstellen
    bad_tar = tmp_path / "malicious.tar"
    with tarfile.open(bad_tar, "w") as tf:
        data = b"malicious content"
        ti = tarfile.TarInfo(name="../../outside_target.txt")
        ti.size = len(data)
        ti.mtime = time.time()
        tf.addfile(ti, io.BytesIO(data))

    target_dir = tmp_path / "safe_sandbox"
    target_dir.mkdir()

    with pytest.raises(ZipSlipSecurityError):
        extract_tar_archive(bad_tar, target_dir)

    assert not (tmp_path / "outside_target.txt").exists()


def test_check_tar_integrity(tmp_path: Path):
    src_file = tmp_path / "doc.txt"
    src_file.write_text("Integrity check content", encoding="utf-8")

    good_tar = tmp_path / "valid.tar.gz"
    create_tar_archive([src_file], good_tar, mode="w:gz")

    is_valid, msg = check_tar_integrity(good_tar)
    assert is_valid is True
    assert msg is None

    # Korrupte Datei testen
    corrupt_tar = tmp_path / "corrupt.tar.gz"
    corrupt_tar.write_bytes(good_tar.read_bytes()[:100] + b"\x00" * 50)

    is_valid_bad, msg_bad = check_tar_integrity(corrupt_tar)
    assert is_valid_bad is False
    assert msg_bad is not None


def test_is_archive_detector(tmp_path: Path):
    assert is_archive(tmp_path / "archive.zip") is False  # existiert noch nicht

    zip_file = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("test.txt", "content")
    assert is_archive(zip_file) is True

    tar_file = tmp_path / "test.tar.gz"
    with tarfile.open(tar_file, "w:gz") as tf:
        pass
    assert is_archive(tar_file) is True

    plain_txt = tmp_path / "plain.txt"
    plain_txt.write_text("just text", encoding="utf-8")
    assert is_archive(plain_txt) is False


def test_universal_extract_and_integrity(tmp_path: Path):
    src_file = tmp_path / "input.txt"
    src_file.write_text("Universal archive test", encoding="utf-8")

    # ZIP
    zip_path = tmp_path / "uni.zip"
    create_archive([src_file], zip_path)
    ok_zip, _ = check_archive_integrity(zip_path)
    assert ok_zip is True

    dest_zip = tmp_path / "dest_zip"
    c_z, _ = extract_archive(zip_path, dest_zip)
    assert c_z == 1
    assert (dest_zip / "input.txt").is_file()

    # TAR.GZ
    tgz_path = tmp_path / "uni.tar.gz"
    create_archive([src_file], tgz_path)
    ok_tgz, _ = check_archive_integrity(tgz_path)
    assert ok_tgz is True

    dest_tgz = tmp_path / "dest_tgz"
    c_t, _ = extract_archive(tgz_path, dest_tgz)
    assert c_t == 1
    assert (dest_tgz / "input.txt").is_file()


def test_archive_workers_with_tar(tmp_path: Path, qtbot):
    src_file = tmp_path / "worker_test.txt"
    src_file.write_text("Worker testing for tar", encoding="utf-8")
    out_tar = tmp_path / "worker_out.tar.gz"

    # Compress worker
    compress_worker = ArchiveCompressWorker([src_file], out_tar)
    with qtbot.waitSignal(compress_worker.finished, timeout=5000) as blocker:
        compress_worker.start()

    success, path, count, bytes_count = blocker.args
    assert success is True
    assert count == 1
    assert out_tar.is_file()

    # Test worker
    test_worker = ArchiveTestWorker(out_tar)
    with qtbot.waitSignal(test_worker.finished, timeout=5000) as blocker:
        test_worker.start()

    is_valid, _ = blocker.args
    assert is_valid is True

    # Extract worker
    extract_dir = tmp_path / "worker_extracted"
    extract_worker = ArchiveExtractWorker(out_tar, extract_dir)
    with qtbot.waitSignal(extract_worker.finished, timeout=5000) as blocker:
        extract_worker.start()

    ext_success, ext_dir, ext_count, _ = blocker.args
    assert ext_success is True
    assert ext_count == 1
    assert (extract_dir / "worker_test.txt").is_file()


def test_atomic_replacement_on_create_zip_and_tar(tmp_path: Path):
    src_file = tmp_path / "source.txt"
    src_file.write_text("version 1", encoding="utf-8")

    target_zip = tmp_path / "replace_target.zip"
    create_zip_archive([src_file], target_zip)
    assert target_zip.is_file()

    # Update source and replace archive
    src_file.write_text("version 2 with more text", encoding="utf-8")
    create_zip_archive([src_file], target_zip)
    summary, entries = inspect_zip(target_zip)
    assert summary.total_files == 1

    # TAR replacement
    target_tar = tmp_path / "replace_target.tar.gz"
    create_tar_archive([src_file], target_tar)
    assert target_tar.is_file()
    create_tar_archive([src_file], target_tar)
    sum_tar, ent_tar = inspect_tar(target_tar)
    assert sum_tar.total_files == 1
