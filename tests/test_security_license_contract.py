"""Automated security, dependency floor, and third-party license contract tests for ExplorerPro."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_vulnerability_floors() -> None:
    """Verify requirements.txt and pyproject.toml enforce patched dependency floors against CVEs."""
    req_file = ROOT / "requirements.txt"
    assert req_file.is_file(), "requirements.txt must exist"
    req_text = req_file.read_text(encoding="utf-8")

    assert re.search(r"^PySide6\s*>=\s*6\.5\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce PySide6>=6.5.0 floor"
    )
    assert re.search(r"^PyMuPDF\s*>=\s*1\.21\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce PyMuPDF>=1.21.0 floor"
    )
    assert re.search(r"^pandas\s*>=\s*2\.0\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce pandas>=2.0.0 floor"
    )
    assert re.search(r"^openpyxl\s*>=\s*3\.1\.0", req_text, re.MULTILINE), (
        "requirements.txt must enforce openpyxl>=3.1.0 floor"
    )

    pyproject_file = ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist"
    pyproject_text = pyproject_file.read_text(encoding="utf-8")

    # PEP 621 dependencies section
    assert "dependencies = [" in pyproject_text, "pyproject.toml must define project.dependencies"
    assert "PySide6>=6.5.0" in pyproject_text, "pyproject.toml must specify PySide6>=6.5.0"
    assert "PyMuPDF>=1.21.0" in pyproject_text, "pyproject.toml must specify PyMuPDF>=1.21.0"
    assert "pandas>=2.0.0" in pyproject_text, "pyproject.toml must specify pandas>=2.0.0"
    assert "openpyxl>=3.1.0" in pyproject_text, "pyproject.toml must specify openpyxl>=3.1.0"

    # Dev optional dependencies floor (pytest >= 9.1.1 protects against CVE-2025-7117 / GHSA-6w46-j5rx-g56g)
    assert "[project.optional-dependencies]" in pyproject_text, "pyproject.toml must define optional-dependencies"
    assert "pytest>=9.1.1" in pyproject_text, "pyproject.toml dev dependencies must require pytest>=9.1.1"
    assert "ruff>=0.9.0" in pyproject_text, "pyproject.toml dev dependencies must require ruff>=0.9.0"
    assert "PyInstaller>=6.10.0" in pyproject_text, "pyproject.toml dev dependencies must require PyInstaller>=6.10.0"
    assert "altgraph>=0.17.4" in pyproject_text, "pyproject.toml dev dependencies must require altgraph>=0.17.4"

    # Check author contact email
    assert "support@lukasgeiger.com" in pyproject_text, "pyproject.toml must use official support email"


def test_third_party_licenses_complete_and_accurate() -> None:
    """Verify THIRD_PARTY_LICENSES.txt comprehensively covers runtime, packaging, and test packages."""
    license_file = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert license_file.is_file(), "THIRD_PARTY_LICENSES.txt must exist"
    content = license_file.read_text(encoding="utf-8")

    required_packages = [
        ("PySide6", "LGPL-3.0-only"),
        ("shiboken6", "LGPL-3.0-only"),
        ("PyMuPDF", "AGPL-3.0-or-later"),
        ("pandas", "BSD-3-Clause"),
        ("numpy", "BSD-3-Clause"),
        ("python-dateutil", "Apache-2.0 OR BSD-3-Clause"),
        ("pytz", "MIT"),
        ("tzdata", "Apache-2.0"),
        ("openpyxl", "MIT"),
        ("et_xmlfile", "MIT"),
        ("PyInstaller", "GPL-2.0-or-later WITH Bootloader-exception"),
        ("pyinstaller-hooks-contrib", "Apache-2.0"),
        ("altgraph", "MIT"),
        ("packaging", "Apache-2.0 OR BSD-2-Clause"),
        ("pytest", "MIT"),
        ("pluggy", "MIT"),
        ("iniconfig", "MIT"),
        ("ruff", "MIT OR Apache-2.0"),
        ("PyPDF2", "BSD-3-Clause"),
        ("xlrd", "BSD-3-Clause"),
        ("pywin32", "PSF-2.0"),
    ]

    for pkg, spdx in required_packages:
        assert pkg in content, f"Package {pkg} missing from THIRD_PARTY_LICENSES.txt"
        assert spdx in content, f"SPDX identifier {spdx} for {pkg} missing from THIRD_PARTY_LICENSES.txt"

    # Ensure structured schema fields exist
    assert "License:" in content, "License: field missing in THIRD_PARTY_LICENSES.txt"
    assert "URL:" in content, "URL: field missing in THIRD_PARTY_LICENSES.txt"
    assert "SPDX:" in content, "SPDX: field missing in THIRD_PARTY_LICENSES.txt"
    assert "Notice:" in content, "Notice: field missing in THIRD_PARTY_LICENSES.txt"


def test_gitignore_security_and_multi_host_hardening() -> None:
    """Verify .gitignore blocks private secrets, certificates, and multi-host conflict files."""
    gitignore_file = ROOT / ".gitignore"
    assert gitignore_file.is_file(), ".gitignore must exist"
    content = gitignore_file.read_text(encoding="utf-8")

    # Secrets and certificate protection
    for pat in ["credentials.json", "*.pfx", "*.cer", "*.crt", "*.pem", "*.key", "keyring/", "secrets.*"]:
        assert pat in content, f"Secret pattern {pat} missing in .gitignore"

    # Multi-host sync hardening
    for host_pat in ["*-WORKSTATION-LG*", "*-ASUS-GEI*", "*.sync-conflict-*", "*.conflict"]:
        assert host_pat in content, f"Sync conflict pattern {host_pat} missing in .gitignore"

    # Multi-agent lock system fail-closed patterns
    for lock_pat in ["LOCK.*", "*.lock", "LOCK*.txt"]:
        assert lock_pat in content, f"Lock pattern {lock_pat} missing in .gitignore"

    # Web companion / Node cache patterns
    assert "node_modules/" in content, "node_modules/ pattern missing in .gitignore"


def test_no_hardcoded_user_paths_in_python_code() -> None:
    """Verify no hardcoded personal user profile paths exist in active Python source and tests."""
    disallowed_regex = re.compile(r"""(?i)C:[/\\]Users[/\\](?:lukas|admin|administrator)[/\\]""", re.VERBOSE)

    python_files = [
        p for p in ROOT.rglob("*.py")
        if not any(part in p.parts for part in [".git", ".pytest_cache", ".ruff_cache", "venv", ".venv", "build", "dist"])
    ]
    assert len(python_files) >= 15, f"Expected at least 15 Python files to scan, found {len(python_files)}"

    violating_lines = []
    for py_file in python_files:
        try:
            text = py_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if disallowed_regex.search(line):
                violating_lines.append(f"{py_file.name}:{idx}: {line.strip()}")

    assert not violating_lines, "Found hardcoded user paths in Python code:\n" + "\n".join(violating_lines)


def test_security_policy_bilingual_and_sla() -> None:
    """Verify SECURITY.md provides bilingual policy, security contact addresses, and 48h SLA."""
    sec_file = ROOT / "SECURITY.md"
    assert sec_file.is_file(), "SECURITY.md must exist"
    sec_text = sec_file.read_text(encoding="utf-8")

    assert "## Deutsch" in sec_text, "SECURITY.md must contain German section"
    assert "## English" in sec_text, "SECURITY.md must contain English section"

    # Contact addresses
    assert "security@file-bricks.org" in sec_text, "SECURITY.md must list security@file-bricks.org"
    assert "support@lukasgeiger.com" in sec_text, "SECURITY.md must list support@lukasgeiger.com"

    # SLA commitment
    assert "48 Stunden" in sec_text, "SECURITY.md must define 48h SLA in German"
    assert "48 hours" in sec_text, "SECURITY.md must define 48h SLA in English"
    assert "5 Werktagen" in sec_text or "5 business days" in sec_text, "SECURITY.md must define triage window"
    assert "Local-First & Zero-Egress" in sec_text, "SECURITY.md must document Local-First commitment"


def test_local_first_and_offline_invariants() -> None:
    """Verify absence of unapproved telemetry, analytics, and remote trackers in core modules."""
    disallowed_patterns = [
        re.compile(r"google-analytics\.com", re.IGNORECASE),
        re.compile(r"mixpanel\.com", re.IGNORECASE),
        re.compile(r"segment\.io", re.IGNORECASE),
        re.compile(r"sentry\.io", re.IGNORECASE),
    ]

    core_files = [
        ROOT / "src" / "main.py",
        ROOT / "src" / "app.py",
        ROOT / "translator.py",
    ]

    for core_file in core_files:
        if not core_file.is_file():
            continue
        text = core_file.read_text(encoding="utf-8")
        for pat in disallowed_patterns:
            assert not pat.search(text), f"Disallowed telemetry pattern {pat.pattern} found in {core_file.name}"


def test_ci_workflow_timeouts_and_concurrency() -> None:
    """Verify GitHub Actions workflows define concurrency controls and bounded job timeouts."""
    workflows_dir = ROOT / ".github" / "workflows"
    assert workflows_dir.is_dir(), ".github/workflows must exist"

    expected_workflows = {
        "ci.yml": 15,
        "stale.yml": 10,
        "welcome.yml": 5,
    }

    for wf_name, expected_timeout in expected_workflows.items():
        wf_path = workflows_dir / wf_name
        assert wf_path.is_file(), f"{wf_name} must exist in .github/workflows"
        content = wf_path.read_text(encoding="utf-8")

        assert "concurrency:" in content, f"{wf_name} must define top-level concurrency"
        assert "cancel-in-progress: true" in content, f"{wf_name} must enable cancel-in-progress"
        assert f"timeout-minutes: {expected_timeout}" in content, (
            f"{wf_name} must specify timeout-minutes: {expected_timeout}"
        )


def test_gitignore_comprehensive_multi_host_and_locks() -> None:
    """Verify .gitignore covers cloud sync copies, lock files, and test/build artifacts."""
    gitignore_file = ROOT / ".gitignore"
    assert gitignore_file.is_file(), ".gitignore must exist"
    content = gitignore_file.read_text(encoding="utf-8")

    required_patterns = [
        "LOCK",
        "uv.lock",
        "!package-lock.json",
        "* (copy)*",
        "* (Copy)*",
        "* (kopie)*",
        "* (Kopie)*",
        "*conflicted copy*",
        "*-WORKSTATION*",
        "*-ASUS*",
        "*-LAPTOP*",
        "*-Mac Studio*",
        "*.sync-temp-*",
        "*.orig",
        "*.rej",
        ".coverage.*",
        ".hypothesis/",
        ".turbo/",
        "wheelhouse/",
        ".wheel-smoke/",
    ]

    for pat in required_patterns:
        assert pat in content, f"Pattern {pat} missing from .gitignore"


def test_pep621_urls_and_pytest_options() -> None:
    """Verify pyproject.toml defines required URLs and standard pytest runner options."""
    pyproject_file = ROOT / "pyproject.toml"
    assert pyproject_file.is_file(), "pyproject.toml must exist"
    content = pyproject_file.read_text(encoding="utf-8")

    assert '"LLM Ready" =' in content or 'LLM Ready =' in content, (
        "pyproject.toml must define LLM Ready URL"
    )
    assert "minversion = " in content, "pyproject.toml pytest section must specify minversion"
    assert 'addopts = "-ra -v"' in content, "pyproject.toml pytest section must specify addopts = '-ra -v'"


def test_marketing_log_hygiene_recency() -> None:
    """Verify MARKETING-LOG.txt documents the latest Pfad A repository hygiene audit."""
    mkt_file = ROOT / "MARKETING-LOG.txt"
    assert mkt_file.is_file(), "MARKETING-LOG.txt must exist"
    content = mkt_file.read_text(encoding="utf-8")

    assert "7. REPOSITORY HYGIENE & CI CONTRACT AUDIT" in content, (
        "MARKETING-LOG.txt must include Section 7 for repository hygiene"
    )
    assert "2026-09-16" in content, "MARKETING-LOG.txt must record the 2026-09-16 audit date"
    assert "PASS" in content, "MARKETING-LOG.txt must record PASS status"
