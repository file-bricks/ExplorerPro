"""Deletion must handle Windows read-only files without following links."""

import os
import stat
import subprocess
import sys
from unittest.mock import Mock

import pytest

from core import delete_service


def test_delete_regular_file_and_nested_folder(tmp_path):
    folder = tmp_path / "selected"
    (folder / "nested").mkdir(parents=True)
    (folder / "nested" / "child.txt").write_text("child")
    direct = tmp_path / "direct.txt"
    direct.write_text("direct")
    delete_service.delete_path(str(direct))
    delete_service.delete_path(str(folder))
    assert not direct.exists()
    assert not folder.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file attributes")
@pytest.mark.parametrize("nested", [False, True])
def test_native_readonly_file_deletion(tmp_path, nested):
    folder = tmp_path / "selected"
    folder.mkdir()
    child = folder / "readonly.txt"
    child.write_text("read-only fixture")
    os.chmod(child, stat.S_IREAD)
    try:
        delete_service.delete_path(str(folder if nested else child))
        assert not child.exists()
        if nested:
            assert not folder.exists()
    finally:
        if child.exists():
            os.chmod(child, stat.S_IWRITE)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows read-only hardlink attributes")
@pytest.mark.parametrize("nested", [False, True])
def test_readonly_hardlink_does_not_change_surviving_alias(tmp_path, nested):
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged bytes")
    selected = tmp_path / "selected"
    selected.mkdir()
    alias = selected / "alias.txt"
    os.link(outside, alias)
    os.chmod(alias, stat.S_IREAD)
    original_attributes = outside.stat().st_file_attributes
    try:
        with pytest.raises(PermissionError) as caught:
            delete_service.delete_path(str(selected if nested else alias))
        assert caught.value.winerror == 5
        assert alias.exists() and outside.exists()
        assert outside.read_text() == "unchanged bytes"
        assert alias.read_text() == "unchanged bytes"
        assert outside.stat().st_file_attributes == original_attributes
        assert alias.stat().st_file_attributes == original_attributes
    finally:
        os.chmod(outside, stat.S_IWRITE)


def test_writable_hardlink_deletes_selected_name_only(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged bytes")
    alias = tmp_path / "selected.txt"
    os.link(outside, alias)
    delete_service.delete_path(str(alias))
    assert not alias.exists()
    assert outside.read_text() == "unchanged bytes"


def _windows_error(code):
    error = PermissionError(13, "access denied")
    error.winerror = code
    return error


@pytest.mark.parametrize("code", [5, 32])
def test_permissions_and_sharing_failures_do_not_chmod_normal_files(tmp_path, monkeypatch, code):
    path = tmp_path / "normal.txt"
    path.write_text("keep")
    error = _windows_error(code)
    remove = Mock(side_effect=error)
    chmod = Mock()
    with monkeypatch.context() as patch:
        patch.setattr(delete_service.os, "remove", remove)
        patch.setattr(delete_service.os, "chmod", chmod)
        with pytest.raises(PermissionError) as caught:
            delete_service.delete_path(str(path))
    assert caught.value is error
    remove.assert_called_once_with(str(path))
    chmod.assert_not_called()
    assert path.read_text() == "keep"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file attributes")
def test_failed_readonly_retry_restores_attribute_and_propagates_error(tmp_path, monkeypatch):
    path = tmp_path / "readonly.txt"
    path.write_text("keep")
    os.chmod(path, stat.S_IREAD)
    native_remove = os.remove
    calls = []
    retry_error = _windows_error(32)

    def remove(name):
        calls.append(name)
        if len(calls) == 1:
            native_remove(name)  # Real WinError 5 from the read-only attribute.
        raise retry_error

    try:
        with monkeypatch.context() as patch:
            patch.setattr(delete_service.os, "remove", remove)
            with pytest.raises(PermissionError) as caught:
                delete_service.delete_path(str(path))
        assert caught.value is retry_error
        assert len(calls) == 2
        assert path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
        assert path.read_text() == "keep"
    finally:
        os.chmod(path, stat.S_IWRITE)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file attributes")
def test_sharing_failure_does_not_clear_readonly_attribute(tmp_path, monkeypatch):
    path = tmp_path / "readonly.txt"
    path.write_text("keep")
    os.chmod(path, stat.S_IREAD)
    try:
        error = _windows_error(32)
        with monkeypatch.context() as patch:
            patch.setattr(delete_service.os, "remove", Mock(side_effect=error))
            chmod = Mock()
            patch.setattr(delete_service.os, "chmod", chmod)
            with pytest.raises(PermissionError) as caught:
                delete_service.delete_path(str(path))
        assert caught.value is error
        chmod.assert_not_called()
        assert path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    finally:
        os.chmod(path, stat.S_IWRITE)


def test_directory_error_does_not_retry_or_chmod(tmp_path, monkeypatch):
    error = _windows_error(5)
    chmod = Mock()
    monkeypatch.setattr(delete_service.os, "chmod", chmod)
    with pytest.raises(PermissionError) as caught:
        delete_service._rmtree_error(os.rmdir, str(tmp_path), (PermissionError, error, None))
    assert caught.value is error
    chmod.assert_not_called()


@pytest.mark.parametrize("kind", ["file", "directory", "broken"])
@pytest.mark.parametrize("nested", [False, True])
def test_symlink_deletes_only_link(tmp_path, kind, nested):
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep")
    target = outside if kind == "directory" else sentinel
    if kind == "broken":
        target = outside / "missing"
    selected = tmp_path / "selected"
    selected.mkdir()
    link = selected / "link"
    try:
        link.symlink_to(target, target_is_directory=kind == "directory")
    except OSError as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")
    delete_service.delete_path(str(selected if nested else link))
    assert not os.path.lexists(link)
    assert sentinel.read_text() == "keep"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction")
@pytest.mark.parametrize("nested", [False, True])
def test_junction_deletes_only_link(tmp_path, nested):
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep")
    selected = tmp_path / "selected"
    selected.mkdir()
    junction = selected / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    try:
        delete_service.delete_path(str(selected if nested else junction))
        assert not os.path.lexists(junction)
        assert sentinel.read_text() == "keep"
    finally:
        if os.path.lexists(junction):
            os.rmdir(junction)
