import json
from pathlib import Path

import pandas as pd

from models.data_value import DataValue
from services.market_snapshot import MarketDataSnapshot
from stock import data as stock_data
from stock.yf_errors import YFINANCE_EXCEPTIONS


ROOT = Path(__file__).resolve().parents[1]


def test_emerging_market_uses_yahoo_otc_suffix():
    assert stock_data._suffix("興櫃") == ".TWO"  # noqa: SLF001
    assert stock_data._suffix("上櫃") == ".TWO"  # noqa: SLF001
    assert stock_data._suffix("上市") == ".TW"  # noqa: SLF001


class _CountingTicker:
    def __init__(self, symbol, calls):
        self.symbol = symbol
        self.calls = calls

    @property
    def info(self):
        self.calls["info"] += 1
        return {"currentPrice": 100.0}

    def history(self, **kwargs):
        self.calls["history"] += 1
        index = pd.date_range("2025-01-01", periods=370, freq="D")
        return pd.DataFrame(
            {
                "Open": 100.0,
                "High": 101.0,
                "Low": 99.0,
                "Close": 100.0,
                "Volume": 1_000,
                "Dividends": 0.0,
            },
            index=index,
        )

    @property
    def quarterly_income_stmt(self):
        self.calls["quarterly_income_stmt"] += 1
        return pd.DataFrame()

    @property
    def balance_sheet(self):
        self.calls["balance_sheet"] += 1
        return pd.DataFrame()

    @property
    def financials(self):
        self.calls["financials"] += 1
        return pd.DataFrame()


def test_data_value_serializes_source_date_unit_and_status():
    item = DataValue(
        value=100.5,
        source="TWSE OpenAPI",
        observed_at="2026-07-17",
        fetched_at="2026-07-18T00:00:00+00:00",
        unit="TWD",
        status="official",
    )
    payload = item.to_dict()
    assert payload == {
        "value": 100.5,
        "source": "TWSE OpenAPI",
        "observed_at": "2026-07-17",
        "fetched_at": "2026-07-18T00:00:00+00:00",
        "unit": "TWD",
        "currency": None,
        "status": "official",
        "note": "",
    }


def test_market_snapshot_caches_each_yahoo_resource_once(monkeypatch):
    calls = {
        "ticker": 0,
        "info": 0,
        "history": 0,
        "quarterly_income_stmt": 0,
        "balance_sheet": 0,
        "financials": 0,
    }

    def factory(symbol):
        calls["ticker"] += 1
        return _CountingTicker(symbol, calls)

    monkeypatch.setattr("services.market_snapshot.yf.Ticker", factory)
    snapshot = MarketDataSnapshot("2330", "上市")
    assert snapshot.info() == snapshot.info()
    assert snapshot.history(period="1y").equals(snapshot.history(period="1y"))
    assert snapshot.quarterly_income_stmt().empty
    assert snapshot.quarterly_income_stmt().empty
    assert snapshot.balance_sheet().empty
    assert snapshot.balance_sheet().empty
    assert snapshot.financials().empty
    assert snapshot.financials().empty
    assert calls == {
        "ticker": 1,
        "info": 1,
        "history": 1,
        "quarterly_income_stmt": 1,
        "balance_sheet": 1,
        "financials": 1,
    }


def test_price_periods_are_sliced_from_one_history_fetch(monkeypatch):
    calls = {"history": 0}

    class Snapshot:
        def info(self):
            return {"currentPrice": 100.0}

        def history(self, **kwargs):
            calls["history"] += 1
            index = pd.date_range("2025-01-01", periods=370, freq="D")
            return pd.DataFrame(
                {
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.0,
                    "Volume": 1_000,
                },
                index=index,
            )

    monkeypatch.setattr(
        stock_data, "_plot_price_chart", lambda *args, **kwargs: "chart.png"
    )
    result, info = stock_data.get_price_data("2330", snapshot=Snapshot())
    assert calls["history"] == 1
    assert info["currentPrice"] == 100.0
    assert set(result) == {"3m", "6m", "1y"}
    assert len(result["3m"]["df"]) < len(result["6m"]["df"]) < len(result["1y"]["df"])


def test_security_registry_has_required_provenance_fields():
    payload = json.loads(
        (ROOT / "stock" / "official_stock_snapshot.json").read_text(encoding="utf-8")
    )
    required = {
        "asset_type",
        "market",
        "currency",
        "listing_date",
        "official_source",
        "source_updated_at",
    }
    assert payload["schema_version"] >= 3
    assert len(payload["stocks"]) >= 2_300
    for stock_id, record in payload["stocks"].items():
        assert required <= set(record), stock_id
        assert record["official_source"], stock_id
        assert record["source_updated_at"], stock_id


def test_programming_errors_are_not_misreported_as_yahoo_network_errors():
    for exception_type in (ValueError, KeyError, TypeError, AttributeError, IndexError):
        assert exception_type not in YFINANCE_EXCEPTIONS
