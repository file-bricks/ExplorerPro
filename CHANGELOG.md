# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt / Added
- GitHub Actions Smoke-Test-Workflow für Python 3.10, 3.11 und 3.12.
- Repository-Privacy-Policy.
- `README_de.md` und `llms.txt` als deutschsprachige und maschinenlesbare Projektkontexte.
- PyInstaller-Spec und Build-Launcher für reproduzierbarere Windows-Builds.
- Windows-Store-Basis mit `store_package.json`, `STORE_LISTING.md`, `SUPPORT.md`,
  `WINDOWS_STORE_PREP.md`, Screenshot-Inventar und Store-Material-Test.
- Reproduzierbarer Desktop-Plattform-Smoke `tests/source_platform_smoke.py` für Linux und macOS.

### Geändert / Changed
- README, Contributing Guide und Code of Conduct auf das aktuelle Repository `file-bricks/ExplorerPro` aktualisiert.
- Öffentliche private Kontaktadresse aus dem Code of Conduct entfernt.
- `.gitignore` um Test-, Coverage- und Cache-Artefakte erweitert.
- Community-Workflows und Testworkflow auf aktuelle GitHub-Actions-Major-Versionen aktualisiert.
- README mit Plattformplan, Exportformat und aktuellem Wartungsstand abgeglichen.
- Portierungsplan markiert die Windows-Store-Basis jetzt als erledigten P0-Schritt.
- Desktop-Öffnen nutzt jetzt plattformgerecht `open` auf macOS und `xdg-open` auf Linux.

### Behoben / Fixed
- Die Such-Checkbox "Im Inhalt" wird jetzt an den Index-Worker weitergereicht.
- Datei-/Ordner-Öffnen zeigt bei fehlender Systemzuordnung eine UI-Warnung statt still zu scheitern.
- macOS hing beim Datei-/Ordner-Öffnen nicht mehr fälschlich am Linux-Handler `xdg-open`.
- Mojibake in README- und Workflow-Texten bereinigt.

## [1.0.0] - 2026-03-05

### Hinzugefügt / Added
- Erstveröffentlichung / Initial release
