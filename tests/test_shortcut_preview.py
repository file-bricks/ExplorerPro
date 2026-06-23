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
