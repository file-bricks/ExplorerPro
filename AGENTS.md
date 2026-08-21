# AGENTS.md — Redirect

Dieses Projekt nutzt **[`CLAUDE.md`](./CLAUDE.md)** als kanonische Instruktions-Datei für alle AI-Coding-Agenten.

Der Inhalt ist **tool-agnostisch**. Der Dateiname ist Claude-Code-spezifisch nur deshalb, weil Claude Code die Datei automatisch in den Kontext lädt — dadurch entfällt ein extra Dateizugriff für das primäre Tool. Andere Agenten (Gemini/Antigravity, Codex, Cursor, Cline, Aider, Copilot) lesen **CLAUDE.md direkt**.

→ **Weiter zu [CLAUDE.md](./CLAUDE.md)**

---

**Warum diese Datei existiert:** Wenn du ein Agent-Tool nutzt, das `AGENTS.md` als Standard liest (OpenAI Codex, neuere Versionen von Aider, etc.), landest du hier und wirst weitergeleitet. Single Source of Truth bleibt CLAUDE.md — keine Duplikation, kein Sync-Drift.
