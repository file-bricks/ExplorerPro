#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crash_log — lokale Fehlerprotokollierung ohne Netzwerkzugriff.

* ``faulthandler`` schreibt bei nativen Abstürzen (Access Violation,
  Segfault) die Python-Stacks aller Threads in ``crash.log``.
* Unbehandelte Python-Ausnahmen (auch aus Qt-Slots, die PySide über
  ``sys.excepthook`` meldet) und aus Threads werden mit Zeitstempel
  protokolliert, statt in der fensterlosen EXE spurlos zu verschwinden.

Die Datei bleibt ausschließlich lokal im Benutzerprofil.
"""
from __future__ import annotations

import datetime as _dt
import faulthandler
import sys
import threading
import traceback
from pathlib import Path

MAX_LOG_BYTES = 1024 * 1024

_log_file = None


def default_log_dir() -> Path:
    return Path.home() / ".explorerpro" / "logs"


def _write(text: str) -> None:
    if _log_file is None:
        return
    try:
        _log_file.write(text)
        _log_file.flush()
    except (OSError, ValueError):
        pass


def _format_exception(exc_type, exc, tb, origin: str) -> str:
    stamp = _dt.datetime.now().isoformat(timespec="seconds")
    body = "".join(traceback.format_exception(exc_type, exc, tb))
    return f"\n=== {stamp} | {origin} ===\n{body}"


def install_crash_logging(log_dir: Path | None = None) -> Path | None:
    """Aktiviert faulthandler und Exception-Hooks; liefert den Logpfad."""
    global _log_file
    if _log_file is not None:
        return Path(_log_file.name)

    log_dir = log_dir or default_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "crash.log"
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            path.replace(log_dir / "crash.old.log")
        _log_file = open(path, "a", encoding="utf-8")
    except OSError:
        return None

    try:
        faulthandler.enable(file=_log_file, all_threads=True)
    except (OSError, ValueError, RuntimeError):
        pass

    previous_hook = sys.excepthook

    def excepthook(exc_type, exc, tb):
        _write(_format_exception(exc_type, exc, tb, "Unbehandelte Ausnahme"))
        if previous_hook is not None and sys.stderr is not None:
            try:
                previous_hook(exc_type, exc, tb)
            except Exception:
                pass

    sys.excepthook = excepthook

    previous_thread_hook = threading.excepthook

    def thread_hook(args):
        name = getattr(args.thread, "name", "?")
        _write(_format_exception(args.exc_type, args.exc_value, args.exc_traceback, f"Thread {name}"))
        if sys.stderr is not None:
            try:
                previous_thread_hook(args)
            except Exception:
                pass

    threading.excepthook = thread_hook
    return path


def uninstall_crash_logging() -> None:
    """Schließt das Log (für Tests und sauberes Beenden)."""
    global _log_file
    if _log_file is None:
        return
    try:
        faulthandler.disable()
    except Exception:
        pass
    sys.excepthook = sys.__excepthook__
    threading.excepthook = threading.__excepthook__
    try:
        _log_file.close()
    except OSError:
        pass
    _log_file = None
