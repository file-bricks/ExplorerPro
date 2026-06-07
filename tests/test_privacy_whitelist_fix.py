"""
Bugfix-Test: privacy_monitor.py check_text() – Whitelist vergleicht nun
tatsächliche Match-Inhalte statt Pattern-Label.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.privacy.privacy_monitor import PrivacyMonitor, PrivacyStatus


def _monitor_with_whitelist(*terms: str) -> PrivacyMonitor:
    m = PrivacyMonitor.__new__(PrivacyMonitor)
    m._enabled = True
    m.whitelist = list(terms)
    m.blacklist = []
    m.case_sensitive = False
    m.whole_words = False
    # Alle Builtin-Patterns aktiviert
    from modules.privacy.privacy_monitor import BUILTIN_PATTERNS
    m.pattern_enabled = {k: True for k in BUILTIN_PATTERNS}
    m._compile_patterns()
    return m


class TestWhitelistFix:
    """Whitelist muss tatsächliche Match-Inhalte vergleichen, nicht Pattern-Namen."""

    def test_whitelisted_email_not_anonymized(self):
        monitor = _monitor_with_whitelist("allowed@example.com")
        text = "Kontakt: allowed@example.com"
        alert = monitor.check_text(text)
        assert alert.status == PrivacyStatus.GREEN, (
            "Whitelisted E-Mail wurde fälschlicherweise als sensibel eingestuft"
        )
        assert "allowed@example.com" in alert.anonymized_text, (
            "Whitelisted E-Mail wurde anonymisiert obwohl sie in der Whitelist steht"
        )

    def test_non_whitelisted_email_still_anonymized(self):
        monitor = _monitor_with_whitelist("safe@example.com")
        text = "Kontakt: secret@evil.com"
        alert = monitor.check_text(text)
        assert "[***]" in alert.anonymized_text, (
            "Nicht-whitelisted E-Mail wurde NICHT anonymisiert"
        )

    def test_partial_whitelist_mixed_text(self):
        monitor = _monitor_with_whitelist("allowed@example.com")
        text = "Von: allowed@example.com An: secret@evil.com"
        alert = monitor.check_text(text)
        assert "allowed@example.com" in alert.anonymized_text, (
            "Whitelisted E-Mail wurde anonymisiert"
        )
        assert "[***]" in alert.anonymized_text, (
            "Nicht-whitelisted E-Mail blieb im Klartext"
        )

    def test_pattern_label_name_does_not_bypass_detection(self):
        # Der alte Bug: wenn "E-Mail Adressen" in der Whitelist stand,
        # wurden ALLE E-Mails übersprungen.
        monitor = _monitor_with_whitelist("E-Mail Adressen")
        text = "Kontakt: secret@evil.com"
        alert = monitor.check_text(text)
        # Pattern-Label in Whitelist darf KEINEN Bypass erzeugen
        assert "[***]" in alert.anonymized_text, (
            "Pattern-Label 'E-Mail Adressen' in Whitelist hat fälschlicherweise Detection gebypastet"
        )

    def test_empty_whitelist_detects_all(self):
        monitor = _monitor_with_whitelist()
        text = "IBAN: DE89370400440532013000"
        alert = monitor.check_text(text)
        assert alert.status != PrivacyStatus.GREEN

    def test_check_text_returns_correct_count_with_whitelist(self):
        monitor = _monitor_with_whitelist("allowed@example.com")
        text = "a@b.com allowed@example.com c@d.com"
        alert = monitor.check_text(text)
        detected_str = " ".join(alert.detected_patterns)
        # 2 nicht-whitelisted Treffer: a@b.com und c@d.com
        assert "2x" in detected_str, (
            f"Erwarte 2 erkannte Treffer (exkl. Whitelist), bekam: {alert.detected_patterns}"
        )
