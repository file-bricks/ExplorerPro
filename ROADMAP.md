# ExplorerPro Roadmap

## Evidenzabgleich 2026-11-01

Die Juli-Planung und die späteren Oktober-Aufzeichnungen sind zeitlich getrennte Stände. `STORE_ISSUES.md` enthält die historischen Paket-/Submission-Angaben. Aktueller Partner-Center-Status, öffentliche Verfügbarkeit und tatsächlich installierte Version wurden hier nicht abgefragt; ihr Readback steht noch aus.

In diesem Checkout existieren `releases/windowsstore/v1.0.8/release-notes.json` und `releases/windowsstore/v1.0.9/release-notes.json`, jedoch keines der beiden dort genannten `ExplorerPro.msix`-Pakete und keine zugehörigen Abnahme-Receipts in diesen Verzeichnissen. Die protokollierten Paket-Hashes sind daher historische Angaben, keine heute neu berechneten Prüfsummen. `store_package.json` deklariert 1.0.9.0 und `Geiger.ExplorerPro`; das beweist weder Paketinhalt noch Veröffentlichung oder Installation.

WACK ist in den Oktober-Aufzeichnungen als übersprungen dokumentiert, nicht als bestanden. Dieser Abgleich bestätigt keine aktuelle Ausnahme-Policy und beauftragt keinen Administratorlauf. Vor einer künftigen Ausführung sind geltende autorisierte Regeln und paketgebundene Gates zu prüfen. Keine Tests, Builds, Installationen, Uploads oder Store-Mutationen in dieser Dokumentationsänderung.


Stand: 2026-07-22
Status: versionierte, kanonische Planungsübersicht

Diese Roadmap zeigt nur den aktuellen Planungskorridor. Verbindliche
Detailstände und Abnahmekriterien stehen in [AUFGABEN.txt](AUFGABEN.txt) und
[PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md); umgesetzte Änderungen stehen im
[CHANGELOG.md](CHANGELOG.md). Die Produktbeschreibung in [README.md](README.md)
und der maschinenlesbare Kontext in [llms.txt](llms.txt) bleiben die
maßgeblichen Scope-Beschreibungen.

## Eigentümer- und Tracking-Status

- Repository: `file-bricks/ExplorerPro`; Maintainer laut README: Lukas Geiger.
- `ROADMAP.md` lag bis zum TASKPLAN-Abgleich TW-EP-06 am 2026-07-19 als
  untracked Arbeitsnotiz vor.
- Entscheidung TW-EP-06: Die bereinigte Datei wird als projektweite,
  versionierte Roadmap in Git aufgenommen. Sie ist keine persönliche
  Agenten- oder Backup-Notiz.
- Neue Detailaufgaben und Definitionen of Done werden nicht in dieser Übersicht
  dupliziert, sondern in den vorhandenen Steuerdateien gepflegt.

## Historische Roadmap-Punkte — erledigt

| Früherer Roadmap-Punkt | Verifizierter Stand |
|---|---|
| Release-EXE startet ohne reproduzierbaren DLL-/Loader-Abbruch | DONE 2026-07-01; Start-Smoke in `tests/test_release_smoke.py` |
| Drag-and-drop zwischen ExplorerPro und externen Anwendungen | DONE 2026-06-27; Implementierung und Tests sind in AUFGABEN/Changelog dokumentiert |
| Read-only Excel-Vorschau für `.xlsx`/`.xls` mit Fallback | DONE 2026-06-28; `src/core/xlsx_reader.py`, Preview-Widget und Tests vorhanden |
| Weitere Coding-Textformate | DONE 2026-06-27; YAML, Shell, C/C++, INI und Markdown ergänzt |
| Software-Originalicons | DONE 2026-06-28; zentraler Icon-Helper und Tests vorhanden |

Diese Punkte sind kein offener Arbeitsvorrat mehr.

## Release-Gates — Juli-Planung mit späterem Evidenzabgleich

| Priorität | Gate | Kanonischer Detailstand |
|---|---|---|
| P0 extern | ExplorerPro-MSIX und WACK-Readback | [AUFGABEN.txt](AUFGABEN.txt), [PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md) und [WINDOWS_STORE_PREP.md](WINDOWS_STORE_PREP.md); historisch fehlten SDK/App Certification Kit; spätere Einreichungen stehen in STORE_ISSUES.md, aktueller Live-/Installationsreadback steht noch aus |
| P0 je Release | Tatsächlichen EXE-/MSIX-Bundle-Inhalt gegen den Dependency- und Lizenzvertrag rücklesen | `pyproject.toml`, `requirements.txt`, `THIRD_PARTY_LICENSES.txt` und `_sources/CROSSCHECK.md` sind seit 2026-07-22 synchron; ein frischer Bundle-Readback darf nicht durch Doku ersetzt werden |

## Am 2026-07-22 geschlossen

- Release-Hygiene und Fremdänderungen sind klassifiziert; Backups, Lock und unreferenzierte Mobile/PWA-Assets bleiben außerhalb von Git und Release.
- Der Standardexport ist privacy-sicher; App-Argumente und Prompt-Inhalte benötigen ein separates Opt-in.
- Ein separater Web/PWA-Viewer ist mangels eigenständigem Usecase No-Go.
- DnD-Kollisionen und Ordner-Nachfahren-Drops sind fail-closed regressionsgesichert.

## Nicht-Ziele dieser Roadmap

- Keine eigene parallele Aufgabenliste oder neue Definition of Done.
- Keine native Android-/iOS-Voll-App und kein Web-Dateimanager-Klon.
- Keine Store-Einreichung vor MSIX, WACK, Lizenz- und Privacy-Gates.
- Keine Produktimplementierung durch die reine Roadmap-Synchronisierung.
