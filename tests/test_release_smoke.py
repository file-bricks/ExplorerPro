from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_EXE = PROJECT_ROOT / "releases" / "v1.0.0" / "ExplorerPro" / "ExplorerPro.exe"


@pytest.mark.skipif(sys.platform != "win32", reason="Release-EXE-Smoke ist Windows-spezifisch")
def test_release_exe_starts_without_native_loader_error() -> None:
    if not RELEASE_EXE.exists():
        pytest.skip(f"Release-EXE fehlt lokal: {RELEASE_EXE}")

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    timeout = float(env.get("EXPLORERPRO_RELEASE_SMOKE_SECONDS", "6"))

    with tempfile.TemporaryDirectory(prefix="explorerpro-release-smoke-") as tmp:
        stdout_path = Path(tmp) / "stdout.txt"
        stderr_path = Path(tmp) / "stderr.txt"

        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            proc = subprocess.Popen(
                [str(RELEASE_EXE)],
                cwd=str(RELEASE_EXE.parent),
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )

            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
                return

        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

        assert proc.returncode == 0, (
            "ExplorerPro-Release-EXE ist vor dem Smoke-Timeout beendet. "
            f"returncode={proc.returncode} hex=0x{proc.returncode & 0xFFFFFFFF:08X}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
