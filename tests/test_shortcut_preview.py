from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from core import shortcut_utils
from core.shortcut_utils import ShortcutPreviewTarget
import gui.preview.preview_panel as preview_panel_mod
from gui.preview.preview_panel import PreviewPanel


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_build_shortcut_preview_target_uses_folder_target(monkeypatch, tmp_path) -> None:
    link = tmp_path / "Ordner.lnk"
    link.write_text("stub", encoding="utf-8")
    target = tmp_path / "Zielordner"
    target.mkdir()

    monkeypatch.setattr(shortcut_utils.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        shortcut_utils,
        "resolve_windows_shortcut_target",
        lambda path: str(target),
    )

    resolved = shortcut_utils.build_shortcut_preview_target(str(link))

    assert resolved == ShortcutPreviewTarget(
        target_path=str(target),
        preview_path=str(target),
        target_kind="directory",
    )


def test_build_shortcut_preview_target_uses_exe_parent(monkeypatch, tmp_path) -> None:
    link = tmp_path / "App.lnk"
    link.write_text("stub", encoding="utf-8")
    target = tmp_path / "bin" / "App.exe"
    target.parent.mkdir()
    target.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(shortcut_utils.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        shortcut_utils,
        "resolve_windows_shortcut_target",
        lambda path: str(target),
    )

    resolved = shortcut_utils.build_shortcut_preview_target(str(link))

    assert resolved == ShortcutPreviewTarget(
        target_path=str(target),
        preview_path=str(target.parent),
        target_kind="executable_parent",
    )


def test_build_shortcut_preview_target_expands_windows_environment_vars(
    monkeypatch, tmp_path
) -> None:
    link = tmp_path / "System.lnk"
    link.write_text("stub", encoding="utf-8")
    target_root = tmp_path / "Windows"
    target = target_root / "System32" / "Tool.exe"
    target.parent.mkdir(parents=True)
    target.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(shortcut_utils.sys, "platform", "win32", raising=False)
    monkeypatch.setenv("EXPLORERPRO_TEST_ROOT", str(target_root))
    monkeypatch.setattr(
        shortcut_utils,
        "resolve_windows_shortcut_target",
        lambda path: "%EXPLORERPRO_TEST_ROOT%/System32/Tool.exe",
    )

    resolved = shortcut_utils.build_shortcut_preview_target(str(link))

    assert resolved == ShortcutPreviewTarget(
        target_path=str(target),
        preview_path=str(target.parent),
        target_kind="executable_parent",
    )


def test_resolve_windows_shortcut_target_ignores_non_windows(monkeypatch, tmp_path) -> None:
    link = tmp_path / "App.lnk"
    link.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(shortcut_utils.sys, "platform", "linux", raising=False)

    assert shortcut_utils.resolve_windows_shortcut_target(str(link)) is None


def test_preview_panel_lists_resolved_shortcut_folder(monkeypatch, tmp_path) -> None:
    _ensure_app()
    link = tmp_path / "Projekt.lnk"
    link.write_text("stub", encoding="utf-8")
    target = tmp_path / "Projekt"
    target.mkdir()
    (target / "README.md").write_text("# Titel", encoding="utf-8")

    monkeypatch.setattr(
        preview_panel_mod,
        "build_shortcut_preview_target",
        lambda path: ShortcutPreviewTarget(
            target_path=str(target),
            preview_path=str(target),
            target_kind="directory",
        ),
    )

    panel = PreviewPanel()
    panel.show_preview(str(link))

    assert panel.preview_stack.currentWidget() is panel.directory_preview
    text = panel.directory_preview.toPlainText()
    assert "Verknüpfung: Projekt.lnk" in text
    assert "README.md" in text
    assert panel.metadata_panel.name_label.text() == target.name


def test_preview_panel_reports_unresolved_shortcut(monkeypatch, tmp_path) -> None:
    _ensure_app()
    link = tmp_path / "Defekt.lnk"
    link.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(preview_panel_mod, "build_shortcut_preview_target", lambda path: None)

    panel = PreviewPanel()
    panel.show_preview(str(link))

    assert panel.preview_stack.currentWidget() is panel.unsupported_label
    assert "konnte nicht aufgelöst werden" in panel.unsupported_label.text()
    assert panel.metadata_panel.name_label.text() == link.name


def _build_lnk(local_path: str, *, env_target: str | None = None) -> bytes:
    """Erzeugt eine minimale MS-SHLLINK-Datei mit LinkInfo bzw. Env-Block."""
    import struct

    flags = 0x80  # IsUnicode
    body = b""
    if env_target is None:
        flags |= 0x02  # HasLinkInfo
        volume = struct.pack("<4I", 0x11, 3, 0, 0x10) + b"\x00"
        header_size = 0x1C
        volume_offset = header_size
        base_offset = volume_offset + len(volume)
        base = local_path.encode("cp1252") + b"\x00"
        suffix_offset = base_offset + len(base)
        suffix = b"\x00"
        size = suffix_offset + len(suffix)
        body += struct.pack(
            "<7I", size, header_size, 0x01, volume_offset, base_offset, 0, suffix_offset
        ) + volume + base + suffix
    else:
        flags |= 0x200  # HasExpString
        ansi = env_target.encode("cp1252").ljust(260, b"\x00")
        wide = env_target.encode("utf-16-le").ljust(520, b"\x00")
        body += struct.pack("<2I", 0x314, 0xA0000001) + ansi + wide
        body += struct.pack("<I", 0)  # TerminalBlock
    header = struct.pack("<I", 0x4C) + bytes.fromhex("0114020000000000c000000000000046")
    header += struct.pack("<I", flags)
    header = header.ljust(0x4C, b"\x00")
    return header + body


def test_native_parser_reads_local_base_path(tmp_path) -> None:
    link = tmp_path / "Tool.lnk"
    link.write_bytes(_build_lnk(r"C:\Tools\Täst\app.exe"))
    assert shortcut_utils.read_shortcut_target_native(str(link)) == r"C:\Tools\Täst\app.exe"


def test_native_parser_reads_environment_block(tmp_path) -> None:
    link = tmp_path / "Env.lnk"
    link.write_bytes(_build_lnk("", env_target=r"%OneDrive%\Dokumente"))
    assert shortcut_utils.read_shortcut_target_native(str(link)) == r"%OneDrive%\Dokumente"


def test_native_parser_rejects_non_shortcuts(tmp_path) -> None:
    junk = tmp_path / "kaputt.lnk"
    junk.write_bytes(b"stub")
    assert shortcut_utils.read_shortcut_target_native(str(junk)) is None
    assert shortcut_utils.parse_shortcut_target(b"\x4c\x00\x00\x00" + b"\x00" * 100) is None


def test_resolution_prefers_native_parser_over_powershell(monkeypatch, tmp_path) -> None:
    link = tmp_path / "Tool.lnk"
    link.write_bytes(_build_lnk(r"C:\Tools\app.exe"))
    monkeypatch.setattr(shortcut_utils.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(shortcut_utils, "_read_shortcut_target_with_win32com", lambda path: None)

    def fail(path):
        raise AssertionError("PowerShell darf nicht gestartet werden")

    monkeypatch.setattr(shortcut_utils, "_read_shortcut_target_with_powershell", fail)
    assert shortcut_utils.resolve_windows_shortcut_target(str(link)) == r"C:\Tools\app.exe"
