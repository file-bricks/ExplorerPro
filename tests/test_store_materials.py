from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_version_from_pyproject() -> str:
    content = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_store_package_matches_project_metadata() -> None:
    package = json.loads((PROJECT_ROOT / "store_package.json").read_text(encoding="utf-8"))

    assert package["app_name"] == "ExplorerPro"
    assert package["identity_name"] == "Geiger.ExplorerPro"
    assert package["executable"] == "ExplorerPro.exe"
    assert package["capabilities"] == "runFullTrust"
    assert package["category"] == "Productivity"
    assert package["license"] == "AGPL-3.0-only"
    assert package["version"] == f"{_read_version_from_pyproject()}.0"
    assert package["privacy_url"].endswith("/PRIVACY_POLICY.md")
    assert package["support_url"].endswith("/SUPPORT.md")


def test_store_documents_exist_and_reference_public_paths() -> None:
    listing = (PROJECT_ROOT / "STORE_LISTING.md").read_text(encoding="utf-8")
    support = (PROJECT_ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    prep = (PROJECT_ROOT / "WINDOWS_STORE_PREP.md").read_text(encoding="utf-8")
    screenshot_note = (PROJECT_ROOT / "README" / "screenshots" / "store" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "https://github.com/file-bricks/ExplorerPro/blob/main/PRIVACY_POLICY.md" in listing
    assert "https://github.com/file-bricks/ExplorerPro/blob/main/SUPPORT.md" in listing
    assert "https://github.com/file-bricks/ExplorerPro/issues" in support
    assert "dist/ExplorerPro/ExplorerPro.exe" in prep
    assert "python generate_store_screenshots.py" in screenshot_note
    assert "main-window.png" in screenshot_note
    assert "search.png" in screenshot_note
    assert "duplicates.png" in screenshot_note
    assert "sync.png" in screenshot_note
    assert "THIRD_PARTY_LICENSES.txt" in prep
    assert "Dediziertes Store-Screenshot-Set fehlt noch." not in prep


def test_existing_main_screenshot_is_present() -> None:
    main_screenshot = PROJECT_ROOT / "README" / "screenshots" / "main.png"
    assert main_screenshot.exists()


def test_store_screenshot_set_is_present() -> None:
    store_dir = PROJECT_ROOT / "README" / "screenshots" / "store"
    for filename in ("main-window.png", "search.png", "duplicates.png", "sync.png"):
        assert (store_dir / filename).exists()
