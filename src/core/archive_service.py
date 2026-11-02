#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_service.py - Native ZIP- und Archiv-Dienste für ExplorerPro
==================================================================
Bietet sichere, hermetische Archiv-Operationen:
- Multi-Item ZIP- & TAR-Komprimierung (Dateien & Ordner rekursiv) mit atomarem Write
- Zip-Slip- und Tar-Slip-geschützte Extraktion mit Pfadtraversal-Abwehr
- Archiv-Inspektion & Metadaten (Dateiliste, Kompressionsraten, Ordnerstrukturen)
- Archiv-Integritätsprüfung (CRC/Checksummen- & Stream-Test)
- Asynchrone QThread-Worker mit Fortschritts- und Abbruchsignalen
"""

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import stat
import tarfile
import time
from typing import Callable, List, Optional, Tuple
import zipfile

from PySide6.QtCore import QThread, Signal


class ZipSlipSecurityError(Exception):
    """Wird ausgelöst, wenn ein Archive-Eintrag versucht, das Zielverzeichnis zu verlassen."""
    pass


# Alias zur semantischen Konsistenz bei TAR-Archiven
TarSlipSecurityError = ZipSlipSecurityError


@dataclass
class ArchiveEntry:
    """Repräsentiert einen einzelnen Eintrag in einem ZIP- oder TAR-Archiv."""
    filename: str
    file_size: int
    compress_size: int
    is_dir: bool
    date_time: Tuple[int, int, int, int, int, int]
    crc: int
    compression_ratio: float
    comment: str = ""

    @property
    def formatted_date(self) -> str:
        try:
            dt = datetime(*self.date_time)
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return "-:-"

    @property
    def formatted_size(self) -> str:
        return format_bytes(self.file_size)

    @property
    def formatted_compressed_size(self) -> str:
        return format_bytes(self.compress_size)


@dataclass
class ArchiveSummary:
    """Zusammenfassung eines ZIP- oder TAR-Archivs."""
    archive_path: str
    total_files: int
    total_folders: int
    uncompressed_size: int
    compressed_size: int
    overall_ratio: float
    is_encrypted: bool = False
    comment: str = ""

    @property
    def formatted_uncompressed_size(self) -> str:
        return format_bytes(self.uncompressed_size)

    @property
    def formatted_compressed_size(self) -> str:
        return format_bytes(self.compressed_size)


def format_bytes(num_bytes: int) -> str:
    """Formatiert Byte-Zahlen lesbar in B, KB, MB, GB."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def sanitize_archive_member_path(member_name: str, target_dir: str | Path) -> Path:
    """
    Sicherheitsprüfung gegen Zip-Slip- und Tar-Slip-Schwachstellen (Directory Traversal).
    Bereinigt den Pfad und stellt sicher, dass das Ziel innerhalb von target_dir liegt.
    """
    target_path = Path(target_dir).resolve()

    # Vorverarbeitung: Windows-Laufwerksbuchstaben und absolute Pfade neutralisieren
    normalized = member_name.replace("\\", "/").strip()
    # Entferne führende Slashes oder Laufwerksbezeichner wie "C:"
    while normalized.startswith("/"):
        normalized = normalized[1:]
    if len(normalized) > 1 and normalized[1] == ":":
        normalized = normalized[2:]
        while normalized.startswith("/"):
            normalized = normalized[1:]

    # Pfadteile auf relative Segmente auflösen
    dest_path = (target_path / normalized).resolve()

    try:
        dest_path.relative_to(target_path)
    except ValueError:
        raise ZipSlipSecurityError(
            f"Sicherheitswarnung: Archiv-Eintrag '{member_name}' verlässt das Zielverzeichnis!"
        )

    return dest_path


SUPPORTED_ARCHIVE_EXTENSIONS = (
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz"
)


def is_archive(path: str | Path) -> bool:
    """Prüft, ob der Pfad ein unterstütztes Archiv (ZIP oder TAR/komprimiert) ist."""
    path_obj = Path(path)
    if not path_obj.is_file():
        return False
    name_lower = path_obj.name.lower()
    if name_lower.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst", ".tgz", ".tbz2", ".txz")):
        return True
    if path_obj.suffix.lower() in SUPPORTED_ARCHIVE_EXTENSIONS:
        return True
    return zipfile.is_zipfile(path_obj) or tarfile.is_tarfile(path_obj)


