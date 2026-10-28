from __future__ import annotations

import os
from pathlib import Path

from .config import STORAGE_DIR


LOG_DIR = STORAGE_DIR / "logs"
RUNTIME_STDOUT_LOG = LOG_DIR / "hub-runtime.out.log"
RUNTIME_STDERR_LOG = LOG_DIR / "hub-runtime.err.log"
MAX_RUNTIME_LOG_BYTES = 10 * 1024 * 1024
RUNTIME_LOG_ARCHIVES = 3
APPLY_FIX_LOG_PATTERN = "apply-fix-*.log"
MAX_APPLY_FIX_LOGS = 50


def _archive(path: Path, number: int) -> Path:
    return path.with_name(f"{path.name}.{number}")


def rotate_stream(fd: int, path: Path, max_bytes: int = MAX_RUNTIME_LOG_BYTES, archives: int = RUNTIME_LOG_ARCHIVES) -> bool:
    """Rotate the log file behind an open descriptor once it exceeds max_bytes.

    Only the process that writes the descriptor may call this: the current file
    becomes archive 1 and a fresh file at path replaces the descriptor via dup2,
    so no write is lost and launchd keeps its original StandardOutPath.
    """
    try:
        stream, target = os.fstat(fd), os.stat(path)
    except OSError:
        return False
    if (stream.st_dev, stream.st_ino) != (target.st_dev, target.st_ino) or stream.st_size <= max_bytes:
        return False
    _archive(path, archives).unlink(missing_ok=True)
    for number in range(archives - 1, 0, -1):
        if _archive(path, number).exists():
            _archive(path, number).replace(_archive(path, number + 1))
    path.replace(_archive(path, 1))
    fresh = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.dup2(fresh, fd)
    finally:
        os.close(fresh)
    return True
