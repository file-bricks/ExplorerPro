"""Read capacity without scanning files or changing the filesystem."""

from dataclasses import dataclass
import os
import shutil
import json
from pathlib import Path
import subprocess
import sys
import threading
import tempfile

QUERY_TIMEOUT_SECONDS = 10
_query_lock = threading.Lock()
_query_processes = set()
_queries_stopped = False


def start_drive_queries():
    global _queries_stopped
    with _query_lock:
        _queries_stopped = False


def stop_drive_queries():
    """Stop only our capacity helpers, including reads stuck inside the OS."""
    global _queries_stopped
    with _query_lock:
        _queries_stopped = True
        for process in tuple(_query_processes):
            if process.poll() is None:
                process.kill()


def _query_command(path, result_path):
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--drive-capacity-query', path, result_path]
    return [sys.executable, str(Path(__file__).resolve()), path, result_path]


def read_drive_usage_bounded(path):
    """Isolate disk_usage so stalled devices cannot retain pool slots forever."""
    with tempfile.TemporaryDirectory(prefix='explorerpro-capacity-') as directory:
        return _read_drive_usage_process(path, Path(directory) / 'result.json')


def _read_drive_usage_process(path, result_path):
    with _query_lock:
        if _queries_stopped:
            raise OSError('Capacity queries stopped')
        process = subprocess.Popen(
            _query_command(path, str(result_path)),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        _query_processes.add(process)
    try:
        try:
            process.wait(timeout=QUERY_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise OSError('Capacity query timed out') from None
        if process.returncode:
            raise OSError('Capacity query unavailable')
        try:
            values = json.loads(result_path.read_text(encoding='utf-8'))
            return DriveUsage(**values)
        except (OSError, ValueError, TypeError):
            raise OSError('Invalid capacity query response') from None
    finally:
        with _query_lock:
            _query_processes.discard(process)


def capacity_query_main(path, result_path):
    """Read-only measurement; write its result to the parent's private temp file."""
    try:
        usage = read_drive_usage(path)
    except (OSError, ValueError):
        return 1
    # Windowed frozen executables may have no stdout, even with redirected pipes.
    with open(result_path, 'x', encoding='utf-8') as result:
        json.dump({'total': usage.total, 'used': usage.used, 'free': usage.free}, result)
    return 0


@dataclass(frozen=True)
class DriveUsage:
    total: int
    used: int
    free: int

    def __post_init__(self):
        if self.total <= 0 or not 0 <= self.used <= self.total or not 0 <= self.free <= self.total:
            raise ValueError("Invalid drive capacity")

    @property
    def used_percent(self) -> float:
        return self.used / self.total * 100


def read_drive_usage(path: str) -> DriveUsage:
    if os.name == "nt":
        # Empty removable drives must return an error rather than opening an
        # operating-system critical-error dialog in this background thread.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        set_mode = kernel.SetThreadErrorMode
        set_mode.argtypes = (wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
        set_mode.restype = wintypes.BOOL
        get_mode = kernel.GetThreadErrorMode
        get_mode.argtypes = ()
        get_mode.restype = wintypes.DWORD
        previous = wintypes.DWORD()
        if not set_mode(get_mode() | 0x0001, ctypes.byref(previous)):  # SEM_FAILCRITICALERRORS
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            usage = shutil.disk_usage(path)
        finally:
            set_mode(previous.value, None)
    else:
        usage = shutil.disk_usage(path)
    return DriveUsage(usage.total, usage.used, usage.free)


def format_capacity(size: int) -> str:
    """Use explicit binary units, retaining useful precision for small drives."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024


if __name__ == '__main__':
    sys.exit(capacity_query_main(*sys.argv[1:]) if len(sys.argv) == 3 else 2)
