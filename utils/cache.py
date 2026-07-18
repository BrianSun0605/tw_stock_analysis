import hashlib
import json
import os
import re
import tempfile
import threading
import time
from typing import Any, Optional

from config import CACHE_DIR, CACHE_MAX_ITEMS
from utils.logger import get_logger

logger = get_logger(__name__)
_CACHE_LOCK = threading.RLock()


def _safe_component(value: str) -> str:
    raw = str(value)
    slug = re.sub(r"[^0-9A-Za-z_-]+", "_", raw).strip("_-") or "cache"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{slug[:48]}_{digest}"


def cache_path(stock_id: str, data_type: str) -> str:
    name = f"{_safe_component(stock_id)}_{_safe_component(data_type)}.json"
    return os.path.join(CACHE_DIR, name)


def _cache_evict_lru() -> None:
    if not os.path.isdir(CACHE_DIR):
        return
    files = [
        os.path.join(CACHE_DIR, name)
        for name in os.listdir(CACHE_DIR)
        if name.endswith(".json") and os.path.isfile(os.path.join(CACHE_DIR, name))
    ]
    if len(files) <= CACHE_MAX_ITEMS:
        return
    files.sort(key=os.path.getmtime)
    for path in files[:len(files) - CACHE_MAX_ITEMS]:
        try:
            os.remove(path)
            logger.debug("evicted cache: %s", os.path.basename(path))
        except OSError as exc:
            logger.debug("cache eviction skipped for %s: %s", path, exc)


def cache_get(stock_id: str, data_type: str, max_age_sec: int = 3600) -> Optional[Any]:
    path = cache_path(stock_id, data_type)
    with _CACHE_LOCK:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if time.time() - float(payload.get("_ts", 0)) > max_age_sec:
                return None
            return payload.get("_data")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError) as exc:
            logger.warning("cache read error for %s/%s: %s", stock_id, data_type, exc)
            return None


def cache_set(stock_id: str, data_type: str, data: Any) -> None:
    path = cache_path(stock_id, data_type)
    temp_path = None
    with _CACHE_LOCK:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=CACHE_DIR,
                prefix=".cache-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = handle.name
                json.dump({"_ts": time.time(), "_data": data}, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            _cache_evict_lru()
        except (OSError, TypeError) as exc:
            logger.warning("cache write error for %s/%s: %s", stock_id, data_type, exc)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


def cache_clear(stock_id: Optional[str] = None, data_type: Optional[str] = None) -> None:
    with _CACHE_LOCK:
        if not os.path.isdir(CACHE_DIR):
            return
        if stock_id and data_type:
            targets = [cache_path(stock_id, data_type)]
        elif stock_id:
            prefix = _safe_component(stock_id) + "_"
            targets = [
                os.path.join(CACHE_DIR, name)
                for name in os.listdir(CACHE_DIR)
                if name.startswith(prefix) and name.endswith(".json")
            ]
        else:
            targets = [
                os.path.join(CACHE_DIR, name)
                for name in os.listdir(CACHE_DIR)
                if name.endswith(".json")
            ]
        for path in targets:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError as exc:
                logger.warning("cache clear error for %s: %s", path, exc)
