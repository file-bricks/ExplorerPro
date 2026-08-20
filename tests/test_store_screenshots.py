from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from generate_store_screenshots import (
    SCREENSHOT_FILES,
    _assert_font_rendering,
    generate_store_screenshots,
)


def test_generate_store_screenshots_creates_expected_pngs() -> None:
    app = QtWidgets.QApplication.instance()
    if app is not None and QtWidgets.QApplication.platformName() == "offscreen":
        pytest.skip("Der PNG-Smoke benötigt eine native Qt-Plattform.")
    if sys.platform != "win32" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        pytest.skip("Der PNG-Smoke benötigt auf CI einen Display-Server.")

    with tempfile.TemporaryDirectory(prefix="explorerpro-store-shots-test-") as tmp_dir:
        targets = generate_store_screenshots(Path(tmp_dir))

        expected = {Path(tmp_dir) / name for name in SCREENSHOT_FILES.values()}
        assert set(targets) == expected

        for target in targets:
            data = target.read_bytes()
            assert data.startswith(b"\x89PNG\r\n\x1a\n")
            assert len(data) > 1024


def test_offscreen_platform_is_rejected_as_tofu_risk() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if QtWidgets.QApplication.platformName() != "offscreen":
        pytest.skip("Der Tofu-Guard betrifft ausschließlich die offscreen-Plattform.")

    with pytest.raises(RuntimeError, match="offscreen"):
        _assert_font_rendering(app)
