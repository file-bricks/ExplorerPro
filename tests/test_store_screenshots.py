from __future__ import annotations

import tempfile
from pathlib import Path

from generate_store_screenshots import SCREENSHOT_FILES, generate_store_screenshots


def test_generate_store_screenshots_creates_expected_pngs() -> None:
    with tempfile.TemporaryDirectory(prefix="explorerpro-store-shots-test-") as tmp_dir:
        targets = generate_store_screenshots(Path(tmp_dir))

        expected = {Path(tmp_dir) / name for name in SCREENSHOT_FILES.values()}
        assert set(targets) == expected

        for target in targets:
            data = target.read_bytes()
            assert data.startswith(b"\x89PNG\r\n\x1a\n")
            assert len(data) > 1024