def inspect_zip(zip_path: str | Path) -> Tuple[ArchiveSummary, List[ArchiveEntry]]:
    """
    Liest ein ZIP-Archiv und gibt die Zusammenfassung sowie alle Einträge zurück.
    """
    path_obj = Path(zip_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"Archiv nicht gefunden: {zip_path}")

    if not zipfile.is_zipfile(path_obj):
        raise zipfile.BadZipFile(f"Datei ist kein gültiges ZIP-Archiv: {zip_path}")

    entries: List[ArchiveEntry] = []
    total_files = 0
    total_folders = 0
    total_uncompressed = 0
    total_compressed = 0
    is_encrypted = False

    with zipfile.ZipFile(path_obj, "r") as zf:
        archive_comment = zf.comment.decode("utf-8", errors="replace") if zf.comment else ""
        for info in zf.infolist():
            # Flag bit 0x1 indicates encryption
            if info.flag_bits & 0x1:
                is_encrypted = True

            is_dir = info.is_dir()
            if is_dir:
                total_folders += 1
            else:
                total_files += 1

            uncomp = info.file_size
            comp = info.compress_size
            total_uncompressed += uncomp
            total_compressed += comp

            ratio = 0.0
            if uncomp > 0:
                ratio = max(0.0, min(100.0, (1.0 - (comp / uncomp)) * 100.0))

            comment = info.comment.decode("utf-8", errors="replace") if info.comment else ""

            entry = ArchiveEntry(
                filename=info.filename,
                file_size=uncomp,
                compress_size=comp,
                is_dir=is_dir,
                date_time=info.date_time,
                crc=info.CRC,
                compression_ratio=ratio,
                comment=comment,
            )
            entries.append(entry)

    overall_ratio = 0.0
    if total_uncompressed > 0:
        overall_ratio = max(0.0, min(100.0, (1.0 - (total_compressed / total_uncompressed)) * 100.0))

    summary = ArchiveSummary(
        archive_path=str(path_obj.resolve()),
        total_files=total_files,
        total_folders=total_folders,
        uncompressed_size=total_uncompressed,
        compressed_size=total_compressed,
        overall_ratio=overall_ratio,
        is_encrypted=is_encrypted,
        comment=archive_comment,
    )

    return summary, entries


def inspect_tar(tar_path: str | Path) -> Tuple[ArchiveSummary, List[ArchiveEntry]]:
    """
    Liest ein TAR-Archiv (inkl. .tar.gz, .tar.bz2, .tar.xz) und gibt Zusammenfassung sowie Einträge zurück.
    """
    path_obj = Path(tar_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"Archiv nicht gefunden: {tar_path}")

    entries: List[ArchiveEntry] = []
    total_files = 0
    total_folders = 0
    total_uncompressed = 0
    compressed_size = path_obj.stat().st_size

    try:
        with tarfile.open(path_obj, "r:*") as tf:
            for member in tf.getmembers():
                is_dir = member.isdir()
                if is_dir:
                    total_folders += 1
                elif member.isreg():
                    total_files += 1

                size = member.size
                total_uncompressed += size

                try:
                    dt_tuple = time.localtime(member.mtime)[:6]
                except Exception:
                    dt_tuple = (1970, 1, 1, 0, 0, 0)

                entry = ArchiveEntry(
                    filename=member.name,
                    file_size=size,
                    compress_size=size,
                    is_dir=is_dir,
                    date_time=dt_tuple,
                    crc=0,
                    compression_ratio=0.0,
                    comment="",
                )
                entries.append(entry)
    except Exception as exc:
        raise ValueError(f"Datei ist kein gültiges TAR-Archiv: {tar_path} ({exc})")

    overall_ratio = 0.0
    if total_uncompressed > 0:
        overall_ratio = max(0.0, min(100.0, (1.0 - (compressed_size / total_uncompressed)) * 100.0))

    summary = ArchiveSummary(
        archive_path=str(path_obj.resolve()),
        total_files=total_files,
        total_folders=total_folders,
        uncompressed_size=total_uncompressed,
        compressed_size=compressed_size,
        overall_ratio=overall_ratio,
        is_encrypted=False,
        comment="",
    )

    return summary, entries


