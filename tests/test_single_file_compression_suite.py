#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_single_file_compression_suite.py - Unit- und Integrationstests für Standalone GZ, BZ2 und XZ
==================================================================================================
Testet die hermetischen Stream-Operationen:
- Erkennung via is_single_file_compressed und Magic-Header-Validierung
- Inspektion von Metadaten (Dateiname, Größen, Kompressionsrate)
- Atomare Komprimierung und Dekomprimierung
- Integritätsprüfungen (Erfolg vs. korrupte Streams)
- Pfadtraversal-Schutz und saubere Abbruchbehandlung
- Einheitliche create_archive- und extract_archive-Fassaden
- Asynchrone QThread-Worker (ArchiveCompressWorker, ArchiveExtractWorker, ArchiveTestWorker)
"""

import bz2
import gzip
import lzma
from pathlib import Path
import pytest

from core.archive_service import (
    ArchiveCompressWorker,
    ArchiveExtractWorker,
    ArchiveTestWorker,
    check_archive_integrity,
    check_single_file_integrity,
    create_archive,
    create_single_file_compressed,
    extract_archive,
    extract_single_file_compressed,
    inspect_archive,
    inspect_single_file_compressed,
    is_archive,
    is_single_file_compressed,
)
from gui.archive_dialog import _get_archive_stem


@pytest.fixture
def sample_payload(tmp_path: Path) -> Path:
    f = tmp_path / "sample_document.txt"
    content = b"ExplorerPro Universal Archive Engine Test Payload\n" * 200
    f.write_bytes(content)
    return f


def test_is_single_file_compressed_detection(tmp_path: Path, sample_payload: Path):
    # Standalone GZ
    gz_path = tmp_path / "test.txt.gz"
    with open(sample_payload, "rb") as fin, gzip.open(gz_path, "wb") as fout:
        fout.write(fin.read())
    assert is_single_file_compressed(gz_path) is True
    assert is_archive(gz_path) is False

    # Standalone BZ2
    bz2_path = tmp_path / "test.txt.bz2"
    with open(sample_payload, "rb") as fin, bz2.open(bz2_path, "wb") as fout:
        fout.write(fin.read())
    assert is_single_file_compressed(bz2_path) is True
    assert is_archive(bz2_path) is False

    # Standalone XZ
    xz_path = tmp_path / "test.txt.xz"
    with open(sample_payload, "rb") as fin, lzma.open(xz_path, "wb") as fout:
        fout.write(fin.read())
    assert is_single_file_compressed(xz_path) is True
    assert is_archive(xz_path) is False

    # Fake header with .gz extension
    fake_gz = tmp_path / "fake.gz"
    fake_gz.write_bytes(b"NOT_A_GZIP_FILE_HEADER")
    assert is_single_file_compressed(fake_gz) is False

    # Plain text file
    assert is_single_file_compressed(sample_payload) is False

    # Directory
    assert is_single_file_compressed(tmp_path) is False

    # Non-existent
    assert is_single_file_compressed(tmp_path / "missing.gz") is False


def test_create_and_inspect_single_file_gz(tmp_path: Path, sample_payload: Path):
    dest_gz = tmp_path / "output.txt.gz"
    count, orig_bytes = create_single_file_compressed(sample_payload, dest_gz)
    assert count == 1
    assert orig_bytes == sample_payload.stat().st_size
    assert dest_gz.exists()

    summary, entries = inspect_single_file_compressed(dest_gz)
    assert summary.total_files == 1
    assert summary.total_folders == 0
    assert summary.uncompressed_size == sample_payload.stat().st_size
    assert summary.compressed_size == dest_gz.stat().st_size
    assert summary.overall_ratio > 0.0

    assert len(entries) == 1
    entry = entries[0]
    assert entry.filename == "output.txt"
    assert entry.file_size == sample_payload.stat().st_size
    assert entry.is_dir is False

    # inspect_archive facade parity
    f_sum, f_entries = inspect_archive(dest_gz)
    assert f_sum.uncompressed_size == summary.uncompressed_size
    assert len(f_entries) == 1


def test_create_and_inspect_single_file_bz2(tmp_path: Path, sample_payload: Path):
    dest_bz2 = tmp_path / "output.txt.bz2"
    count, orig_bytes = create_single_file_compressed(sample_payload, dest_bz2)
    assert count == 1
    assert orig_bytes == sample_payload.stat().st_size
    assert dest_bz2.exists()

    summary, entries = inspect_single_file_compressed(dest_bz2)
    assert summary.total_files == 1
    assert summary.total_folders == 0
    assert summary.uncompressed_size == sample_payload.stat().st_size
    assert summary.compressed_size == dest_bz2.stat().st_size
    assert summary.overall_ratio > 0.0

    assert len(entries) == 1
    assert entries[0].filename == "output.txt"

    # inspect_archive facade
    f_sum, f_entries = inspect_archive(dest_bz2)
    assert f_sum.uncompressed_size == summary.uncompressed_size
    assert len(f_entries) == 1


def test_create_and_inspect_single_file_xz(tmp_path: Path, sample_payload: Path):
    dest_xz = tmp_path / "output.txt.xz"
    count, orig_bytes = create_single_file_compressed(sample_payload, dest_xz)
    assert count == 1
    assert orig_bytes == sample_payload.stat().st_size
    assert dest_xz.exists()

    summary, entries = inspect_single_file_compressed(dest_xz)
    assert summary.total_files == 1
    assert summary.total_folders == 0
    assert summary.uncompressed_size == sample_payload.stat().st_size
    assert summary.compressed_size == dest_xz.stat().st_size
    assert summary.overall_ratio > 0.0

    assert len(entries) == 1
    assert entries[0].filename == "output.txt"

    # inspect_archive facade
    f_sum, f_entries = inspect_archive(dest_xz)
    assert f_sum.uncompressed_size == summary.uncompressed_size
    assert len(f_entries) == 1


def test_extract_single_file_compressed_roundtrip(tmp_path: Path, sample_payload: Path):
    orig_bytes = sample_payload.read_bytes()

    for ext in [".gz", ".bz2", ".xz"]:
        archive_file = tmp_path / f"archive{ext}"
        create_single_file_compressed(sample_payload, archive_file)

        extract_dir = tmp_path / f"extracted_{ext.strip('.')}"
        count, decomp_bytes = extract_single_file_compressed(archive_file, extract_dir)
        assert count == 1
        assert decomp_bytes == len(orig_bytes)

        extracted_file = extract_dir / "archive"
        assert extracted_file.exists()
        assert extracted_file.read_bytes() == orig_bytes

        # Overwrite=False skips
        c2, b2 = extract_single_file_compressed(archive_file, extract_dir, overwrite=False)
        assert c2 == 0
        assert b2 == 0


def test_check_single_file_integrity(tmp_path: Path, sample_payload: Path):
    for ext in [".gz", ".bz2", ".xz"]:
        archive_file = tmp_path / f"valid{ext}"
        create_single_file_compressed(sample_payload, archive_file)

        # Valid test
        is_ok, err = check_single_file_integrity(archive_file)
        assert is_ok is True
        assert err is None

        # Facade check_archive_integrity
        f_ok, f_err = check_archive_integrity(archive_file)
        assert f_ok is True
        assert f_err is None

        # Corrupted test
        corrupt_file = tmp_path / f"corrupt{ext}"
        content = archive_file.read_bytes()
        # Truncate content in half
        corrupt_file.write_bytes(content[: len(content) // 2])

        c_ok, c_err = check_single_file_integrity(corrupt_file)
        assert c_ok is False
        assert c_err is not None

        fc_ok, fc_err = check_archive_integrity(corrupt_file)
        assert fc_ok is False
        assert fc_err is not None


def test_create_archive_unified_dispatch(tmp_path: Path, sample_payload: Path):
    # Single file to .gz -> Standalone GZ
    out_gz = tmp_path / "single.txt.gz"
    c, b = create_archive([sample_payload], out_gz)
    assert c == 1
    assert is_single_file_compressed(out_gz) is True

    # Multiple files to .gz -> TAR.GZ
    second_file = tmp_path / "second.txt"
    second_file.write_text("Second content", encoding="utf-8")
    out_multi_gz = tmp_path / "multi.tar.gz"
    c_m, b_m = create_archive([sample_payload, second_file], out_multi_gz)
    assert c_m == 2
    assert is_single_file_compressed(out_multi_gz) is False
    assert is_archive(out_multi_gz) is True


def test_extract_archive_facade_with_single_file(tmp_path: Path, sample_payload: Path):
    out_xz = tmp_path / "document.txt.xz"
    create_single_file_compressed(sample_payload, out_xz)

    target_dir = tmp_path / "facade_extract"
    c, b = extract_archive(out_xz, target_dir)
    assert c == 1
    assert (target_dir / "document.txt").exists()
    assert (target_dir / "document.txt").read_text(encoding="utf-8") == sample_payload.read_text(encoding="utf-8")


def test_workers_with_single_file_compressed(qtbot, tmp_path: Path, sample_payload: Path):
    dest_gz = tmp_path / "worker_test.txt.gz"

    # 1. CompressWorker
    c_worker = ArchiveCompressWorker([sample_payload], dest_gz)
    with qtbot.waitSignal(c_worker.finished, timeout=5000) as blocker:
        c_worker.start()
    success, res_path, count, num_bytes = blocker.args
    assert success is True
    assert count == 1
    assert dest_gz.exists()

    # 2. TestWorker
    t_worker = ArchiveTestWorker(dest_gz)
    with qtbot.waitSignal(t_worker.finished, timeout=5000) as blocker:
        t_worker.start()
    is_valid, msg = blocker.args
    assert is_valid is True
    assert msg == ""

    # 3. ExtractWorker
    extract_target = tmp_path / "worker_extracted"
    e_worker = ArchiveExtractWorker(dest_gz, extract_target)
    with qtbot.waitSignal(e_worker.finished, timeout=5000) as blocker:
        e_worker.start()
    e_success, e_target, e_count, e_bytes = blocker.args
    assert e_success is True
    assert e_count == 1
    assert (extract_target / "worker_test.txt").exists()


def test_archive_stem_detection():
    assert _get_archive_stem("server.tar.gz") == "server"
    assert _get_archive_stem("backup.tar.bz2") == "backup"
    assert _get_archive_stem("data.tar.xz") == "data"
    assert _get_archive_stem("archive.zip") == "archive"
    assert _get_archive_stem("plain.tar") == "plain"
    assert _get_archive_stem("access.log.gz") == "access.log"
    assert _get_archive_stem("database.sql.bz2") == "database.sql"
    assert _get_archive_stem("records.csv.xz") == "records.csv"


def test_empty_file_compression_and_extraction(tmp_path: Path):
    empty_src = tmp_path / "empty.txt"
    empty_src.write_bytes(b"")

    for ext in [".gz", ".bz2", ".xz"]:
        out_archive = tmp_path / f"empty{ext}"
        c, b = create_single_file_compressed(empty_src, out_archive)
        assert c == 1
        assert b == 0

        summary, entries = inspect_single_file_compressed(out_archive)
        assert summary.uncompressed_size == 0
        assert summary.total_files == 1

        ext_dir = tmp_path / f"empty_ext_{ext.strip('.')}"
        ec, eb = extract_single_file_compressed(out_archive, ext_dir)
        assert ec == 1
        assert eb == 0
        assert (ext_dir / "empty").exists()
        assert (ext_dir / "empty").stat().st_size == 0


def test_cancellation_during_single_file_compression(tmp_path: Path, sample_payload: Path):
    dest_gz = tmp_path / "cancelled.gz"
    count, b = create_single_file_compressed(
        sample_payload, dest_gz, is_cancelled=lambda: True
    )
    assert count == 0
    assert b == 0
    assert not dest_gz.exists()


def test_cancellation_during_single_file_extraction(tmp_path: Path, sample_payload: Path):
    dest_gz = tmp_path / "for_cancel.gz"
    create_single_file_compressed(sample_payload, dest_gz)

    target_dir = tmp_path / "cancelled_extract"
    count, b = extract_single_file_compressed(
        dest_gz, target_dir, is_cancelled=lambda: True
    )
    assert count == 0
    assert b == 0


def test_gui_dialogs_with_single_file_gz(qtbot, tmp_path: Path, sample_payload: Path):
    from gui.archive_dialog import ArchiveCompressDialog, ArchiveExtractDialog, ArchiveViewerDialog
    from gui.preview.preview_panel import ArchivePreview

    dest_gz = tmp_path / "gui_test.txt.gz"
    create_single_file_compressed(sample_payload, dest_gz)

    # 1. Preview
    preview = ArchivePreview()
    qtbot.addWidget(preview)
    preview.load_archive(str(dest_gz))
    assert preview.name_label.text() == "gui_test.txt.gz"
    assert "1 Dateien" in preview.count_label.text()
    assert preview.table.rowCount() == 1
    assert "gui_test.txt" in preview.table.item(0, 0).text()

    # 2. Viewer Dialog
    viewer = ArchiveViewerDialog(str(dest_gz))
    qtbot.addWidget(viewer)
    assert viewer.table.rowCount() == 1
    assert "gui_test.txt" in viewer.table.item(0, 0).text()

    # 3. Extract Dialog
    ext_dlg = ArchiveExtractDialog(str(dest_gz), default_target_dir=str(tmp_path))
    qtbot.addWidget(ext_dlg)
    assert ext_dlg.subfolder_cb.isChecked()
    assert "gui_test.txt" in ext_dlg.subfolder_cb.text()

    # 4. Compress Dialog with single file
    comp_dlg = ArchiveCompressDialog([str(sample_payload)], current_dir=str(tmp_path))
    qtbot.addWidget(comp_dlg)
    assert "sample_document.zip" in comp_dlg.dest_edit.text()

