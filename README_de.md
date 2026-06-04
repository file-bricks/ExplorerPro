# ExplorerPro Suite

[English](README.md) | [Maschinenlesbarer Kontext](llms.txt)

ExplorerPro ist ein lokaler Desktop-Dateimanager für Power User. Die App bündelt Mehrtab-Dateibrowser, Vorschau, Datenschutzprüfung, Duplikatsuche, Synchronisation, App-Launcher, Prompt-Sammlung und einen leichten Code-Editor in einer PySide6-Oberfläche.

## Funktionen

- **Dateibrowser:** Mehrtab-Navigation mit Breadcrumbs und Kontextmenüs.
- **Vorschau:** PDF-, Bild-, Quellcode- und Textvorschau direkt in der App.
- **Datenschutzprüfung:** Hinweise auf sensible Dateinamen oder Inhalte.
- **Erweiterte Suche:** Filter nach Typ, Größe, Datum und Suchtext.
- **Duplikatsuche:** Hash-basierte Duplikaterkennung.
- **Schnell-Editor:** Integrierter Editor mit QScintilla und Pygments.
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

ExplorerPro bleibt zuerst eine Desktop-App. Windows ist die Hauptplattform und Store-Kandidat. macOS und Linux sind P1-Ziele für Source- und Build-Smokes. Web, Android und iOS sind nur als mögliche Companion-Oberflächen für redigierte Exporte vorgesehen, nicht als Ersatz für den lokalen Dateimanager.

Das geplante Austauschformat ist in [EXPORTFORMAT.md](EXPORTFORMAT.md) dokumentiert. Der Plattform- und Store-Plan steht in [PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md).

## Windows Store

Die lokale Windows-Store-Basis liegt jetzt in
[store_package.json](store_package.json), [STORE_LISTING.md](STORE_LISTING.md),
[SUPPORT.md](SUPPORT.md) und [WINDOWS_STORE_PREP.md](WINDOWS_STORE_PREP.md).
Der aktuelle Basisscreenshot liegt unter
[`README/screenshots/main.png`](README/screenshots/main.png); das geplante
Store-Screenshot-Set ist in
[`README/screenshots/store/README.md`](README/screenshots/store/README.md)
dokumentiert.

## Tests

```bash
python -m pytest -q
python -m compileall -q src tests manage_translations.py translator.py
```

Die Tests decken Import-Smokes, Weitergabe des Suchfilters "Im Inhalt", Fehlerbehandlung beim Datei-/Ordner-Öffnen und Basis-Bootstrapping ab.

## Datenschutz

ExplorerPro arbeitet mit lokal gewählten Dateien. Für die Kernfunktionen sind kein Cloud-Backend und kein externes Konto nötig. Lokale Scan-Ergebnisse, private Dateilisten, Logs, Build-Ausgaben und Test-Artefakte gehören nicht ins Repository.

Siehe [PRIVACY_POLICY.md](PRIVACY_POLICY.md).
Store-bezogene Supporthinweise stehen in [SUPPORT.md](SUPPORT.md).

## Screenshot

![ExplorerPro Hauptfenster](README/screenshots/main.png)

## Lizenz

ExplorerPro steht unter AGPL v3. Siehe [LICENSE](LICENSE).

Dieses Projekt nutzt PySide6 unter LGPL-kompatiblen Bedingungen und PyMuPDF unter AGPL-Bedingungen.

## Status

- Version: 1.0.0
- Maintainer: Lukas Geiger
- Letzte Repository-Wartung: 2026-06-04

## Haftung

Dieses Projekt wird unentgeltlich als Open-Source-Software bereitgestellt. Nutzung auf eigenes Risiko. Es gibt keine Wartungszusage, Verfügbarkeitsgarantie, Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.
