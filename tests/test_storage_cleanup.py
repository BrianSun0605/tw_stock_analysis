import os
import shutil
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

from storage import cleanup
from utils import cache


ROOT = Path(__file__).resolve().parents[1]


def _test_dir(label):
    return ROOT / "output" / f".{label}-{uuid.uuid4().hex}"


def test_expired_sqlite_cache_is_deleted_and_hit_updates_last_access(monkeypatch):
    root = _test_dir("cache-db")
    monkeypatch.setattr(cache, "CACHE_DIR", str(root))
    try:
        cache.cache_set("2330", "test", {"ok": True})
        db_path = root / "app_cache.sqlite3"
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                "UPDATE cached_responses SET fetched_at = ?, last_accessed_at = ?",
                (time.time() - 100, 1),
            )
            connection.commit()
        assert cache.cache_get("2330", "test", max_age_sec=200) == {"ok": True}
        with closing(sqlite3.connect(db_path)) as connection:
            last_access = connection.execute(
                "SELECT last_accessed_at FROM cached_responses"
            ).fetchone()[0]
        assert last_access > 1

        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                "UPDATE cached_responses SET fetched_at = ?", (time.time() - 300,)
            )
            connection.commit()
        assert cache.cache_get("2330", "test", max_age_sec=200) is None
        with closing(sqlite3.connect(db_path)) as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM cached_responses").fetchone()[
                    0
                ]
                == 0
            )
    finally:
        if root.is_dir():
            shutil.rmtree(root)


def test_cache_capacity_uses_lru_high_and_target_watermarks(monkeypatch):
    root = _test_dir("cache-capacity")
    monkeypatch.setattr(cache, "CACHE_DIR", str(root))
    monkeypatch.setattr(cache, "CACHE_HIGH_WATER_BYTES", 180)
    monkeypatch.setattr(cache, "CACHE_EVICT_TARGET_BYTES", 80)
    try:
        cache.cache_set("old", "test", "x" * 70)
        time.sleep(0.01)
        cache.cache_set("middle", "test", "y" * 70)
        time.sleep(0.01)
        cache.cache_set("new", "test", "z" * 70)
        assert cache.cache_get("old", "test") is None
        assert cache.cache_get("new", "test") == "z" * 70
    finally:
        if root.is_dir():
            shutil.rmtree(root)


def test_output_cleanup_deletes_each_old_file_but_keeps_fresh_file(monkeypatch):
    root = _test_dir("output-cleanup")
    root.mkdir(parents=True)
    old_file = root / "old.pdf"
    fresh_file = root / "fresh.pdf"
    old_file.write_bytes(b"old")
    fresh_file.write_bytes(b"fresh")
    now = time.time()
    os.utime(old_file, (now - 4 * 86400, now - 4 * 86400))
    monkeypatch.setattr(cleanup, "OUTPUT_DIR", str(root))
    monkeypatch.setattr(cleanup, "OUTPUT_TTL_SECONDS", 3 * 86400)
    monkeypatch.setattr(cleanup, "OUTPUT_MAX_BYTES", 1024)
    try:
        assert cleanup.enforce_output_policy(now=now) == 1
        assert not old_file.exists()
        assert fresh_file.exists()
    finally:
        if root.is_dir():
            shutil.rmtree(root)


def test_task_cleanup_rejects_unscoped_path_and_removes_only_exact_task(monkeypatch):
    root = _test_dir("tasks")
    task_id = uuid.uuid4().hex
    task_dir = root / task_id / "charts"
    task_dir.mkdir(parents=True)
    (task_dir / "chart.png").write_bytes(b"png")
    sibling = root / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(cleanup, "TASK_ARTIFACT_DIR", str(root))
    try:
        assert cleanup.remove_task_artifacts("../") == 0
        assert cleanup.remove_task_artifacts(task_id) == 1
        assert not (root / task_id).exists()
        assert sibling.exists()
    finally:
        if root.is_dir():
            shutil.rmtree(root)
