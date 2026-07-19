import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from typing import Any, Optional

from config import (
    CACHE_DIR,
    CACHE_EVICT_TARGET_BYTES,
    CACHE_HIGH_WATER_BYTES,
)
from storage.app_db import connect
from utils.logger import get_logger

logger = get_logger(__name__)
_CACHE_LOCK = threading.RLock()


def _safe_component(value: str) -> str:
    raw = str(value)
    slug = re.sub(r"[^0-9A-Za-z_-]+", "_", raw).strip("_-") or "cache"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{slug[:48]}_{digest}"


def _cache_key(stock_id: str, data_type: str) -> str:
    raw = f"{stock_id}\0{data_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _db_path() -> str:
    return os.path.join(CACHE_DIR, "app_cache.sqlite3")


def cache_path(stock_id: str, data_type: str) -> str:
    """Return the old portable JSON path for diagnostics/migration only."""
    name = f"{_safe_component(stock_id)}_{_safe_component(data_type)}.json"
    return os.path.join(CACHE_DIR, name)


def cache_get(stock_id: str, data_type: str, max_age_sec: int = 3600) -> Optional[Any]:
    key = _cache_key(stock_id, data_type)
    now = time.time()
    with _CACHE_LOCK:
        try:
            with connect(_db_path()) as connection:
                row = connection.execute(
                    "SELECT payload_json, fetched_at FROM cached_responses WHERE cache_key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    return None
                if now - float(row[1]) > max_age_sec:
                    connection.execute(
                        "DELETE FROM cached_responses WHERE cache_key = ?", (key,)
                    )
                    return None
                connection.execute(
                    "UPDATE cached_responses SET last_accessed_at = ? WHERE cache_key = ?",
                    (now, key),
                )
                return json.loads(row[0])
        except (
            sqlite3.Error,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            OSError,
        ) as exc:
            logger.warning("cache read error for %s/%s: %s", stock_id, data_type, exc)
            return None


def cache_set(stock_id: str, data_type: str, data: Any) -> None:
    try:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        logger.warning(
            "cache serialization error for %s/%s: %s", stock_id, data_type, exc
        )
        return
    now = time.time()
    encoded_size = len(payload.encode("utf-8"))
    with _CACHE_LOCK:
        try:
            with connect(_db_path()) as connection:
                connection.execute(
                    """
                    INSERT INTO cached_responses(
                        cache_key, stock_id, data_type, payload_json, payload_bytes,
                        fetched_at, last_accessed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        stock_id=excluded.stock_id,
                        data_type=excluded.data_type,
                        payload_json=excluded.payload_json,
                        payload_bytes=excluded.payload_bytes,
                        fetched_at=excluded.fetched_at,
                        last_accessed_at=excluded.last_accessed_at
                    """,
                    (
                        _cache_key(stock_id, data_type),
                        str(stock_id),
                        str(data_type),
                        payload,
                        encoded_size,
                        now,
                        now,
                    ),
                )
            cache_enforce_capacity()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("cache write error for %s/%s: %s", stock_id, data_type, exc)


def cache_enforce_capacity() -> int:
    """Evict least-recently-used rows after the 200 MiB high-water mark."""
    deleted = 0
    with _CACHE_LOCK:
        try:
            with connect(_db_path()) as connection:
                total = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(payload_bytes), 0) FROM cached_responses"
                    ).fetchone()[0]
                )
                if total <= CACHE_HIGH_WATER_BYTES:
                    return 0
                rows = connection.execute(
                    "SELECT cache_key, payload_bytes FROM cached_responses "
                    "ORDER BY last_accessed_at ASC"
                ).fetchall()
                for key, size in rows:
                    connection.execute(
                        "DELETE FROM cached_responses WHERE cache_key = ?", (key,)
                    )
                    total -= int(size)
                    deleted += 1
                    if total <= CACHE_EVICT_TARGET_BYTES:
                        break
        except (sqlite3.Error, OSError) as exc:
            logger.warning("cache capacity cleanup failed: %s", exc)
    return deleted


def cache_clear(
    stock_id: Optional[str] = None, data_type: Optional[str] = None
) -> None:
    with _CACHE_LOCK:
        try:
            with connect(_db_path()) as connection:
                if stock_id is not None and data_type is not None:
                    connection.execute(
                        "DELETE FROM cached_responses WHERE cache_key = ?",
                        (_cache_key(stock_id, data_type),),
                    )
                elif stock_id is not None:
                    connection.execute(
                        "DELETE FROM cached_responses WHERE stock_id = ?",
                        (str(stock_id),),
                    )
                elif data_type is not None:
                    connection.execute(
                        "DELETE FROM cached_responses WHERE data_type = ?",
                        (str(data_type),),
                    )
                else:
                    connection.execute("DELETE FROM cached_responses")
        except (sqlite3.Error, OSError) as exc:
            logger.warning("cache clear error: %s", exc)
