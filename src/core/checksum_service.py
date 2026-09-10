#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChecksumService - Schnelle, ressourcenschonende Prüfsummen-Berechnung
Unterstützt MD5, SHA-1, SHA-256, SHA-512 in einem einzigen Datei-Pass
inklusive QThread-Background-Worker und Hash-Verifikation.
"""

import hashlib
import os
from typing import Callable, Dict, Optional, Tuple
from PySide6.QtCore import QThread, Signal


SUPPORTED_ALGORITHMS = ("md5", "sha1", "sha256", "sha512")
DEFAULT_ALGORITHMS = ("md5", "sha1", "sha256", "sha512")
CHUNK_SIZE = 64 * 1024  # 64 KB Chunks


def compute_file_hashes(
    filepath: str,
    algorithms: Tuple[str, ...] = DEFAULT_ALGORITHMS,
    chunk_size: int = CHUNK_SIZE,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> Dict[str, str]:
    """
    Berechnet Prüfsummen für eine Datei in einem einzigen Lesedurchlauf.
    Gibt ein Wörterbuch {algo: hexdigest} zurück.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

    total_size = os.path.getsize(filepath)
    hashers = {}
    for algo in algorithms:
        algo_lower = algo.lower()
        if algo_lower == "md5":
            hashers["md5"] = hashlib.md5()
        elif algo_lower in ("sha1", "sha-1"):
            hashers["sha1"] = hashlib.sha1()
        elif algo_lower in ("sha256", "sha-256"):
            hashers["sha256"] = hashlib.sha256()
        elif algo_lower in ("sha512", "sha-512"):
            hashers["sha512"] = hashlib.sha512()
        else:
            raise ValueError(f"Nicht unterstützter Hash-Algorithmus: {algo}")

    bytes_read = 0
    with open(filepath, "rb") as f:
        while True:
            if is_cancelled and is_cancelled():
                return {}
            chunk = f.read(chunk_size)
            if not chunk:
                break
            for hasher in hashers.values():
                hasher.update(chunk)
            bytes_read += len(chunk)
            if progress_callback:
                progress_callback(bytes_read, total_size)

    return {algo: hasher.hexdigest() for algo, hasher in hashers.items()}


def verify_hash(calculated_hashes: Dict[str, str], expected_hash: str) -> Optional[Tuple[str, str]]:
    """
    Prüft, ob der erwartete Hash mit einer der berechneten Prüfsummen übereinstimmt.
    Normalisiert Whitespace und Groß-/Kleinschreibung.
    Gibt (algorithm_name, calculated_hash) zurück oder None bei keiner Übereinstimmung.
    """
    if not expected_hash:
        return None

    cleaned = expected_hash.strip().lower()
    if ":" in cleaned:
        cleaned = cleaned.split(":", 1)[1].strip()

    for algo, val in calculated_hashes.items():
        if val.lower() == cleaned:
            return (algo, val)

    return None


class ChecksumWorker(QThread):
    """Hintergrund-Thread zur blockierungsfreien Prüfsummenberechnung großer Dateien."""

    progress = Signal(int, int)   # bytes_read, total_bytes
    finished = Signal(dict)        # {algo: hexdigest}
    error = Signal(str)

    def __init__(
        self,
        filepath: str,
        algorithms: Tuple[str, ...] = ("md5", "sha1", "sha256", "sha512"),
        parent=None,
    ):
        super().__init__(parent)
        self.filepath = filepath
        self.algorithms = algorithms
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        try:
            results = compute_file_hashes(
                filepath=self.filepath,
                algorithms=self.algorithms,
                progress_callback=self._on_progress,
                is_cancelled=self.is_cancelled,
            )
            if not self._cancelled:
                self.finished.emit(results)
        except Exception as exc:
            if not self._cancelled:
                self.error.emit(str(exc))

    def _on_progress(self, bytes_read: int, total_bytes: int):
        if not self._cancelled:
            self.progress.emit(bytes_read, total_bytes)