def inspect_archive(archive_path: str | Path) -> Tuple[ArchiveSummary, List[ArchiveEntry]]:
    """
    Liest ein beliebiges unterstütztes Archiv (ZIP oder TAR/komprimiert)
    und gibt die Zusammenfassung sowie alle Einträge zurück.
    """
    path_obj = Path(archive_path)
    if not path_obj.is_file():
        raise FileNotFoundError(f"Archiv nicht gefunden: {archive_path}")

    if zipfile.is_zipfile(path_obj):
        return inspect_zip(path_obj)
    elif tarfile.is_tarfile(path_obj):
        return inspect_tar(path_obj)
    else:
        name_lower = path_obj.name.lower()
        if name_lower.endswith(".zip"):
            return inspect_zip(path_obj)
        elif name_lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
            return inspect_tar(path_obj)
        raise ValueError(f"Nicht unterstütztes oder beschädigtes Archivformat: {archive_path}")


def check_zip_integrity(zip_path: str | Path) -> Tuple[bool, Optional[str]]:
    """
    Prüft die Integrität eines ZIP-Archivs mittels CRC-Check.
    Gibt (True, None) bei Erfolg zurück oder (False, Fehlermeldung).
    """
    path_obj = Path(zip_path)
    if not path_obj.is_file():
        return False, f"Datei nicht gefunden: {zip_path}"

    if not zipfile.is_zipfile(path_obj):
        return False, "Kein gültiges ZIP-Archiv"

    try:
        with zipfile.ZipFile(path_obj, "r") as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                return False, f"Beschädigte Datei im Archiv gefunden: {bad_file}"
        return True, None
    except Exception as exc:
        return False, f"Fehler bei Integritätsprüfung: {exc}"


def check_tar_integrity(tar_path: str | Path) -> Tuple[bool, Optional[str]]:
    """
    Prüft die Integrität eines TAR-Archivs durch sequentielles Lesen aller Member-Streams.
    Gibt (True, None) bei Erfolg zurück oder (False, Fehlermeldung).
    """
    path_obj = Path(tar_path)
    if not path_obj.is_file():
        return False, f"Datei nicht gefunden: {tar_path}"

    try:
        with tarfile.open(path_obj, "r:*") as tf:
            for member in tf.getmembers():
                if member.isreg():
                    f = tf.extractfile(member)
                    if f is not None:
                        while True:
                            chunk = f.read(128 * 1024)
                            if not chunk:
                                break
        return True, None
    except Exception as exc:
        return False, f"Fehler bei TAR-Integritätsprüfung: {exc}"


def check_archive_integrity(archive_path: str | Path) -> Tuple[bool, Optional[str]]:
    """Prüft die Integrität eines ZIP- oder TAR-Archivs."""
    path_obj = Path(archive_path)
    if zipfile.is_zipfile(path_obj):
        return check_zip_integrity(path_obj)
    elif tarfile.is_tarfile(path_obj):
        return check_tar_integrity(path_obj)
    else:
        name_lower = path_obj.name.lower()
        if name_lower.endswith(".zip"):
            return check_zip_integrity(path_obj)
        return check_tar_integrity(path_obj)


# Alias zur Abwärtskompatibilität
verify_zip_integrity = check_zip_integrity
verify_archive_integrity = check_archive_integrity


