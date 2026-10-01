"""Permanent deletion with a Windows read-only retry for single-link files."""

import os
import shutil
import stat
import sys


def _retry_readonly_file(operation, path, error):
    """Retry a failed file deletion once; never relax directory permissions."""
    if (
        sys.platform != "win32"
        or getattr(error, "winerror", None) != 5
        or operation not in (os.remove, os.unlink)
    ):
        raise error
    try:
        original = os.lstat(path)
    except OSError:
        raise error
    if not (
        stat.S_ISREG(original.st_mode)
        and original.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
        and original.st_nlink == 1
    ):
        # Attributes belong to the file, not its name. Clearing read-only on
        # a hardlink would also modify aliases outside the selected tree.
        raise error

    os.chmod(path, original.st_mode | stat.S_IWRITE)
    try:
        operation(path)
    except OSError:
        # An ACL or open handle can still prevent deletion. Restore the user's
        # read-only bit on the same file, and propagate the retry error.
        try:
            current = os.lstat(path)
            if (
                stat.S_ISREG(current.st_mode)
                and (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino)
            ):
                os.chmod(path, original.st_mode)
        except OSError:
            pass
        raise


def _rmtree_error(operation, path, exc_info):
    # onerror is available on every supported Python version (3.10+).
    _retry_readonly_file(operation, path, exc_info[1])


def delete_path(path):
    """Delete one selected entry, without traversing symlink/junction targets."""
    entry = os.lstat(path)
    if stat.S_ISLNK(entry.st_mode):
        os.unlink(path)
    elif getattr(entry, "st_reparse_tag", None) == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003):
        os.rmdir(path)
    elif stat.S_ISDIR(entry.st_mode):
        # Python 3.8+ also avoids descending into nested Windows junctions.
        shutil.rmtree(path, onerror=_rmtree_error)
    else:
        try:
            os.remove(path)
        except OSError as error:
            _retry_readonly_file(os.remove, path, error)
