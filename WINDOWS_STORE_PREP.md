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
- `build_exe.bat` für den lokalen PyInstaller-Build nach `dist/ExplorerPro/ExplorerPro.exe`
- `START_ExplorerPro.bat` mit EXE-Start und Python-Fallback

## Geplanter Pretest-Ablauf

1. `build_exe.bat` ausführen und prüfen, dass `dist/ExplorerPro/ExplorerPro.exe` entsteht.
2. Store-Screenshot-Set gemäß `README/screenshots/store/README.md` ergänzen.
3. `THIRD_PARTY_LICENSES.txt` ergänzen, damit Store- und Lizenzartefakte vollständig sind.
4. `_STORE/msstore_pretest.ps1` mit ExplorerPro-Pfaden laufen lassen.
5. MSIX bauen.
6. WACK als Administrator gegen das MSIX ausführen.
7. Partner-Center-Eintrag mit den Texten aus `STORE_LISTING.md` befüllen.

## Noch offene Blocker

- `THIRD_PARTY_LICENSES.txt` fehlt noch.
- Dediziertes Store-Screenshot-Set fehlt noch.
- MSIX wurde für ExplorerPro noch nicht gebaut.
- WACK-Protokoll fehlt noch.

## Hinweise zu Store-Claims

- ExplorerPro ist eine lokale Desktop-App und kein Cloud-Dateimanager.
- Es gibt keine öffentliche Upload-Webapp und keine Pflicht zur Kontoregistrierung.
- Wegen `runFullTrust` ist ein klassischer Desktop-Bridge-/MSIX-Pfad zu erwarten.
