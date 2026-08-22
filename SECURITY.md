# Security Policy / Sicherheitsrichtlinie

## Deutsch

### Sicherheitsphilosophie & Leitlinien

`file-bricks/ExplorerPro` ist als rein lokale Desktop-Explorer-Suite mit Mehrtab-Dateibrowser, integriertem Quelltext-Editor, PDF-Viewer, Datenschutz-Monitor, Duplikaterkennung und Ordnersynchronisation konzipiert. Sicherheit, Datenschutz und Geheimnisschutz basieren auf folgenden Kernprinzipien:

- **Local-First & Zero-Egress:** ExplorerPro führt alle Dateioperationen, Volltext-Indexierungen (FTS5), Duplikatanalysen und Vorschau-Renderings 100% lokal aus. Es werden keinerlei Telemetriedaten, Nutzungsstatistiken oder Dateiinhalte über das Netzwerk übertragen.
- **Keine Cloud-Zwangsverbindung:** Es existieren keine Zwangsverbindungen zu externen Cloud-Diensten oder Online-APIs. Die Anwendung funktioniert vollständig autark und offline.
- **Unprivilegierter User-Mode (Non-Elevation):** ExplorerPro benötigt und verlangt keine Administratorrechte. Alle Dateioperationen, Suchindizes und Einstellungsdaten laufen streng im unprivilegierten Benutzerkontext ab.
- **Destruktive Sicherheit (Destructive Safety):** Dateioperationen (Löschen, Verschieben, Überschreiben) erfordern explizite Sicherheits-Bestätigungsdialoge oder nutzen den sicheren Papierkorb des Betriebssystems. Es erfolgt kein blindes oder unbestätigtes Löschen von Daten.
- **SQLite- & FTS5-Datenbank-Isolation:** Suchindizes und Metadaten werden in lokalen SQLite-Datenbanken mit WAL-Modus isoliert abgelegt. Datenbankzugriffe sind thread-safe gekapselt.
- **Host-lokale Datenisolation:** Maschinenspezifische Einstellungen (`settings_explorer_pro.json`), Suchdatenbanken und Logs liegen außerhalb des Quellcode-Checkouts im benutzereigenen AppData-/Config-Verzeichnis (`%LOCALAPPDATA%\ExplorerPro`, `~/.config/explorerpro`, `~/Library/Application Support/ExplorerPro`).
- **Sanitärer Workspace-Export:** Das standardisierte Workspace-Austauschformat (`explorerpro-workspace-v1`) schließt absolute Systempfade, Anwendungsargumente und sensible Prompt-Inhalte standardmäßig aus, um ein sicheres Teilen über Teams hinweg zu gewährleisten.

### Unterstützte Versionen

| Version | Unterstützt | Anmerkungen |
| ------- | ----------- | ----------- |
| 1.0.x   | Ja          | Aktuelle Hauptversion mit 6-Sprachen-GUI (i18n), A11y & Multi-OS CI-Härtung |
| < 1.0.0 | Nein        | Bitte auf die aktuelle Version aktualisieren |

### Sicherheitslücken melden

Wenn Sie eine Sicherheitslücke oder ein kritisches Integritätsproblem in ExplorerPro entdecken:

1. **Bevorzugter Meldeweg:** Nutzen Sie die private Vulnerability-Reporting-Funktion direkt auf GitHub:
   - Öffnen Sie den Tab **Security** in diesem Repository
   - Wählen Sie **Report a vulnerability** ([Direktlink](https://github.com/file-bricks/ExplorerPro/security/advisories/new))
   - Beschreiben Sie das Verhalten, Schritte zur Reproduktion und mögliche Auswirkungen
2. **Direkter E-Mail-Kontakt:** Alternativ können Sie sich direkt an unsere Sicherheitskoordinatoren wenden:
   - `security@file-bricks.org`
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

Bitte öffnen Sie für Sicherheitslücken **keine öffentlichen Issues** und veröffentlichen Sie keine sensiblen Dateiinhalte oder Pfade. Bestätigte Sicherheitsprobleme werden mit höchster Priorität behoben.

---

## English

### Security Principles & Core Guarantees

`file-bricks/ExplorerPro` is engineered as a strictly local desktop file explorer suite featuring multi-tab file browsing, an integrated code editor, PDF viewer, privacy monitor, duplicate detection, and folder synchronization. Security, privacy, and secret protection are grounded in the following guarantees:

- **Local-First & Zero-Egress:** ExplorerPro executes all file browsing, FTS5 fulltext indexing, duplicate hashing, and preview rendering 100% locally. No user files, telemetry, or analytics are transmitted across the network.
- **Zero Cloud Requirement:** No mandatory cloud accounts, analytics trackers, or external endpoints. The entire application operates fully offline and self-contained.
- **Unprivileged User-Mode Operation (Non-Elevation):** ExplorerPro operates strictly within standard user privileges and does not require elevated administrator rights.
- **Destructive Safety & Guardrails:** File operations (deletion, moving, overwriting) require explicit confirmation dialogs or route through the operating system recycle bin. No blind or unconfirmed file destruction occurs.
- **SQLite & FTS5 Database Isolation:** Search indices and metadata are isolated within local SQLite databases using WAL mode. Database interactions are encapsulated with thread-safety.
- **Host-Local Runtime Settings & Logs:** Machine-specific settings, search indices, and diagnostic logs live outside the source checkout in host-local directories (`%LOCALAPPDATA%\ExplorerPro`, `~/.config/explorerpro`, `~/Library/Application Support/ExplorerPro`).
- **Sanitized Workspace Exchange Format:** The standardized exchange contract (`explorerpro-workspace-v1`) intentionally omits absolute system paths, launcher arguments, and sensitive prompt bodies by default to ensure safe sharing across teams.

### Supported Versions

| Version | Supported | Notes |
| ------- | --------- | ----- |
| 1.0.x   | Yes       | Active production release with 6-language GUI (i18n), A11y & Multi-OS CI hardening |
| < 1.0.0 | No        | Upgrade to the latest version recommended |

### Reporting a Vulnerability

If you discover a security vulnerability or privacy exposure in ExplorerPro:

1. **Preferred Method:** Report privately via GitHub's Security Advisories flow:
   - Navigate to the **Security** tab of this repository
   - Click **Report a vulnerability** ([Direct Link](https://github.com/file-bricks/ExplorerPro/security/advisories/new))
   - Provide reproduction steps, affected environment, and potential impact
2. **Direct Security Email:** Alternatively, email our security coordinators directly:
   - `security@file-bricks.org`
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

Please **do not disclose vulnerabilities in public issues**. Confirmed security patches are prioritized and released promptly.
