"""
Regressionstests für PrivacyMonitor und BlacklistManager:
1. Span-basierte Anonymisierung ohne Korrumpierung von Wort-Substrings (z.B. 'johanna' bei Blacklist-Eintrag 'anna').
2. Korrekte Auflösung überlappender Treffer (z.B. E-Mail-Adresse und darin enthaltene Blacklist-Domain).
3. Whitelist-Durchsetzung in der Methode anonymize().
4. Fallunterscheidung bei case_sensitive = True in der Whitelist.
5. Schutz vor leeren oder Whitespace-Einträgen in Blacklist/Whitelist.
6. BlacklistManager.export_to_file erstellt fehlende Elternverzeichnisse automatisch.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.privacy.privacy_monitor import BUILTIN_PATTERNS, PrivacyMonitor, PrivacyStatus
from modules.privacy.blacklist_manager import BlacklistManager


def _build_monitor(
    blacklist: list[str] | None = None,
    whitelist: list[str] | None = None,
    whole_words: bool = True,
    case_sensitive: bool = False,
    enable_all_patterns: bool = True,
) -> PrivacyMonitor:
    m = PrivacyMonitor.__new__(PrivacyMonitor)
    m._enabled = True
    m.blacklist = set(blacklist or [])
    m.whitelist = set(whitelist or [])
    m.whole_words = whole_words
    m.case_sensitive = case_sensitive
    m.pattern_enabled = {k: enable_all_patterns for k in BUILTIN_PATTERNS}
    m._compile_patterns()
    return m


class TestPrivacyMonitorSpanRedaction:
    """Verifiziert span-basierte Anonymisierung und Substring-Schutz."""

    def test_substring_preservation_whole_words(self):
        """'johanna' darf bei Blacklist 'anna' und whole_words=True nicht verstümmelt werden."""
        m = _build_monitor(blacklist=["anna"], whole_words=True)
        text = "johanna und anna"
        alert = m.check_text(text)
        assert alert.anonymized_text == "johanna und [***]", (
            f"Erwartet 'johanna und [***]', erhalten: '{alert.anonymized_text}'"
        )

    def test_overlapping_email_and_blacklist_domain(self):
        """Überlappende Treffer (E-Mail + Domain) müssen zu einem sauberen Placeholder verschmelzen."""
        m = _build_monitor(blacklist=["geheim.com"], whole_words=False)
        text = "Kontakt: info@geheim.com und Domain geheim.com"
        alert = m.check_text(text)
        assert alert.anonymized_text == "Kontakt: [***] und Domain [***]", (
            f"Erwartet 'Kontakt: [***] und Domain [***]', erhalten: '{alert.anonymized_text}'"
        )
        assert alert.status == PrivacyStatus.RED or alert.status == PrivacyStatus.YELLOW

    def test_anonymize_enforces_whitelist(self):
        """anonymize() muss Whitelist-Begriffe unangetastet lassen."""
        m = _build_monitor(
            whitelist=["allowed@example.com"],
            blacklist=["evil"],
            whole_words=True,
        )
        text = "Mail: allowed@example.com und secret@evil.com"
        anonymized = m.anonymize(text)
        assert "allowed@example.com" in anonymized, (
            f"Whitelisted E-Mail wurde in anonymize() gelöscht: '{anonymized}'"
        )
        assert "[***]" in anonymized
        assert "secret@evil.com" not in anonymized

    def test_case_sensitive_whitelist_matching(self):
        """Bei case_sensitive=True muss die Whitelist Casing strikt unterscheiden."""
        m = _build_monitor(
            whitelist=["Allowed@Example.com"],
            case_sensitive=True,
        )
        # Abweichende Kleinschreibung wird als sensibel erkannt
        alert_lower = m.check_text("Mail: allowed@example.com")
        assert alert_lower.status != PrivacyStatus.GREEN
        assert alert_lower.anonymized_text == "Mail: [***]"

        # Exakte Schreibweise ist erlaubt
        alert_exact = m.check_text("Mail: Allowed@Example.com")
        assert alert_exact.status == PrivacyStatus.GREEN
        assert alert_exact.anonymized_text == "Mail: Allowed@Example.com"

    def test_empty_or_whitespace_blacklist_guard(self):
        """Leere oder nur aus Whitespace bestehende Begriffe dürfen keine Falsch-Positiven erzeugen."""
        m = _build_monitor(blacklist=["", "   ", "\t"], enable_all_patterns=False)
        alert = m.check_text("Ein ganz normaler unbedenklicher Text.")
        assert alert.status == PrivacyStatus.GREEN
        assert alert.anonymized_text == "Ein ganz normaler unbedenklicher Text."

    def test_anonymize_consistent_with_check_text(self):
        """anonymize(text) muss identisch zu check_text(text).anonymized_text sein."""
        m = _build_monitor(
            blacklist=["alpha", "beta"],
            whitelist=["allowed@example.com"],
        )
        samples = [
            "alpha und allowed@example.com und beta",
            "Keine sensiblen Daten hier",
            "DE89370400440532013000 Überweisung",
        ]
        for s in samples:
            alert = m.check_text(s)
            assert m.anonymize(s) == alert.anonymized_text


class TestBlacklistManagerExport:
    """Verifiziert BlacklistManager Export in neue Verzeichnisse."""

    def test_export_to_file_creates_parent_directory(self, tmp_path):
        cfg_dir = tmp_path / "config"
        mgr = BlacklistManager(config_dir=cfg_dir)
        mgr.add_to_blacklist("geheim")

        nested_target = tmp_path / "nested" / "sub" / "exported_bl.txt"
        success = mgr.export_to_file(str(nested_target), source="blacklist")
        assert success is True
        assert nested_target.exists()
        assert "geheim" in nested_target.read_text(encoding="utf-8")
