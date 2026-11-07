# Windows Store Prep - ExplorerPro

## Evidenzabgleich 2026-11-01

Die Juli-Planung und die späteren Oktober-Aufzeichnungen sind zeitlich getrennte Stände. `STORE_ISSUES.md` enthält die historischen Paket-/Submission-Angaben. Aktueller Partner-Center-Status, öffentliche Verfügbarkeit und tatsächlich installierte Version wurden hier nicht abgefragt; ihr Readback steht noch aus.

In diesem Checkout existieren `releases/windowsstore/v1.0.8/release-notes.json` und `releases/windowsstore/v1.0.9/release-notes.json`, jedoch keines der beiden dort genannten `ExplorerPro.msix`-Pakete und keine zugehörigen Abnahme-Receipts in diesen Verzeichnissen. Die protokollierten Paket-Hashes sind daher historische Angaben, keine heute neu berechneten Prüfsummen. `store_package.json` deklariert 1.0.9.0 und `Geiger.ExplorerPro`; das beweist weder Paketinhalt noch Veröffentlichung oder Installation.

WACK ist in den Oktober-Aufzeichnungen als übersprungen dokumentiert, nicht als bestanden. Dieser Abgleich bestätigt keine aktuelle Ausnahme-Policy und beauftragt keinen Administratorlauf. Vor einer künftigen Ausführung sind geltende autorisierte Regeln und paketgebundene Gates zu prüfen. Keine Tests, Builds, Installationen, Uploads oder Store-Mutationen in dieser Dokumentationsänderung.


Stand: 2026-07-18

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

## Historischer Pretest-Entwurf (Juli 2026, keine Ausführungsanweisung)

1. `build_exe.bat` ausführen und prüfen, dass `dist/ExplorerPro/ExplorerPro.exe` entsteht.
2. `python generate_store_screenshots.py` ausführen und das Store-Screenshot-Set gemäß `README/screenshots/store/README.md` prüfen.
3. `THIRD_PARTY_LICENSES.txt` kurz gegen die aktuelle Runtime-Liste gegenlesen, damit Store- und Lizenzartefakte vollständig bleiben.
4. Den vorgesehenen Store-Pretest gegen ExplorerPro-Pfade laufen lassen; der historische Pfad `_STORE/msstore_pretest.ps1` ist im aktuellen Checkout noch nicht vorhanden und muss vor Ausführung geklärt oder angelegt werden.
5. MSIX bauen.
6. Historischer Entwurf: WACK als Administrator. Nicht als aktuelle Anweisung verwenden; zuerst geltende autorisierte Regeln prüfen (siehe Evidenzabgleich oben).
7. Partner-Center-Eintrag mit den Texten aus `STORE_LISTING.md` befüllen.

## Im Juli 2026 dokumentierte Blocker

- Damaliger Stand: MSIX noch nicht gebaut; spätere Oktober-Aufzeichnungen dokumentieren gebaute Pakete, die hier aktuell nicht vorliegen.
- WACK-Protokoll fehlt noch.
- Der im Ablauf genannte `_STORE/msstore_pretest.ps1`-Pfad fehlt im aktuellen Checkout.
- Windows SDK/App Certification Kit sowie `makeappx.exe`, `signtool.exe` und `appcert.exe` wurden am 2026-07-22 weder im `PATH` noch unter dem üblichen Windows-Kits-Pfad gefunden. Installation und ein signierter MSIX-/WACK-Lauf bleiben externe Gates.

## Hinweise zu Store-Claims

- ExplorerPro ist eine lokale Desktop-App und kein Cloud-Dateimanager.
- Es gibt keine öffentliche Upload-Webapp und keine Pflicht zur Kontoregistrierung.
- Wegen `runFullTrust` ist ein klassischer Desktop-Bridge-/MSIX-Pfad zu erwarten.
