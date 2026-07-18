# ExplorerPro Roadmap

Stand: 2026-07-19
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

## Aktuelle offene Gates

| Priorität | Gate | Kanonischer Detailstand |
|---|---|---|
| P0 | ExplorerPro-MSIX, lokaler Start-Smoke und WACK-Readback | [AUFGABEN.txt](AUFGABEN.txt), [PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md) und [WINDOWS_STORE_PREP.md](WINDOWS_STORE_PREP.md); externe Partner-Center-Freigabe folgt erst nach den lokalen Gates |
| P0 | Dependency- und Lizenzprovenienz für das tatsächliche Release-Bundle | [AUFGABEN.txt](AUFGABEN.txt) und `THIRD_PARTY_LICENSES.txt`; QScintilla/Pygments-Status bleibt vor Release zu klären |
| P0 | Release-Hygiene: Dirty-/Untracked-Baseline, Launcher-Meldungen und Build-Provenienz | TASKPLAN TW-EP-05; dieser Roadmap-Sync verändert keine Asset-, Backup-, Launcher-, Build- oder Produktdateien |
| P2 | Export-/Privacy-Vertrag vollständig rücklesen und begrenzten lokalen Web/PWA-Viewer entscheiden | [AUFGABEN.txt](AUFGABEN.txt), [EXPORTFORMAT.md](EXPORTFORMAT.md) und [PORTIERUNGSPLAN.md](PORTIERUNGSPLAN.md); keine Upload-Webapp und keine Cloud-Synchronisierung |

## Nicht-Ziele dieser Roadmap

- Keine eigene parallele Aufgabenliste oder neue Definition of Done.
- Keine native Android-/iOS-Voll-App und kein Web-Dateimanager-Klon.
- Keine Store-Einreichung vor MSIX, WACK, Lizenz- und Privacy-Gates.
- Keine Produktimplementierung durch die reine Roadmap-Synchronisierung.
