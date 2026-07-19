"""Bounded, path-safe cleanup for runtime files."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import List

from config import (
    CHART_DIR,
    CLEANUP_INTERVAL_SECONDS,
    LOG_DIR,
    LOG_MAX_BYTES,
    LOG_TTL_SECONDS,
    OUTPUT_DIR,
    OUTPUT_MAX_BYTES,
    OUTPUT_TTL_SECONDS,
    TASK_ARTIFACT_DIR,
    TASK_ARTIFACT_TTL_SECONDS,
)
from utils.cache import cache_enforce_capacity
from utils.logger import get_logger

logger = get_logger(__name__)
_LOCK = threading.RLock()
_LAST_CLEANUP_AT = 0.0
_TASK_ID = re.compile(r"^[a-f0-9]{32}$")


def _files(root: str) -> List[Path]:
    base = Path(root).resolve()
    if not base.is_dir():
        return []
    result = []
    for path in base.rglob("*"):
        try:
            resolved = path.resolve()
            if (
                path.is_file()
                and not path.is_symlink()
                and resolved.is_relative_to(base)
            ):
                result.append(path)
        except (OSError, RuntimeError):
            continue
    return result


def _remove_file(path: Path, root: str) -> bool:
    try:
        base = Path(root).resolve()
        resolved = path.resolve()
        if not resolved.is_relative_to(base) or path.is_symlink():
            return False
        path.unlink(missing_ok=True)
        return True
    except (OSError, RuntimeError):
        return False


def _remove_empty_dirs(root: str) -> None:
    base = Path(root).resolve()
    if not base.is_dir():
        return
    directories = sorted(
        (path for path in base.rglob("*") if path.is_dir() and not path.is_symlink()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for path in directories:
        try:
            if path.resolve().is_relative_to(base):
                path.rmdir()
        except OSError:
            pass


def remove_expired_files(root: str, ttl_seconds: int, now: float | None = None) -> int:
    cutoff = (time.time() if now is None else now) - ttl_seconds
    deleted = 0
    for path in _files(root):
        try:
            expired = path.stat().st_mtime < cutoff
        except OSError:
            continue
        if expired and _remove_file(path, root):
            deleted += 1
    _remove_empty_dirs(root)
    return deleted


def enforce_directory_capacity(root: str, maximum_bytes: int) -> int:
    files = _files(root)
    entries = []
    total = 0
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        entries.append((stat.st_mtime, stat.st_size, path))
        total += stat.st_size
    if total <= maximum_bytes:
        return 0
    deleted = 0
    for _modified, size, path in sorted(entries):
        if _remove_file(path, root):
            total -= size
            deleted += 1
        if total <= maximum_bytes:
            break
    _remove_empty_dirs(root)
    return deleted


def enforce_output_policy(now: float | None = None) -> int:
    deleted = remove_expired_files(OUTPUT_DIR, OUTPUT_TTL_SECONDS, now=now)
    return deleted + enforce_directory_capacity(OUTPUT_DIR, OUTPUT_MAX_BYTES)


def remove_task_artifacts(task_id: str) -> int:
    if not _TASK_ID.fullmatch(str(task_id)):
        return 0
    base = Path(TASK_ARTIFACT_DIR).resolve()
    target = (base / task_id).resolve()
    if not target.is_relative_to(base) or not target.is_dir():
        return 0
    deleted = 0
    for path in _files(str(target)):
        if _remove_file(path, str(target)):
            deleted += 1
    _remove_empty_dirs(str(target))
    try:
        target.rmdir()
    except OSError:
        pass
    return deleted


def cleanup_runtime_storage(*, force: bool = False, now: float | None = None) -> dict:
    global _LAST_CLEANUP_AT
    current = time.time() if now is None else now
    with _LOCK:
        if not force and current - _LAST_CLEANUP_AT < CLEANUP_INTERVAL_SECONDS:
            return {"skipped": True}
        result = {
            "skipped": False,
            "output_deleted": enforce_output_policy(now=current),
            "task_artifacts_deleted": remove_expired_files(
                TASK_ARTIFACT_DIR, TASK_ARTIFACT_TTL_SECONDS, now=current
            ),
            "legacy_charts_deleted": remove_expired_files(
                CHART_DIR, TASK_ARTIFACT_TTL_SECONDS, now=current
            ),
            "logs_deleted": (
                remove_expired_files(LOG_DIR, LOG_TTL_SECONDS, now=current)
                + enforce_directory_capacity(LOG_DIR, LOG_MAX_BYTES)
            ),
            "cache_rows_deleted": cache_enforce_capacity(),
        }
        _LAST_CLEANUP_AT = current
        logger.info("runtime cleanup: %s", result)
        return result
