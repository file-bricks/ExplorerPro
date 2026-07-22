<img src="assets/banner_v2.svg" width="100%" alt="ExplorerPro Banner">

# ExplorerPro Suite

[English](README.md) | **[Deutsch](README_de.md)** | [Maschinenlesbarer Kontext](llms.txt)

[![Lizenz: AGPL v3](https://img.shields.io/badge/Lizenz-AGPL%20v3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Plattform: Windows](https://img.shields.io/badge/Plattform-Windows-lightgrey.svg)]()

> Power-User-Dateimanager für den Desktop — Mehrtab-Browser, Vorschau, Datenschutz, Duplikatsuche, Sync & Code-Editor in einer PySide6-App.



ExplorerPro ist ein lokaler Desktop-Dateimanager für Power User. Die App bündelt Mehrtab-Dateibrowser, Vorschau, Datenschutzprüfung, Duplikatsuche, Synchronisation, App-Launcher, Prompt-Sammlung und einen leichten Code-Editor in einer PySide6-Oberfläche.

## Funktionen

- **Dateibrowser:** Mehrtab-Navigation mit Breadcrumbs und Kontextmenüs.
- **Vorschau:** PDF-, Bild-, Quellcode-, Text-, Ordner- und Windows-Verknüpfungsvorschau direkt in der App.
- **Datenschutzprüfung:** Hinweise auf sensible Dateinamen oder Inhalte.
- **Erweiterte Suche:** Filter nach Typ, Größe, Datum und Suchtext.
- **Duplikatsuche:** Hash-basierte Duplikaterkennung.
- **Schnell-Editor:** Integrierter Editor mit Syntax-Highlighting (u. a. Python, JSON, TOML).
- **Synchronisation:** Lokale Ordner-Synchronisation mit Ausschlussmustern.
- **Launcher:** Schnellzugriff auf konfigurierte Apps und Prompts.

## Installation

```bash
git clone https://github.com/file-bricks/ExplorerPro.git
cd ExplorerPro
python --version  # Python 3.10+
python -m pip install -r requirements.txt
```

## Start

```bash
python src/main.py
```

Unter Windows kann auch der Launcher im Projektroot genutzt werden:

```bat
START_ExplorerPro.bat
```

## Plattformplan

ExplorerPro bleibt eine Desktop-App. Windows ist die Hauptplattform und Store-Kandidat. macOS und Linux sind Source- und Build-Smoke-Ziele. Eine separate Web-, Android- oder iOS-Oberfläche ist derzeit mangels eigenständigem Usecase No-Go.

Der implementierte, versionierte Austauschvertrag ist in [EXPORTFORMAT.md](EXPORTFORMAT.md) dokumentiert. Sein Standard lässt absolute Pfade, App-Argumente und Prompt-Inhalte aus; ein separater Web/PWA-Viewer ist derzeit begründet No-Go. Der Plattform- und Store-Plan steht in [PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md).

## Windows Store

Die lokale Windows-Store-Basis liegt jetzt in
[store_package.json](store_package.json), [STORE_LISTING.md](STORE_LISTING.md),
[SUPPORT.md](SUPPORT.md) und [WINDOWS_STORE_PREP.md](WINDOWS_STORE_PREP.md).
Der aktuelle Basisscreenshot liegt unter
[`README/screenshots/main.png`](README/screenshots/main.png); das redigierte
Store-Screenshot-Set mit `main-window.png`, `search.png`, `duplicates.png`
und `sync.png` liegt unter [`README/screenshots/store/`](README/screenshots/store)
und wird über `python generate_store_screenshots.py` reproduziert.

## Tests

```bash
python -m pytest -q
python -m compileall -q src tests manage_translations.py translator.py
```

Die Tests decken Import-Smokes, Weitergabe des Suchfilters "Im Inhalt", Fehlerbehandlung beim Datei-/Ordner-Öffnen, aufgelöste `.lnk`-Vorschauziele und Basis-Bootstrapping ab.

## Datenschutz

ExplorerPro arbeitet mit lokal gewählten Dateien. Für die Kernfunktionen sind kein Cloud-Backend und kein externes Konto nötig. Lokale Scan-Ergebnisse, private Dateilisten, Logs, Build-Ausgaben und Test-Artefakte gehören nicht ins Repository.

Siehe [PRIVACY_POLICY.md](PRIVACY_POLICY.md).
Store-bezogene Supporthinweise stehen in [SUPPORT.md](SUPPORT.md).

## Screenshot

![ExplorerPro Hauptfenster](README/screenshots/main.png)

## Lizenz

ExplorerPro steht unter AGPL v3. Siehe [LICENSE](LICENSE).

Dieses Projekt nutzt PySide6 unter LGPL-kompatiblen Bedingungen und PyMuPDF unter AGPL-Bedingungen.
Eine vollständige Liste der Drittanbieter-Abhängigkeiten und ihrer Lizenzen steht in
[THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt).

## Status

- Version: 1.0.0
- Maintainer: Lukas Geiger
- Letzte Dokumentationsprüfung: 2026-07-22

## Haftung

Dieses Projekt wird unentgeltlich als Open-Source-Software bereitgestellt. Nutzung auf eigenes Risiko. Es gibt keine Wartungszusage, Verfügbarkeitsgarantie, Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.
