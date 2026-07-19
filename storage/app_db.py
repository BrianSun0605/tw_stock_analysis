"""Small SQLite store for structured cache metadata and application state."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator


SCHEMA_VERSION = 1


@contextmanager
def connect(path: str) -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        _migrate(connection)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS securities (
            security_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_updated_at TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS source_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL,
            attempted_at REAL NOT NULL,
            status TEXT NOT NULL,
            record_count INTEGER,
            content_hash TEXT,
            message TEXT
        );
        CREATE TABLE IF NOT EXISTS cached_responses (
            cache_key TEXT PRIMARY KEY,
            stock_id TEXT NOT NULL,
            data_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_bytes INTEGER NOT NULL,
            fetched_at REAL NOT NULL,
            last_accessed_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cached_responses_access
            ON cached_responses(last_accessed_at);
        CREATE INDEX IF NOT EXISTS idx_cached_responses_stock
            ON cached_responses(stock_id, data_type);
        """
    )
    row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        connection.execute(
            "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
        )
    elif int(row[0]) != SCHEMA_VERSION:
        raise RuntimeError(
            f"unsupported app database schema: {row[0]} (expected {SCHEMA_VERSION})"
        )
