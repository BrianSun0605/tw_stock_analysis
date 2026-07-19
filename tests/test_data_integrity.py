import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from news.base_provider import BaseNewsProvider
from stock import data as stock_data
from stock import normalizer
from utils import cache


class _Ticker:
    def __init__(self, info):
        self.info = info


def test_yfinance_annual_revenue_is_not_fabricated_as_monthly(monkeypatch):
    monkeypatch.setattr(
        stock_data.yf, "Ticker", lambda _: _Ticker({"totalRevenue": 1_200_000})
    )
    assert stock_data._fetch_revenue_yfinance("2330", "上市") == []


def test_yfinance_quarterly_eps_uses_quarter_columns(monkeypatch):
    frame = pd.DataFrame(
        {pd.Timestamp("2025-03-31"): [13.95]},
        index=["Diluted EPS"],
    )
    ticker = _Ticker({})
    ticker.quarterly_income_stmt = frame
    monkeypatch.setattr(stock_data.yf, "Ticker", lambda _: ticker)
    result = stock_data._fetch_eps_yfinance("2330", "上市")
    assert len(result) == 1
    assert {
        key: result[0][key]
        for key in ("year", "quarter", "eps", "label", "source", "unit", "status")
    } == {
        "year": 2025,
        "quarter": 1,
        "eps": 13.95,
        "label": "Q1 2025",
        "source": "Yahoo Finance quarterly_income_stmt",
        "unit": "TWD_per_share",
        "status": "fallback",
    }
    assert result[0]["data_value"]["observed_at"] == "2025-03-31"


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
    assert ":" not in path[len("cache") :]
    assert ".." not in path
    cache.cache_set("peers:半導體/../x", "peers", {"ok": True})
    try:
        assert cache.cache_get("peers:半導體/../x", "peers") == {"ok": True}
    finally:
        cache.cache_clear("peers:半導體/../x", "peers")


def test_official_snapshot_contains_core_etfs_and_asset_types():
    for stock_id, expected_name in {
        "0050": "元大台灣50",
        "006208": "富邦台50",
        "00878": "國泰永續高股息",
    }.items():
        result = normalizer.normalize(stock_id)
        assert result["stock_id"] == stock_id
        assert result["name"] == expected_name
        assert result["asset_type"] == "etf"


def test_official_snapshot_covers_supported_markets_and_product_types():
    snapshot_path = Path(normalizer.__file__).with_name("official_stock_snapshot.json")
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    stocks = payload["stocks"]

    assert payload["schema_version"] >= 4
    assert len(stocks) >= 2_700
    minimums = {
        "listed": 800,
        "otc": 700,
        "emerging": 250,
        "listed_funds": 200,
        "otc_funds": 80,
        "listed_etns": 5,
        "listed_supplemental": 20,
        "otc_supplemental": 5,
    }
    assert all(
        payload["source_counts"].get(name, 0) >= minimum
        for name, minimum in minimums.items()
    )
    expected = {
        "1260": ("興櫃", "stock"),
        "020029": ("上市", "etn"),
        "020001": ("上櫃", "etn"),
        "2881A": ("上市", "preferred_stock"),
        "8349A": ("上櫃", "preferred_stock"),
        "01001T": ("上市", "reit"),
        "009825": ("上櫃", "etf"),
    }
    for stock_id, (market, asset_type) in expected.items():
        result = normalizer.normalize(stock_id.lower())
        assert result["stock_id"] == stock_id
        assert result["market"] == market
        assert result["asset_type"] == asset_type
        assert result["official_source"].startswith("https://")
        assert result["source_updated_at"]

    assert "700019" not in stocks
    assert not any(item.get("asset_type") == "warrant" for item in stocks.values())


def test_default_etn_observation_date_uses_taipei_calendar_date():
    payload = {
        "domestic": {
            "stat": "ok",
            "fields": ["證券代號", "證券簡稱"],
            "data": [["020029", "元大ESG高股息N"]],
        }
    }
    result = normalizer._parse_twse_etn_payloads(payload)  # noqa: SLF001
    expected = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    assert result["020029"]["source_updated_at"] == expected


def test_unknown_numeric_security_code_is_rejected():
    assert normalizer.normalize("99999999")["stock_id"] == ""
    assert normalizer.search_stock("99999999") == []
