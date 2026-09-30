"""Read capacity without scanning files or changing the filesystem."""

from dataclasses import dataclass
import os
import shutil


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
