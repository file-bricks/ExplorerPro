# Windows Store Prep - ExplorerPro

Stand: 2026-06-04

## Ziel dieses Dokuments

Dieses Dokument hält die projektlokale Windows-Store-Basis für ExplorerPro fest.
Es ersetzt noch keine echte Einreichung, bündelt aber die Artefakte und Prüfpunkte,
die für den nächsten Store-Schritt bereitstehen oder noch offen sind.

## Bereits vorhanden

- `store_package.json` mit Name, Identity, Version, Kategorie und URLs
- `STORE_LISTING.md` mit DE/EN-Storetexten
- `PRIVACY_POLICY.md` als öffentliche Datenschutzseite
- `SUPPORT.md` als öffentliche Supportseite
- `README/screenshots/main.png` als vorhandener Basis-Screenshot
- `README/screenshots/store/main-window.png`, `search.png`, `duplicates.png` und `sync.png` als dediziertes Store-Screenshot-Set
- `generate_store_screenshots.py` für reproduzierbare, redigierte Store-Screenshots aus Demo-Daten
- `THIRD_PARTY_LICENSES.txt` für die aktuell dokumentierten Python-Abhängigkeiten
- `build_exe.bat` für den lokalen PyInstaller-Build nach `dist/ExplorerPro/ExplorerPro.exe`
- `START_ExplorerPro.bat` mit EXE-Start und Python-Fallback

## Geplanter Pretest-Ablauf

1. `build_exe.bat` ausführen und prüfen, dass `dist/ExplorerPro/ExplorerPro.exe` entsteht.
2. `python generate_store_screenshots.py` ausführen und das Store-Screenshot-Set gemäß `README/screenshots/store/README.md` prüfen.
3. `THIRD_PARTY_LICENSES.txt` kurz gegen die aktuelle Runtime-Liste gegenlesen, damit Store- und Lizenzartefakte vollständig bleiben.
4. `_STORE/msstore_pretest.ps1` mit ExplorerPro-Pfaden laufen lassen.
5. MSIX bauen.
6. WACK als Administrator gegen das MSIX ausführen.
7. Partner-Center-Eintrag mit den Texten aus `STORE_LISTING.md` befüllen.

## Noch offene Blocker

- MSIX wurde für ExplorerPro noch nicht gebaut.
- WACK-Protokoll fehlt noch.

## Hinweise zu Store-Claims

- ExplorerPro ist eine lokale Desktop-App und kein Cloud-Dateimanager.
- Es gibt keine öffentliche Upload-Webapp und keine Pflicht zur Kontoregistrierung.
- Wegen `runFullTrust` ist ein klassischer Desktop-Bridge-/MSIX-Pfad zu erwarten.
