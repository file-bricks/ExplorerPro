#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_bugsweep_archive_security_and_resilience_20261118.py
=========================================================
Hermetische Regressionstests für den Bugsweep-Lauf 2026-11-18:
1. Unterordner-Stammnamen-Traversal & Windows-Gerätenamen in _get_archive_stem
2. Pfad-Sanitisierung gegen leere/Root-Member, Windows-Gerätenamen, NTFS-ADS & Symlinks
3. Selbst-Einschluss-Schutz, Prä-1980-Zeitstempel & Read-Only-Overwrite bei Archiven
4. Selektive Ordner-Extraktion (members=["folder/"]) in ZIP, TAR & ArchiveViewerDialog
5. Präzise Einzelstream-Abgrenzung (.gz/.bz2/.xz/.tar.zst) in is_archive & PreviewPanel
"""

import bz2
import gzip
import io
import lzma
import os
from pathlib import Path
import stat
import tarfile
import time
import zipfile

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from core.archive_service import (
    ZipSlipSecurityError,
    check_zip_integrity,
    create_tar_archive,
    create_zip_archive,
    extract_tar_archive,
    extract_zip_archive,
    inspect_tar,
    inspect_zip,
    is_archive,
    sanitize_archive_member_path,
)
from gui.archive_dialog import (
    ArchiveCompressDialog,
    ArchiveExtractDialog,
    ArchiveViewerDialog,
    _get_archive_stem,
)


@pytest.fixture
def qapp_guard():
    app = QApplication.instance() or QApplication([])
    prev = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    try:
        yield app
    finally:
        app.processEvents()
        app.setQuitOnLastWindowClosed(prev)


def _wait_until(predicate, timeout_s: float = 5.0) -> None:
    app = QApplication.instance()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if app is not None:
            app.processEvents()
        if predicate():
            if app is not None:
                app.processEvents()
            return
        time.sleep(0.02)
    assert predicate(), "Timeout while waiting for asynchronous archive operation"


def test_get_archive_stem_blocks_traversal_empty_and_windows_devices(tmp_path: Path):
    base = tmp_path / "downloads"
    base.mkdir()

    for dangerous_name in ("..tar.gz", "...tar.gz", "...zip", "..zip", ".zip", ".tar.gz", "....tar.xz"):
        stem = _get_archive_stem(dangerous_name)
        assert stem not in ("", ".", ".."), f"Unsafe stem {stem!r} for {dangerous_name!r}"
        resolved = (base / stem).resolve()
        assert resolved.parent == base.resolve()

    for dev_archive in ("CON.zip", "nul.tar.gz", "COM1.tgz", "lpt9.tar.xz", "prn.tar"):
        dev_stem = _get_archive_stem(dev_archive)
        assert dev_stem.upper() not in {"CON", "NUL", "COM1", "LPT9", "PRN"}
        assert (base / dev_stem).resolve().parent == base.resolve()

    assert not _get_archive_stem("report..zip").endswith(".")
    assert _get_archive_stem("my_backup.zip") == "my_backup"
    assert _get_archive_stem("archive.tar.gz") == "archive"
    assert _get_archive_stem("document.pdf") == "document"


def test_extract_dialog_and_browser_keep_crafted_archive_inside_base_dir(
    tmp_path: Path, qapp_guard, monkeypatch
):
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    victim = tmp_path / "victim.txt"
    victim.write_text("KEEP_ORIGINAL", encoding="utf-8")

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    crafted_tar = downloads / "...tar.gz"

    payload_src = tmp_path / "payload_src.txt"
    payload_src.write_text("OVERWRITTEN_BY_ARCHIVE", encoding="utf-8")
    with tarfile.open(crafted_tar, "w:gz") as tf:
        tf.add(str(payload_src), arcname="victim.txt")

    dlg = ArchiveExtractDialog(str(crafted_tar), default_target_dir=str(downloads))
    try:
        assert dlg.subfolder_cb.isChecked()
        dlg._start_extraction()
        assert dlg.worker is not None
        _wait_until(lambda: not dlg.worker.isRunning())

        assert Path(dlg.extracted_target).resolve().parent == downloads.resolve()
        assert victim.read_text(encoding="utf-8") == "KEEP_ORIGINAL"
        assert (
            Path(dlg.extracted_target) / "victim.txt"
        ).read_text(encoding="utf-8") == "OVERWRITTEN_BY_ARCHIVE"
    finally:
        dlg.close()

    from gui.browser.file_browser import FileBrowser

    downloads2 = tmp_path / "downloads2"
    downloads2.mkdir()
    victim2 = tmp_path / "victim2.txt"
    victim2.write_text("SAFE_PARENT", encoding="utf-8")
    crafted_zip = downloads2 / "...zip"
    with zipfile.ZipFile(crafted_zip, "w") as zf:
        zf.writestr("victim2.txt", "EVIL")

    browser = FileBrowser()
    try:
        browser._current_path = str(downloads2)
        browser.refresh = lambda: None
        browser._extract_archive_here(str(crafted_zip))
        _wait_until(lambda: not browser._archive_task_dialogs)
    finally:
        browser.close()

    assert victim2.read_text(encoding="utf-8") == "SAFE_PARENT"
    assert (downloads2 / "extracted_archive" / "victim2.txt").read_text(encoding="utf-8") == "EVIL"


def test_sanitize_archive_member_path_rejects_empty_root_ads_and_devices(tmp_path: Path):
    target = tmp_path / "jail"
    target.mkdir()

    invalid_everywhere = [
        "",
        ".",
        "./",
        "/",
        "C:/",
        "   ",
        "bad\x00name.txt",
    ]
    windows_only_invalid = [
        "a:stream",
        "doc.txt:evil_stream",
        "sub/file.txt:$DATA",
        "CON.txt",
        "sub/NUL",
        "COM1.log",
        "LPT2",
        "trailing./file.txt",
        "folder/bad ",
    ]
    for bad in invalid_everywhere:
        for windows_rules in (True, False):
            with pytest.raises(ZipSlipSecurityError, match="."):
                sanitize_archive_member_path(bad, target, windows_rules=windows_rules)
    for bad in windows_only_invalid:
        with pytest.raises(ZipSlipSecurityError, match="."):
            sanitize_archive_member_path(bad, target, windows_rules=True)
        # Unter Linux/macOS sind diese Namen gültig und bleiben im Zielordner.
        accepted = sanitize_archive_member_path(bad, target, windows_rules=False)
        accepted.relative_to(target.resolve())

    good = sanitize_archive_member_path("./folder/sub/doc.txt", target)
    assert good == (target / "folder" / "sub" / "doc.txt").resolve()


def test_sanitize_windows_rules_default_follows_platform(tmp_path: Path, monkeypatch):
    target = tmp_path / "jail"
    target.mkdir()
    import core.archive_service as archive_service

    monkeypatch.setattr(archive_service, "_windows_name_rules_default", lambda: True)
    with pytest.raises(ZipSlipSecurityError):
        sanitize_archive_member_path("log 12:30.txt", target)
    monkeypatch.setattr(archive_service, "_windows_name_rules_default", lambda: False)
    assert sanitize_archive_member_path("log 12:30.txt", target).name == "log 12:30.txt"


def _write_tar(path: Path, names: list[str]) -> None:
    with tarfile.open(path, "w") as tf:
        for name in names:
            data = name.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_extract_tar_with_posix_legal_names_is_complete_or_untouched(tmp_path: Path):
    archive = tmp_path / "logs.tar"
    _write_tar(archive, ["a.txt", "log 12:30.txt", "z.txt"])
    target = tmp_path / "out"

    if os.name == "nt":
        with pytest.raises(ZipSlipSecurityError):
            extract_tar_archive(archive, target)
        assert list(target.iterdir()) == []
    else:
        count, _ = extract_tar_archive(archive, target)
        assert count == 3
        assert sorted(p.name for p in target.iterdir()) == ["a.txt", "log 12:30.txt", "z.txt"]


def test_extract_rejects_traversal_before_writing_anything(tmp_path: Path):
    tar_archive = tmp_path / "evil.tar"
    _write_tar(tar_archive, ["a.txt", "../escape.txt", "z.txt"])
    tar_target = tmp_path / "tar_out"
    with pytest.raises(ZipSlipSecurityError):
        extract_tar_archive(tar_archive, tar_target)
    assert list(tar_target.iterdir()) == []
    assert not (tmp_path / "escape.txt").exists()

    zip_archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_archive, "w") as zf:
        zf.writestr("a.txt", "a")
        zf.writestr("../escape.txt", "evil")
        zf.writestr("z.txt", "z")
    zip_target = tmp_path / "zip_out"
    with pytest.raises(ZipSlipSecurityError):
        extract_zip_archive(zip_archive, zip_target)
    assert list(zip_target.iterdir()) == []


def test_extract_blocks_symlink_escape_and_skips_zip_symlink_entries(
    tmp_path: Path, monkeypatch
):
    # 1. ZIP mit Unix-Symlink-Eintrag (S_IFLNK) darf keinen Symlink/Payload extrahieren
    zip_with_link = tmp_path / "with_symlink.zip"
    with zipfile.ZipFile(zip_with_link, "w") as zf:
        link_info = zipfile.ZipInfo("passwd_link")
        link_info.create_system = 3  # Unix
        link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(link_info, "/etc/passwd")
        zf.writestr("regular.txt", "safe content")

    out_zip_dir = tmp_path / "out_zip"
    count, _ = extract_zip_archive(zip_with_link, out_zip_dir)
    assert count == 1
    assert (out_zip_dir / "regular.txt").read_text(encoding="utf-8") == "safe content"
    assert not (out_zip_dir / "passwd_link").exists()

    # 2. Symlink-Komponente unterhalb von target_dir muss blockiert werden
    jail = tmp_path / "symlink_jail"
    jail.mkdir()
    escape_sub = jail / "linked_sub"
    escape_sub.mkdir()
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: True if self == escape_sub.resolve() or self.name == "linked_sub" else real_is_symlink(self),
    )
    with pytest.raises(ZipSlipSecurityError):
        sanitize_archive_member_path("linked_sub/pwned.txt", jail)
    monkeypatch.undo()

    # 3. Legitimes tar -C dir . Archiv mit "./" Verzeichnis-Header funktioniert,
    #    aber reguläre Datei namens "." wird mit ZipSlipSecurityError abgewiesen.
    dot_dir_tar = tmp_path / "dot_dir.tar"
    with tarfile.open(dot_dir_tar, "w") as tf:
        d_info = tarfile.TarInfo(name="./")
        d_info.type = tarfile.DIRTYPE
        d_info.mtime = time.time()
        tf.addfile(d_info)

        payload = b"hello from dot tar"
        f_info = tarfile.TarInfo(name="./hello.txt")
        f_info.size = len(payload)
        f_info.mtime = time.time()
        tf.addfile(f_info, io.BytesIO(payload))

    out_dot = tmp_path / "out_dot"
    c_dot, _ = extract_tar_archive(dot_dir_tar, out_dot)
    assert c_dot == 1
    assert (out_dot / "hello.txt").read_bytes() == b"hello from dot tar"

    bad_root_file_tar = tmp_path / "bad_root_file.tar"
    with tarfile.open(bad_root_file_tar, "w") as tf:
        payload = b"overwrite root"
        f_info = tarfile.TarInfo(name=".")
        f_info.type = tarfile.REGTYPE
        f_info.size = len(payload)
        f_info.mtime = time.time()
        tf.addfile(f_info, io.BytesIO(payload))

    with pytest.raises(ZipSlipSecurityError):
        extract_tar_archive(bad_root_file_tar, tmp_path / "out_bad_root")


def test_create_zip_and_tar_exclude_destination_self_inclusion_and_staging(
    tmp_path: Path, qapp_guard
):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "alpha.txt").write_text("alpha payload", encoding="utf-8")

    in_place_zip = project_dir / "bundle.zip"
    c1, _ = create_zip_archive([project_dir], in_place_zip)
    assert c1 == 1
    c2, _ = create_zip_archive([project_dir], in_place_zip)
    assert c2 == 1
    _, zip_entries = inspect_zip(in_place_zip)
    zip_names = [e.filename for e in zip_entries]
    assert zip_names == ["project/alpha.txt"]

    in_place_zip.unlink()

    in_place_tar = project_dir / "bundle.tar.gz"
    t1, _ = create_tar_archive([project_dir], in_place_tar, mode="w:gz")
    assert t1 == 1
    t2, _ = create_tar_archive([project_dir], in_place_tar, mode="w:gz")
    assert t2 == 1
    _, tar_entries = inspect_tar(in_place_tar)
    tar_file_names = [e.filename for e in tar_entries if not e.is_dir]
    assert tar_file_names == ["project/alpha.txt"]

    dlg = ArchiveCompressDialog([str(project_dir)], current_dir=str(project_dir))
    try:
        default_dest = Path(dlg.dest_edit.text()).resolve()
        assert default_dest.parent == project_dir.parent.resolve()
    finally:
        dlg.close()


def test_create_zip_archive_clamps_pre_1980_timestamps_and_overwrites_readonly_dest(
    tmp_path: Path,
):
    epoch_file = tmp_path / "epoch_1970.txt"
    epoch_file.write_text("UNIX epoch 1970 content", encoding="utf-8")
    os.utime(epoch_file, (86400, 86400))

    pre_1970_file = tmp_path / "pre_1970.txt"
    pre_1970_file.write_text("Pre-1970 negative mtime", encoding="utf-8")
    try:
        os.utime(pre_1970_file, (-157766400, -157766400))
    except (OSError, OverflowError, ValueError):
        os.utime(pre_1970_file, (0, 0))

    future_2150_file = tmp_path / "future_2150.txt"
    future_2150_file.write_text("Post-2107 future mtime", encoding="utf-8")
    try:
        os.utime(future_2150_file, (5680281600, 5680281600))
        has_future = True
    except (OSError, OverflowError, ValueError):
        has_future = False

    sources = [epoch_file, pre_1970_file] + ([future_2150_file] if has_future else [])
    dest_zip = tmp_path / "epoch.zip"
    count, total_bytes = create_zip_archive(sources, dest_zip)
    assert count == len(sources)
    assert total_bytes > 0

    ok, err = check_zip_integrity(dest_zip)
    assert ok is True
    assert err is None

    _, entries = inspect_zip(dest_zip)
    by_name = {e.filename: e for e in entries}
    assert by_name["epoch_1970.txt"].date_time == (1980, 1, 1, 0, 0, 0)
    assert by_name["pre_1970.txt"].date_time == (1980, 1, 1, 0, 0, 0)
    if has_future:
        assert by_name["future_2150.txt"].date_time == (2107, 12, 31, 23, 59, 58)

    os.chmod(dest_zip, stat.S_IREAD)
    try:
        count2, _ = create_zip_archive([epoch_file], dest_zip)
        assert count2 == 1

        out_dir = tmp_path / "extracted_ro"
        extract_zip_archive(dest_zip, out_dir)
        extracted_file = out_dir / "epoch_1970.txt"
        assert extracted_file.read_text(encoding="utf-8") == "UNIX epoch 1970 content"

        os.chmod(extracted_file, stat.S_IREAD)
        count3, _ = extract_zip_archive(dest_zip, out_dir, overwrite=True)
        assert count3 == 1
    finally:
        if dest_zip.exists():
            os.chmod(dest_zip, stat.S_IWRITE | stat.S_IREAD)
        ro_target = tmp_path / "extracted_ro" / "epoch_1970.txt"
        if ro_target.exists():
            os.chmod(ro_target, stat.S_IWRITE | stat.S_IREAD)


def test_selective_folder_extraction_in_zip_tar_and_viewer_dialog(
    tmp_path: Path, qapp_guard, monkeypatch
):
    src_root = tmp_path / "workspace"
    nested = src_root / "nested" / "sub"
    nested.mkdir(parents=True)
    (src_root / "nested" / "a.txt").write_text("file A", encoding="utf-8")
    (nested / "b.txt").write_text("file B", encoding="utf-8")
    other = src_root / "other"
    other.mkdir()
    (other / "c.txt").write_text("file C", encoding="utf-8")

    zip_path = tmp_path / "folders.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nested/", "")
        zf.writestr("nested/a.txt", "file A")
        zf.writestr("nested/sub/b.txt", "file B")
        zf.writestr("nested2/intruder.txt", "do not match prefix neighbor")
        zf.writestr("other/", "")
        zf.writestr("other/c.txt", "file C")

    out_zip_sel = tmp_path / "out_zip_sel"
    c_zip, _ = extract_zip_archive(zip_path, out_zip_sel, members=["nested/"])
    assert c_zip == 2
    assert (out_zip_sel / "nested" / "a.txt").read_text(encoding="utf-8") == "file A"
    assert (out_zip_sel / "nested" / "sub" / "b.txt").read_text(encoding="utf-8") == "file B"
    assert not (out_zip_sel / "other" / "c.txt").exists()
    assert not (out_zip_sel / "nested2" / "intruder.txt").exists()

    tar_path = tmp_path / "folders.tar.gz"
    create_tar_archive([src_root / "nested", src_root / "other"], tar_path, mode="w:gz")

    out_tar_sel = tmp_path / "out_tar_sel"
    c_tar, _ = extract_tar_archive(tar_path, out_tar_sel, members=["nested"])
    assert c_tar == 2
    assert (out_tar_sel / "nested" / "a.txt").read_text(encoding="utf-8") == "file A"
    assert (out_tar_sel / "nested" / "sub" / "b.txt").read_text(encoding="utf-8") == "file B"
    assert not (out_tar_sel / "other" / "c.txt").exists()

    viewer_out = tmp_path / "viewer_out"
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: str(viewer_out),
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.StandardButton.Ok,
    )

    dlg = ArchiveViewerDialog(str(zip_path))
    try:
        dlg.table.selectRow(0)
        dlg._extract_selected()
        assert dlg.extract_worker is not None
        _wait_until(lambda: not dlg.extract_worker.isRunning())
    finally:
        dlg.close()

    assert (viewer_out / "nested" / "a.txt").is_file()
    assert (viewer_out / "nested" / "sub" / "b.txt").is_file()
    assert not (viewer_out / "other" / "c.txt").exists()


def test_is_archive_rejects_standalone_compressed_streams_and_unsupported_zst(
    tmp_path: Path, qapp_guard
):
    gz_single = tmp_path / "server.log.gz"
    gz_single.write_bytes(gzip.compress(b"2026-11-18 INFO booted\n"))

    bz2_single = tmp_path / "dump.sql.bz2"
    bz2_single.write_bytes(bz2.compress(b"SELECT 1;\n"))

    xz_single = tmp_path / "metrics.json.xz"
    xz_single.write_bytes(lzma.compress(b'{"ok": true}\n'))

    zst_unsupported = tmp_path / "backup.tar.zst"
    zst_unsupported.write_bytes(b"\x28\xb5\x2f\xfd\x00\x58\x01\x00\x00")

    assert is_archive(gz_single) is False
    assert is_archive(bz2_single) is False
    assert is_archive(xz_single) is False
    assert is_archive(zst_unsupported) is False

    disguised_tgz = tmp_path / "tarball_named_only.gz"
    src_f = tmp_path / "note.txt"
    src_f.write_text("inside tar", encoding="utf-8")
    with tarfile.open(disguised_tgz, "w:gz") as tf:
        tf.add(str(src_f), arcname="note.txt")
    assert is_archive(disguised_tgz) is True

    from gui.preview.preview_panel import PreviewPanel

    panel = PreviewPanel()
    try:
        panel.show_preview(str(gz_single))
        assert panel.preview_stack.currentIndex() != 7
        panel.show_preview(str(disguised_tgz))
        assert panel.preview_stack.currentIndex() == 7
    finally:
        panel.close()
