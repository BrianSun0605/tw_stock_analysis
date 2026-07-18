import json
import os
import time
from typing import Any, Optional

from config import CACHE_DIR, CACHE_MAX_ITEMS
from utils.logger import get_logger

logger = get_logger(__name__)


def cache_path(stock_id: str, data_type: str) -> str:
    name = f"{stock_id}_{data_type}.json"
    return os.path.join(CACHE_DIR, name)


def _cache_evict_lru():
    import glob
    pattern = os.path.join(CACHE_DIR, "*.json")
    files = glob.glob(pattern)
    if len(files) <= CACHE_MAX_ITEMS:
        return
    files.sort(key=lambda p: os.path.getmtime(p))
    excess = len(files) - CACHE_MAX_ITEMS
    for f in files[:excess]:
        try:
            os.remove(f)
            logger.debug("evicted cache: %s", os.path.basename(f))
        except OSError:
            pass


def cache_get(stock_id: str, data_type: str, max_age_sec: int = 3600) -> Optional[Any]:
    path = cache_path(stock_id, data_type)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("_ts", 0) > max_age_sec:
            return None
        return data.get("_data")
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning("cache read error for %s/%s: %s", stock_id, data_type, e)
        return None


def cache_set(stock_id: str, data_type: str, data: Any) -> None:
    path = cache_path(stock_id, data_type)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_ts": time.time(), "_data": data}, f, ensure_ascii=False)
        _cache_evict_lru()
    except (OSError, TypeError) as e:
        logger.warning("cache write error for %s/%s: %s", stock_id, data_type, e)


def cache_clear(stock_id=None, data_type=None):
    if stock_id and data_type:
        path = cache_path(stock_id, data_type)
        if os.path.exists(path):
            os.remove(path)
    elif stock_id:
        for fname in os.listdir(CACHE_DIR):
            if fname.startswith(stock_id + "_"):
                os.remove(os.path.join(CACHE_DIR, fname))
    else:
        for fname in os.listdir(CACHE_DIR):
            if fname != "charts":
                path = os.path.join(CACHE_DIR, fname)
                if os.path.isfile(path):
                    os.remove(path)
