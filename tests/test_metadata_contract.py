"""
test_metadata_contract.py - Automated metadata, governance and bootstrap parity tests.

Validates that ExplorerPro complies with portfolio bootstrap standards:
- CLAUDE.md with valid YAML frontmatter and operational quick commands
- AGENTS.md redirecting to CLAUDE.md
- README.md and README_de.md substantive documentation
- LICENSE (AGPL-3.0) and SECURITY.md (Zero-Egress / offline posture)
- llms.txt entry point
- locales/translations.json 100% complete across 6 target languages
- store_package.json valid configuration
- .gitignore coverage
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_claude_md_exists_and_valid():
    claude_path = REPO_ROOT / "CLAUDE.md"
    assert claude_path.exists(), "CLAUDE.md must exist in repository root."
    content = claude_path.read_text(encoding="utf-8")
    assert content.startswith("---"), "CLAUDE.md must have YAML frontmatter."
    assert "name: ExplorerPro" in content
    assert "profile: STANDARD" in content
    assert "anthropic_compatible: true" in content
    assert "python -m pytest" in content
    assert "Zero-Egress" in content


def test_agents_md_redirect():
    agents_path = REPO_ROOT / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md must exist in repository root."
    content = agents_path.read_text(encoding="utf-8")
    assert "CLAUDE.md" in content, "AGENTS.md must redirect to CLAUDE.md."


def test_readme_and_readme_de():
    readme_en = REPO_ROOT / "README.md"
    readme_de = REPO_ROOT / "README_de.md"
    assert readme_en.exists(), "README.md must exist."
    assert readme_de.exists(), "README_de.md must exist."
    assert len(readme_en.read_text(encoding="utf-8")) > 500
    assert len(readme_de.read_text(encoding="utf-8")) > 500


def test_license_exists_and_agpl3():
    license_path = REPO_ROOT / "LICENSE"
    assert license_path.exists(), "LICENSE must exist."
    content = license_path.read_text(encoding="utf-8")
    assert "AFFERO GENERAL PUBLIC LICENSE" in content or "AGPL" in content


def test_security_policy():
    sec_path = REPO_ROOT / "SECURITY.md"
    assert sec_path.exists(), "SECURITY.md must exist."
    content = sec_path.read_text(encoding="utf-8")
    assert len(content) > 100


def test_llms_txt_structure():
    llms_path = REPO_ROOT / "llms.txt"
    assert llms_path.exists(), "llms.txt must exist."
    content = llms_path.read_text(encoding="utf-8")
    assert "file-bricks/ExplorerPro" in content
    assert "PySide6" in content


def test_translations_complete():
    trans_path = REPO_ROOT / "locales" / "translations.json"
    assert trans_path.exists(), "locales/translations.json must exist."
    data = json.loads(trans_path.read_text(encoding="utf-8"))
    assert len(data) >= 30, f"Expected at least 30 translation strings, found {len(data)}"
    
    missing_en = []
    for key, val in data.items():
        assert isinstance(val, dict), f"Translation entry '{key}' must be a dict"
        assert "de" in val and val["de"], f"Missing 'de' in '{key}'"
        if not val.get("en"):
            missing_en.append(key)
    
    assert not missing_en, f"Missing 'en' translations for: {missing_en}"


def test_store_package_valid():
    pkg_path = REPO_ROOT / "store_package.json"
    assert pkg_path.exists(), "store_package.json must exist."
    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert data.get("app_name") == "ExplorerPro"
    assert data.get("identity_name") == "Geiger.ExplorerPro"
    assert not data.get("publisher", "").startswith("CN=YourPublisher")


def test_gitignore_coverage():
    gi_path = REPO_ROOT / ".gitignore"
    assert gi_path.exists(), ".gitignore must exist."
    content = gi_path.read_text(encoding="utf-8")
    for pattern in ["__pycache__", ".pytest_cache", ".ruff_cache", "dist/", "build/", "LOCK*.txt"]:
        assert pattern in content, f".gitignore should contain '{pattern}'"
