"""Bounded subprocess queries for properties, without Qt or GUI-thread reads."""
import json
import os
from pathlib import Path
from core.file_attributes import is_cloud_placeholder

MAX_ENTRIES = 100_000

def _folder_details(folder_path, max_files=MAX_ENTRIES):
    files_count = dirs_count = total = 0
    partial = False
    def inaccessible(error):
        nonlocal partial
        partial = True
    for root, dirs, files in os.walk(folder_path, followlinks=False, onerror=inaccessible):
        dirs_count += len(dirs)
        traversable = []
        for name in dirs:
            path = os.path.join(root, name)
            if (os.path.islink(path) or getattr(os.path, "isjunction", lambda p: False)(path)
                    or is_cloud_placeholder(path)):
                partial = True
            else:
                traversable.append(name)
        dirs[:] = traversable
        for name in files:
            files_count += 1
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                partial = True
            if files_count + dirs_count >= max_files:
                partial = True
                break
        if files_count + dirs_count >= max_files:
            partial = True
            break
    return {"files": files_count, "folders": dirs_count, "bytes": total, "partial": partial}

def calculate_folder_stats(folder_path, max_files=MAX_ENTRIES):
    result = _folder_details(folder_path, max_files)
    return result["files"], result["folders"], result["bytes"]

def query_details(kind, target):
    if is_cloud_placeholder(target):
        raise ValueError("Nur online verfügbar. Datei zuerst lokal verfügbar machen.")
    if kind == "folder":
        if not os.path.isdir(target):
            raise NotADirectoryError(target)
        return _folder_details(target)
    if kind == "text":
        # Bound the read even if the file grows after the metadata check.
        with open(target, "rb") as handle:
            raw = handle.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("Datei > 5 MB")
        text = raw.decode("utf-8", errors="ignore")
        return {"lines": len(text.splitlines()), "words": len(text.split()), "chars": len(text)}
    raise ValueError("Unknown properties query")

def details_query_main(kind, target, output):
    try:
        payload = {"result": query_details(kind, target)}
        code = 0
    except Exception as exc:
        payload = {"error": str(exc)}
        code = 1
    Path(output).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return code
