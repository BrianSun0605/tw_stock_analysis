from pathlib import Path

import peewee
import yfinance.cache as yf_cache

import config
import main
from stock.yf_errors import YFINANCE_EXCEPTIONS


def test_yfinance_cache_is_project_local_and_writable():
    cache_dir = Path(config.YFINANCE_CACHE_DIR)

    assert cache_dir.parent == Path(config.CACHE_DIR)
    assert cache_dir.is_dir()
    assert Path(yf_cache._CookieDBManager._cache_dir) == cache_dir

    probe = cache_dir / ".write-test"
    probe.write_text("ok", encoding="utf-8")
    try:
        assert probe.read_text(encoding="utf-8") == "ok"
    finally:
        probe.unlink(missing_ok=True)


def test_yfinance_cache_database_errors_are_recoverable():
    assert peewee.OperationalError in YFINANCE_EXCEPTIONS


def test_cli_returns_failure_exit_code_when_analysis_fails(monkeypatch):
    monkeypatch.setattr(main, "batch_mode", lambda _query: None)

    assert main.cli(["0050"]) == 1


def test_cli_returns_success_exit_code_when_report_exists(monkeypatch):
    monkeypatch.setattr(main, "batch_mode", lambda _query: "output/0050_report.pdf")

    assert main.cli(["0050"]) == 0
