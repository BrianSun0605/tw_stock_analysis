import pandas as pd

from news.base_provider import BaseNewsProvider
from stock import data as stock_data
from utils import cache


class _Ticker:
    def __init__(self, info):
        self.info = info


def test_yfinance_annual_revenue_is_not_fabricated_as_monthly(monkeypatch):
    monkeypatch.setattr(stock_data.yf, "Ticker", lambda _: _Ticker({"totalRevenue": 1_200_000}))
    assert stock_data._fetch_revenue_yfinance("2330", "上市") == []


def test_yfinance_quarterly_eps_uses_quarter_columns(monkeypatch):
    frame = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [13.95]},
        index=["Diluted EPS"],
    )
    ticker = _Ticker({})
    ticker.quarterly_income_stmt = frame
    monkeypatch.setattr(stock_data.yf, "Ticker", lambda _: ticker)
    assert stock_data._fetch_eps_yfinance("2330", "上市") == [{
        "year": 2025,
        "quarter": 1,
        "eps": 13.95,
        "label": "Q1 2025",
        "source": "Yahoo Finance quarterly_income_stmt",
    }]


def test_yfinance_quarterly_eps_can_derive_same_quarter_ratio(monkeypatch):
    frame = pd.DataFrame(
        {pd.Timestamp("2025-09-30"): [400.0, 20.0]},
        index=["Net Income Common Stockholders", "Diluted Average Shares"],
    )
    ticker = _Ticker({})
    ticker.quarterly_income_stmt = frame
    monkeypatch.setattr(stock_data.yf, "Ticker", lambda _: ticker)
    assert stock_data._fetch_eps_yfinance("2330", "上市")[0]["eps"] == 20.0


def test_news_date_normalizes_rfc822():
    provider = BaseNewsProvider()
    assert provider._normalize_date("Fri, 18 Jul 2025 08:30:00 GMT") == "2025-07-18"


def test_cache_filename_is_portable_and_cannot_escape_directory(monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", "cache")
    path = cache.cache_path("peers:半導體/../x", "peers")
    assert path.startswith("cache")
    assert ":" not in path[len("cache"):]
    assert ".." not in path
    cache.cache_set("peers:半導體/../x", "peers", {"ok": True})
    try:
        assert cache.cache_get("peers:半導體/../x", "peers") == {"ok": True}
    finally:
        cache.cache_clear("peers:半導體/../x", "peers")
