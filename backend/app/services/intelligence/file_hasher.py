"""Per-file hashing utilities for the Repository Intelligence layer.

Provides SHA-256 hashing of file content along with size and last-modified
metadata so that future incremental rebuilds can detect changed files without
re-parsing everything.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from app.services.intelligence.models import FileHashRecord

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hash_file(path: Path, language: str = "unknown") -> Optional[FileHashRecord]:
    """Compute SHA-256 + mtime + size for a file.

    Returns ``None`` if the file cannot be read (permission error, gone, etc.).

    Parameters
    ----------
    path:
        Absolute or repository-relative path to the file.
    language:
        Language label to embed in the record (for filtering later).
    """
    try:
        stat = path.stat()
        content = path.read_bytes()
    except OSError:
        return None

    digest = hashlib.sha256(content).hexdigest()
    return FileHashRecord(
        path=path.as_posix(),          # store as-is; caller normalises to relative
        sha256=digest,
        size_bytes=stat.st_size,
        last_modified=stat.st_mtime,
        language=language,
    )


def hash_source(source: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 encoded source string."""
    return hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()


def hash_dir(root: Path, skip_dirs: set, skip_exts: set) -> str:
    """Compute a deterministic SHA-256 of an entire directory tree.

    Hashes (relative_path + size) for every non-skipped file.
    The result changes when any file is added, removed, or resized.

    Parameters
    ----------
    root:
        Absolute path to the repository root.
    skip_dirs:
        Set of directory names to prune during ``os.walk``.
    skip_exts:
        Set of file extensions to exclude.
    """
    hasher = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if full.suffix.lower() in skip_exts:
                continue
            rel = full.relative_to(root).as_posix()
            try:
                size = full.stat().st_size
            except OSError:
                size = 0
            hasher.update(rel.encode())
            hasher.update(str(size).encode())
    return hasher.hexdigest()