def create_zip_archive(
    sources: List[str | Path],
    dest_zip: str | Path,
    compression: int = zipfile.ZIP_DEFLATED,
    compresslevel: int = 6,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """
    Komprimiert mehrere Dateien und Verzeichnisse atomar in eine ZIP-Datei.
    Gibt (anzahl_dateien, bytes_entpackt) zurück.
    """
    if not sources:
        raise ValueError("Keine Quelldateien zum Komprimieren übergeben.")

    dest_path = Path(dest_zip).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    items_to_add: List[Tuple[Path, str]] = []

    for src in sources:
        src_path = Path(src).resolve()
        if not src_path.exists():
            continue

        if src_path.is_file():
            items_to_add.append((src_path, src_path.name))
        elif src_path.is_dir():
            root_parent = src_path.parent
            for dirpath, dirnames, filenames in os.walk(src_path):
                curr_dir = Path(dirpath)
                if not dirnames and not filenames:
                    rel_dir = curr_dir.relative_to(root_parent).as_posix() + "/"
                    items_to_add.append((curr_dir, rel_dir))
                for fname in filenames:
                    fpath = curr_dir / fname
                    rel_f = fpath.relative_to(root_parent).as_posix()
                    items_to_add.append((fpath, rel_f))

    total_items = len(items_to_add)
    if total_items == 0:
        raise ValueError("Keine gültigen Dateien in den ausgewählten Pfaden gefunden.")

    temp_zip = dest_path.with_name(f"{dest_path.name}.tmp_{int(time.time()*1000)}")
    added_files = 0
    total_bytes = 0

    try:
        kwargs = {"compression": compression}
        if compression in (zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2):
            kwargs["compresslevel"] = compresslevel

        with zipfile.ZipFile(temp_zip, "w", **kwargs) as zf:
            for idx, (fpath, arcname) in enumerate(items_to_add, start=1):
                if is_cancelled and is_cancelled():
                    zf.close()
                    if temp_zip.exists():
                        temp_zip.unlink(missing_ok=True)
                    return 0, 0

                if progress_callback:
                    progress_callback(idx, total_items, arcname)

                if fpath.is_file():
                    zf.write(fpath, arcname)
                    added_files += 1
                    try:
                        total_bytes += fpath.stat().st_size
                    except OSError:
                        pass
                elif fpath.is_dir():
                    zinfo = zipfile.ZipInfo(arcname if arcname.endswith("/") else arcname + "/")
                    zinfo.external_attr = 0o777 << 16 | stat.S_IFDIR
                    zf.writestr(zinfo, "")

        # Atomare Veröffentlichung via os.replace
        if temp_zip.exists():
            os.replace(temp_zip, dest_path)

        return added_files, total_bytes

    except Exception:
        if temp_zip.exists():
            temp_zip.unlink(missing_ok=True)
        raise


def create_tar_archive(
    sources: List[str | Path],
    dest_tar: str | Path,
    mode: str = "w:gz",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """
    Komprimiert mehrere Dateien und Verzeichnisse atomar in eine TAR-Datei.
    mode: "w:gz", "w:bz2", "w:xz" oder "w" (uncompressed).
    Gibt (anzahl_dateien, bytes_entpackt) zurück.
    """
    if not sources:
        raise ValueError("Keine Quelldateien zum Komprimieren übergeben.")

    dest_path = Path(dest_tar).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    items_to_add: List[Tuple[Path, str]] = []
    for src in sources:
        src_path = Path(src).resolve()
        if not src_path.exists():
            continue

        if src_path.is_file():
            items_to_add.append((src_path, src_path.name))
        elif src_path.is_dir():
            root_parent = src_path.parent
            for dirpath, dirnames, filenames in os.walk(src_path):
                curr_dir = Path(dirpath)
                rel_dir = curr_dir.relative_to(root_parent).as_posix()
                if rel_dir and rel_dir != ".":
                    items_to_add.append((curr_dir, rel_dir))
                for fname in filenames:
                    fpath = curr_dir / fname
                    rel_f = fpath.relative_to(root_parent).as_posix()
                    items_to_add.append((fpath, rel_f))

    total_items = len(items_to_add)
    if total_items == 0:
        raise ValueError("Keine gültigen Dateien in den ausgewählten Pfaden gefunden.")

    temp_tar = dest_path.with_name(f"{dest_path.name}.tmp_{int(time.time()*1000)}")
    added_files = 0
    total_bytes = 0

    try:
        with tarfile.open(temp_tar, mode) as tf:
            for idx, (fpath, arcname) in enumerate(items_to_add, start=1):
                if is_cancelled and is_cancelled():
                    tf.close()
                    if temp_tar.exists():
                        temp_tar.unlink(missing_ok=True)
                    return 0, 0

                if progress_callback:
                    progress_callback(idx, total_items, arcname)

                tf.add(fpath, arcname=arcname, recursive=False)
                if fpath.is_file():
                    added_files += 1
                    try:
                        total_bytes += fpath.stat().st_size
                    except OSError:
                        pass

        if temp_tar.exists():
            os.replace(temp_tar, dest_path)

        return added_files, total_bytes
    except Exception:
        if temp_tar.exists():
            temp_tar.unlink(missing_ok=True)
        raise


def create_archive(
    sources: List[str | Path],
    dest_path: str | Path,
    compression: int = zipfile.ZIP_DEFLATED,
    compresslevel: int = 6,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """Erstellt atomar ein Archiv (ZIP oder TAR je nach Zieldateiendung)."""
    dest = Path(dest_path)
    name_lower = dest.name.lower()
    if name_lower.endswith((".tar.gz", ".tgz")):
        return create_tar_archive(sources, dest, mode="w:gz", progress_callback=progress_callback, is_cancelled=is_cancelled)
    elif name_lower.endswith((".tar.bz2", ".tbz2")):
        return create_tar_archive(sources, dest, mode="w:bz2", progress_callback=progress_callback, is_cancelled=is_cancelled)
    elif name_lower.endswith((".tar.xz", ".txz")):
        return create_tar_archive(sources, dest, mode="w:xz", progress_callback=progress_callback, is_cancelled=is_cancelled)
    elif name_lower.endswith(".tar"):
        return create_tar_archive(sources, dest, mode="w", progress_callback=progress_callback, is_cancelled=is_cancelled)
    else:
        return create_zip_archive(sources, dest, compression=compression, compresslevel=compresslevel, progress_callback=progress_callback, is_cancelled=is_cancelled)


def extract_zip_archive(
    zip_path: str | Path,
    target_dir: str | Path,
    members: Optional[List[str]] = None,
    overwrite: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """
    Extrahiert Dateien sicher (Zip-Slip-geschützt) aus einem ZIP-Archiv.
    Gibt (anzahl_entpackt, bytes_entpackt) zurück.
    """
    path_obj = Path(zip_path).resolve()
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if not path_obj.is_file():
        raise FileNotFoundError(f"Archivdatei nicht gefunden: {zip_path}")

    with zipfile.ZipFile(path_obj, "r") as zf:
        infolist = zf.infolist()
        if members is not None:
            member_set = set(members)
            infolist = [info for info in infolist if info.filename in member_set]

        total_members = len(infolist)
        extracted_files = 0
        extracted_bytes = 0

        for idx, info in enumerate(infolist, start=1):
            if is_cancelled and is_cancelled():
                return extracted_files, extracted_bytes

            if progress_callback:
                progress_callback(idx, total_members, info.filename)

            dest_path = sanitize_archive_member_path(info.filename, target_path)

            if info.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if dest_path.exists() and not overwrite:
                continue

            # Atomar via temporäre Datei schreiben
            temp_dest = dest_path.with_name(f"{dest_path.name}.tmp_{int(time.time()*1000)}")
            try:
                with zf.open(info, "r") as src_f, open(temp_dest, "wb") as dst_f:
                    while True:
                        if is_cancelled and is_cancelled():
                            if temp_dest.exists():
                                temp_dest.unlink(missing_ok=True)
                            return extracted_files, extracted_bytes
                        chunk = src_f.read(64 * 1024)
                        if not chunk:
                            break
                        dst_f.write(chunk)
                os.replace(temp_dest, dest_path)
            except Exception:
                if temp_dest.exists():
                    temp_dest.unlink(missing_ok=True)
                raise

            # mtime wiederherstellen
            try:
                dt = datetime(*info.date_time)
                mtime = dt.timestamp()
                os.utime(dest_path, (mtime, mtime))
            except Exception:
                pass

            extracted_files += 1
            extracted_bytes += info.file_size

    return extracted_files, extracted_bytes


def extract_tar_archive(
    tar_path: str | Path,
    target_dir: str | Path,
    members: Optional[List[str]] = None,
    overwrite: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """
    Extrahiert Dateien sicher (Tar-Slip-geschützt) aus einem TAR-Archiv (.tar, .tar.gz, etc.).
    Gibt (anzahl_entpackt, bytes_entpackt) zurück.
    """
    path_obj = Path(tar_path).resolve()
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if not path_obj.is_file():
        raise FileNotFoundError(f"Archivdatei nicht gefunden: {tar_path}")

    with tarfile.open(path_obj, "r:*") as tf:
        all_members = tf.getmembers()
        if members is not None:
            member_set = set(members)
            all_members = [m for m in all_members if m.name in member_set]

        total_members = len(all_members)
        extracted_files = 0
        extracted_bytes = 0

        for idx, member in enumerate(all_members, start=1):
            if is_cancelled and is_cancelled():
                return extracted_files, extracted_bytes

            if progress_callback:
                progress_callback(idx, total_members, member.name)

            dest_path = sanitize_archive_member_path(member.name, target_path)

            if member.isdir():
                dest_path.mkdir(parents=True, exist_ok=True)
                continue

            # Nur reguläre Dateien extrahieren (Sicherheitsgrenze)
            if not member.isreg():
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path.exists() and not overwrite:
                continue

            temp_dest = dest_path.with_name(f"{dest_path.name}.tmp_{int(time.time()*1000)}")
            f_in = tf.extractfile(member)
            if f_in is None:
                continue

            try:
                with f_in, open(temp_dest, "wb") as dst_f:
                    while True:
                        if is_cancelled and is_cancelled():
                            if temp_dest.exists():
                                temp_dest.unlink(missing_ok=True)
                            return extracted_files, extracted_bytes
                        chunk = f_in.read(64 * 1024)
                        if not chunk:
                            break
                        dst_f.write(chunk)
                os.replace(temp_dest, dest_path)
            except Exception:
                if temp_dest.exists():
                    temp_dest.unlink(missing_ok=True)
                raise

            try:
                os.utime(dest_path, (member.mtime, member.mtime))
            except Exception:
                pass

            extracted_files += 1
            extracted_bytes += member.size

    return extracted_files, extracted_bytes


def extract_archive(
    archive_path: str | Path,
    target_dir: str | Path,
    members: Optional[List[str]] = None,
    overwrite: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """Extrahiert ein beliebiges unterstütztes Archiv (ZIP oder TAR)."""
    p = Path(archive_path)
    if zipfile.is_zipfile(p):
        return extract_zip_archive(p, target_dir, members, overwrite, progress_callback, is_cancelled)
    elif tarfile.is_tarfile(p):
        return extract_tar_archive(p, target_dir, members, overwrite, progress_callback, is_cancelled)
    else:
        name_lower = p.name.lower()
        if name_lower.endswith(".zip"):
            return extract_zip_archive(p, target_dir, members, overwrite, progress_callback, is_cancelled)
        return extract_tar_archive(p, target_dir, members, overwrite, progress_callback, is_cancelled)


class ArchiveCompressWorker(QThread):
    """Hintergrund-Thread für Archiv-Komprimierung (ZIP & TAR)."""
    progress = Signal(int, int, str)       # current, total, filename
    finished = Signal(bool, str, int, int) # success, dest_path, count, bytes
    error = Signal(str)

    def __init__(
        self,
        sources: List[str | Path],
        dest_zip: str | Path,
        compression: int = zipfile.ZIP_DEFLATED,
        compresslevel: int = 6,
        parent=None,
    ):
        super().__init__(parent)
        self.sources = sources
        self.dest_zip = dest_zip
        self.compression = compression
        self.compresslevel = compresslevel
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            count, num_bytes = create_archive(
                self.sources,
                self.dest_zip,
                compression=self.compression,
                compresslevel=self.compresslevel,
                progress_callback=lambda cur, tot, name: self.progress.emit(cur, tot, name),
                is_cancelled=lambda: self._is_cancelled,
            )
            if self._is_cancelled:
                self.finished.emit(False, str(self.dest_zip), 0, 0)
            else:
                self.finished.emit(True, str(self.dest_zip), count, num_bytes)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit(False, str(self.dest_zip), 0, 0)


class ArchiveExtractWorker(QThread):
    """Hintergrund-Thread für Archiv-Extraktion (ZIP & TAR)."""
    progress = Signal(int, int, str)       # current, total, filename
    finished = Signal(bool, str, int, int) # success, target_dir, count, bytes
    error = Signal(str)

    def __init__(
        self,
        zip_path: str | Path,
        target_dir: str | Path,
        members: Optional[List[str]] = None,
        overwrite: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.zip_path = zip_path
        self.target_dir = target_dir
        self.members = members
        self.overwrite = overwrite
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            count, num_bytes = extract_archive(
                self.zip_path,
                self.target_dir,
                members=self.members,
                overwrite=self.overwrite,
                progress_callback=lambda cur, tot, name: self.progress.emit(cur, tot, name),
                is_cancelled=lambda: self._is_cancelled,
            )
            if self._is_cancelled:
                self.finished.emit(False, str(self.target_dir), 0, 0)
            else:
                self.finished.emit(True, str(self.target_dir), count, num_bytes)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit(False, str(self.target_dir), 0, 0)


class ArchiveTestWorker(QThread):
    """Hintergrund-Thread zur Prüfung der Archiv-Integrität (ZIP & TAR)."""
    finished = Signal(bool, str) # is_valid, message

    def __init__(self, zip_path: str | Path, parent=None):
        super().__init__(parent)
        self.zip_path = zip_path

    def run(self):
        is_valid, msg = check_archive_integrity(self.zip_path)
        self.finished.emit(is_valid, msg or "")
