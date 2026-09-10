# Third-Party Software Licenses & Runtime Invariants

Stand: **2026-09-10**  
Repository: **file-bricks/ExplorerPro**  
Primary License: **GNU Affero General Public License v3 (AGPL-3.0)**  
Parent Organization: **file-bricks**  
Umbrella Ecosystem: **open-bricks**

---

## 1. Overview & Licensing Policy

ExplorerPro is a 100% local-first, privacy-aware desktop file manager and power-user explorer suite. The application itself is licensed under the **GNU Affero General Public License v3 (AGPL-3.0)**.

To maintain absolute software integrity, zero-egress security, and compliance with open-source licensing standards, all direct runtime, optional, and build dependencies have been audited. ExplorerPro utilizes only components with compatible permissive or copyleft licenses (LGPL-3.0, AGPL-3.0, BSD-3-Clause, MIT, PSFL-2.0).

---

## 2. Direct Runtime Dependencies

The core execution environment depends strictly on the following packages:

| Package | Version Range | License | Role / Purpose | Integration Model |
|---|---|---|---|---|
| **PySide6** | `>=6.5.0, <7.0.0` | **LGPL-3.0-only** / GPL-2.0 / GPL-3.0 | Desktop GUI Framework (Qt 6 widgets, event loop, styling) | Dynamically linked shared libraries; no proprietary Qt modifications |
| **PyMuPDF** (`fitz`) | `>=1.21.0, <2.0.0` | **AGPL-3.0-only** / Artifex Commercial | High-performance PDF rendering and document preview extraction | Direct Python binding; 100% compliant with ExplorerPro's AGPL-3.0 license |
| **pandas** | `>=2.0.0, <4.0.0` | **BSD-3-Clause** | Tabular data analysis and structured CSV/Excel parsing | Imported library for dataset preview and statistics |
| **openpyxl** | `>=3.1.0, <4.0.0` | **MIT** | Modern Microsoft Excel (`.xlsx`) sheet parsing and metadata extraction | Standard Python library for spreadsheet preview |

---

## 3. Optional & Platform Dependencies

ExplorerPro provides specialized extensions and fallback handlers when certain environments or legacy document formats are detected:

| Package | Version Range | License | Role / Purpose | Trigger Condition |
|---|---|---|---|---|
| **PyInstaller** | `>=6.0.0, <7.0.0` | **GPL-2.0-or-later** (with packaging exception) | Standalone executable compilation (`ExplorerPro.exe`) | Build-time packaging only; not bundled into source distributions |
| **PyPDF2** | `>=3.0.0, <4.0.0` | **BSD-3-Clause** | Legacy PDF fallback extractor when native engines are unavailable | Optional runtime fallback; isolated in preview engine |
| **xlrd** | `>=2.0.0, <3.0.0` | **BSD-3-Clause** | Legacy Microsoft Excel (`.xls`) binary workbook preview | Optional runtime fallback; isolated in spreadsheet preview |
| **pywin32** | `>=306` | **PSFL-2.0** / Mixed Permissive | Windows `.lnk` shortcut target resolution and shell integration | Windows platform only (`platform_system == 'Windows'`) |

---

## 4. Development & Quality Assurance Dependencies

Testing, linting, and quality gate tools used exclusively during development and CI pipelines:

| Tool | Version Range | License | Purpose |
|---|---|---|---|
| **pytest** | `>=8.0.0` | **MIT** | Automated unit, integration, and metadata contract testing |
| **ruff** | `>=0.5.0` | **MIT** / **Apache-2.0** | Extremely fast static Python linter and code style enforcement |
| **setuptools** | Current | **MIT** | PEP 517 / PEP 621 packaging metadata provider |

---

## 5. Architectural & Governance Invariants

All dependencies adhere to five core architectural guarantees:

1. **100% Local-First & Zero-Egress Privacy (`INV-LOCAL-01`)**:
   None of the runtime dependencies establish outgoing network connections, telemetry beacons, cloud synchronizations, or remote API requests. All file manipulation, indexing, and preview rendering occur entirely on the local machine.

2. **Unprivileged RunAsInvoker Security (`INV-SEC-02`)**:
   All dependencies operate within standard user-level permissions. ExplorerPro never demands UAC administrator elevation or sudo privileges.

3. **Dynamic Qt Linking Compliance (`INV-QT-03`)**:
   `PySide6` is dynamically linked against unmodified Qt 6 runtime binaries in full adherence to GNU Lesser General Public License v3 (LGPL-3.0).

4. **Copyleft & AGPL-3.0 Alignment (`INV-AGPL-04`)**:
   `PyMuPDF` is utilized under the AGPL-3.0 terms, which completely matches and reinforces ExplorerPro's top-level AGPL-3.0 licensing architecture.

5. **Safe File Operations & Destruction Defense (`INV-SAFE-05`)**:
   File deletion, duplicate elimination, and folder synchronization delegate destructive actions to the operating system's native Recycle Bin or enforce explicit, cancel-default confirmation gates.

---

## 6. Full License Texts Summary

### LGPL-3.0 (GNU Lesser General Public License v3)
Used by: `PySide6`  
Permissions: Commercial use, modification, distribution.  
Requirements: Shared library dynamic linking, source disclosure of modified library portions (none performed).

### AGPL-3.0 (GNU Affero General Public License v3)
Used by: `ExplorerPro`, `PyMuPDF`  
Permissions: Commercial use, modification, distribution, network service interaction.  
Requirements: Complete source disclosure under AGPL-3.0, license notice retention.

### BSD-3-Clause
Used by: `pandas`, `PyPDF2`, `xlrd`  
Permissions: Commercial use, modification, distribution, private use.  
Requirements: Retention of copyright notice, conditions list, and disclaimer; endorsement restrictions.

### MIT License
Used by: `openpyxl`, `pytest`, `ruff`, `setuptools`  
Permissions: Commercial use, modification, distribution, private use, sublicensing.  
Requirements: Inclusion of copyright and permission notice.

### Python Software Foundation License (PSFL-2.0)
Used by: `pywin32`, Python standard library  
Permissions: Commercial use, modification, distribution.  
Requirements: Retention of copyright and license notice.
