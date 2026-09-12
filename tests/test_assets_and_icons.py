# -*- coding: utf-8 -*-
"""
test_assets_and_icons.py - Automated contract tests for ExplorerPro icon and asset suite.

Validates:
- 1024x1024 RGBA master icons (root, assets, mobile)
- 7-layer Windows ICO files (16, 24, 32, 48, 64, 128, 256)
- Mobile / PWA assets, maskable icons and valid manifest.json
- Microsoft Store tiles and canonical icon_* assets
- Defensive load_app_icon() loader resolution
"""

import json
import struct
import sys
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_7_LAYERS = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
EXPECTED_FAVICON_LAYERS = [(16, 16), (24, 24), (32, 32), (48, 48)]


def read_ico_layers(ico_path: Path) -> list[tuple[int, int]]:
    """Reads all frame dimensions from an ICO header."""
    with open(ico_path, "rb") as f:
        _reserved, ico_type, count = struct.unpack("<HHH", f.read(6))
        assert ico_type == 1, f"Not an ICO file: {ico_path}"
        sizes = []
        for _ in range(count):
            w, h, _, _, _, _, _, _ = struct.unpack("<BBBBHHII", f.read(16))
            sizes.append((w or 256, h or 256))
    return sorted(sizes)


def test_master_icons_exist_and_valid():
    """Verify root master PNGs and 7-layer ICOs."""
    root_pngs = ["DesktopIcon.png", "icon.png"]
    for name in root_pngs:
        path = REPO_ROOT / name
        assert path.exists(), f"Missing root master PNG: {name}"
        with Image.open(path) as img:
            assert img.size == (1024, 1024), f"{name} size is not 1024x1024: {img.size}"
            assert img.mode == "RGBA", f"{name} mode is not RGBA: {img.mode}"

    root_icos = ["ExplorerPro.ico", "DesktopIcon.ico", "icon.ico"]
    for name in root_icos:
        path = REPO_ROOT / name
        assert path.exists(), f"Missing root ICO: {name}"
        layers = read_ico_layers(path)
        assert layers == EXPECTED_7_LAYERS, f"{name} has invalid layers: {layers}"


def test_assets_folder_parity():
    """Verify assets/ folder contains 7-layer ICOs, 1024x1024 PNGs and favicons."""
    assets_dir = REPO_ROOT / "assets"
    assert assets_dir.is_dir(), "assets/ directory missing"

    for name in ["ExplorerPro.png", "DesktopIcon.png", "icon.png"]:
        path = assets_dir / name
        assert path.exists(), f"Missing {name} in assets/"
        with Image.open(path) as img:
            assert img.size == (1024, 1024), f"{name} size is {img.size}"
            assert img.mode == "RGBA", f"{name} mode is {img.mode}"

    for name in ["ExplorerPro.ico", "DesktopIcon.ico", "icon.ico"]:
        path = assets_dir / name
        assert path.exists(), f"Missing {name} in assets/"
        layers = read_ico_layers(path)
        assert layers == EXPECTED_7_LAYERS, f"{name} layers invalid: {layers}"

    # Favicons & Apple Touch
    fav_png = assets_dir / "favicon.png"
    assert fav_png.exists(), "assets/favicon.png missing"
    with Image.open(fav_png) as img:
        assert img.size == (32, 32)

    fav_64 = assets_dir / "favicon-64.png"
    assert fav_64.exists(), "assets/favicon-64.png missing"
    with Image.open(fav_64) as img:
        assert img.size == (64, 64)

    fav_ico = assets_dir / "favicon.ico"
    assert fav_ico.exists(), "assets/favicon.ico missing"
    assert read_ico_layers(fav_ico) == EXPECTED_FAVICON_LAYERS

    touch_png = assets_dir / "apple-touch-icon.png"
    assert touch_png.exists(), "assets/apple-touch-icon.png missing"
    with Image.open(touch_png) as img:
        assert img.size == (180, 180)


def test_mobile_pwa_icons_and_manifest():
    """Verify mobile_icons/ PWA suite, maskable icons and W3C manifest."""
    mobile_dir = REPO_ROOT / "mobile_icons"
    assert mobile_dir.is_dir(), "mobile_icons/ directory missing"

    master_mobile = mobile_dir / "icon.png"
    assert master_mobile.exists(), "mobile_icons/icon.png missing"
    with Image.open(master_mobile) as img:
        assert img.size == (1024, 1024)
        assert img.mode == "RGBA"

    expected_sizes = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-maskable-192.png": (192, 192),
        "icon-maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
        "apple-touch-icon-180.png": (180, 180),
        "favicon.png": (32, 32),
    }
    for file_name, size in expected_sizes.items():
        path = mobile_dir / file_name
        assert path.exists(), f"Missing {file_name} in mobile_icons/"
        with Image.open(path) as img:
            assert img.size == size, f"{file_name} size {img.size} != {size}"

    # icons/ subfolder parity
    sub_dir = mobile_dir / "icons"
    assert sub_dir.is_dir(), "mobile_icons/icons/ missing"
    for name, size in [
        ("Icon-192.png", (192, 192)),
        ("Icon-512.png", (512, 512)),
        ("Icon-maskable-192.png", (192, 192)),
        ("Icon-maskable-512.png", (512, 512)),
        ("favicon.png", (32, 32)),
    ]:
        path = sub_dir / name
        assert path.exists(), f"Missing {name} in mobile_icons/icons/"
        with Image.open(path) as img:
            assert img.size == size

    # Manifest
    manifest_path = mobile_dir / "manifest.json"
    assert manifest_path.exists(), "manifest.json missing"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data.get("name") == "ExplorerPro"
    assert data.get("short_name") == "ExplorerPro"
    assert data.get("display") == "standalone"
    assert len(data.get("icons", [])) >= 4


def test_store_assets_integrity():
    """Verify Microsoft Store assets and canonical icon_* suite."""
    store_dir = REPO_ROOT / "store_assets"
    assert store_dir.is_dir(), "store_assets/ missing"

    # Preflight required icons
    required_store = [
        "Square44x44Logo.png",
        "Square150x150Logo.png",
        "Wide310x150Logo.png",
        "Square310x310Logo.png",
        "StoreLogo.png",
    ]
    for name in required_store:
        assert (store_dir / name).exists(), f"Missing required store asset: {name}"

    # Pipeline canonical icons
    canonical_icons = {
        "icon_44x44.png": (44, 44),
        "icon_50x50.png": (50, 50),
        "icon_150x150.png": (150, 150),
        "icon_310x150.png": (310, 150),
        "icon_310x310.png": (310, 310),
    }
    for name, size in canonical_icons.items():
        path = store_dir / name
        assert path.exists(), f"Missing canonical store asset: {name}"
        with Image.open(path) as img:
            assert img.size == size, f"{name} size {img.size} != {size}"


def test_app_icon_loader_returns_valid_icon():
    """Verify src.main.load_app_icon() returns a valid, non-null QIcon."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    if str(REPO_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "src"))

    from main import load_app_icon

    icon = load_app_icon()
    assert isinstance(icon, QIcon), "load_app_icon() did not return a QIcon"
    assert not icon.isNull(), "load_app_icon() returned a null QIcon"
    available_sizes = icon.availableSizes()
    assert len(available_sizes) > 0, "Icon has no available sizes"
