# TASKPLAN-Status — ExplorerPro #1324

**Datum:** 2026-09-17  
**Rolle:** TASKSOLVER / `tasksolver-codex`  
**Task:** `[ExplorerPro] EXE/MSIX-Bundle Inhalt gegen Dependency- und Lizenzvertrag prüfen`  
**Versuch:** 3 von 3  
**Status:** SKIP dokumentiert; Task bleibt offen

## Ergebnis

Die lokalen Onedir- und Quellcode-Gates sind belastbar, aber die Definition of Done
ist nicht vollständig erfüllbar. Es gibt keinen autorisierten und reproduzierbar
nachgewiesenen SDK-MSIX-Build mit Signatur-, WACK- und Store-Readback. Deshalb wird
kein `done` gesetzt und kein Release- oder OneDrive-Artefakt übernommen.

## Verifizierte lokale Evidenz

- Kanonischer Klon: `C:\_Local_DEV\repos\ExplorerPro`, `master`, vor der Änderung sauber
  auf `612c35b`; nach der lokalen Maßnahme ein Commit voraus gegenüber `origin/master`.
- Frischer PyInstaller-Onedir-Build Versuch 1: Exit 0, 1.800 Dateien,
  345.293.216 Bytes, `ExplorerPro.exe` 18.468.626 Bytes,
  SHA-256 `2E82394B07C8D429D5C8CA26EEA365B97EA5685D801E4C60028D2C0CE173690B`.
- Frischer PyInstaller-Onedir-Build Versuch 2 nach Packaging-Änderung: Exit 0,
  1.804 Dateien, `ExplorerPro.exe` 18.468.626 Bytes,
  SHA-256 `D12CD1721D3476991C28203339A9A777087B96D163DE97CDF904A34FB41B2817`.
- `ExplorerPro.spec` nimmt `LICENSE`, `THIRD_PARTY_LICENSES.txt`,
  `PRIVACY_POLICY.md` und `SUPPORT.md` als Daten auf. `build_exe.bat` kopiert sie
  zusätzlich auf die Bundle-Wurzelebene. Der lokale Test dafür besteht; die
  Änderung ist in Commit `717082d292ab6b2fadd5019a48d117143d3984e3` mit DCO-Signoff.
- Volltests nach der Änderung: `323 passed, 2 skipped`; die beiden Skips sind der
  fehlende historische Release-EXE-Smoke und der native Qt-Screenshot-Smoke.
  Compileall, `manage_translations.py --check`, Ruff, Store-Readiness und
  `git diff --check` bestanden.

## Nicht erfüllte Abschluss-Gates

1. Der frische PyInstaller-Graph zieht neben den vier direkten Runtime-Paketen
   weitere Hook-/transitive Komponenten ein. Unter anderem erscheinen
   `aiohttp`, `bcrypt`, `certifi`, `chardet`, `charset-normalizer`,
   `cryptography`, `fsspec`, `frozenlist`, `invoke`, `lxml`, `lz4`,
   `MarkupSafe`, `multidict`, `paramiko`, `propcache`, `psutil`, `pyarrow`,
   `pydantic`, `tqdm` und `yarl`; sie sind nicht vollständig gegen das
   projektseitige `THIRD_PARTY_LICENSES.txt` adjudiziert. Ein versionierter
   Closure-/Lizenzmanifest-Snapshot fehlt weiterhin.
2. Die aktuelle OneDrive-Projektion wurde nur lesend via FileCommander geprüft.
   `releases/ExplorerPro.msix` hat 97.112.151 Bytes und SHA-256
   `84AF3F207D289B92DBA49A6A1B8CB071B669A0738E90C6E0F860892304A8964F`.
   Das Archiv enthält 941 Einträge; auf der Wurzelebene liegen nur
   `AppxBlockMap.xml`, `AppxManifest.xml`, `ExplorerPro.exe` und
   `[Content_Types].xml`. `LICENSE`, `THIRD_PARTY_LICENSES.txt`,
   `PRIVACY_POLICY.md` und `SUPPORT.md` fehlen dort weiterhin.
3. Das OneDrive-Manifest weist `Geiger.ExplorerPro`, den Publisher und
   `Version="1.0.0.0"` aus; `store_package.json` deklariert dagegen `1.0.5.0`.
   Die Projektdatei liegt unter aktivem `cldflt.sys`-Cloud-Lock-Risiko hoch.
   Die Projektion ist daher kein akzeptierter lokaler Release-Readback und wurde
   nicht verändert.
4. `makeappx.exe`, `signtool.exe` und `appcert.exe` sind lokal nicht vorhanden.
   Ein frischer Windows-SDK-MSIX-Build, Signaturprüfung, WACK-Protokoll und
   separater Store-/Partner-Center-Readback konnten daher nicht belegt werden.

## SKIP-Grund

**Dritter erfolgloser Bearbeitungsversuch:** Der lokale Packaging-Vertrag wurde
verbessert und getestet, aber die autorisierte Dependency-/Lizenz-Closure sowie
die externen MSIX-, Signatur-, WACK- und Store-Gates bleiben ohne Windows SDK,
Release-/Notice-Entscheidung und autorisierten Store-Readback offen. Task 1324
bleibt deshalb offen; kein Release, Upload oder OneDrive-Mutation durch
TASKSOLVER.
