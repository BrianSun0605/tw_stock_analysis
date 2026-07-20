from datetime import date

from stock import data as stock_data
from stock import finmind
from stock.official_financials import OfficialNetworkError


class _Response:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        return None

    def json(self):
        return {"status": 200, "msg": "success", "data": self._rows}


def _monthly_rows():
    rows = []
    for ordinal in range(24):
        year = 2024 + (ordinal // 12)
        month = ordinal % 12 + 1
        rows.append(
            {
                "revenue_year": year,
                "revenue_month": month,
                "revenue": 1_000_000 + ordinal * 10_000,
            }
        )
    return rows


def _eps_rows():
    rows = []
    for ordinal in range(8):
        year = 2024 + ordinal // 4
        month = (ordinal % 4 + 1) * 3
        rows.append(
            {
                "date": date(year, month, 28).isoformat(),
                "type": "EPS",
                "value": float(ordinal + 1),
            }
        )
    return rows


def test_finmind_monthly_revenue_normalizes_twd_to_thousands(monkeypatch):
    monkeypatch.setattr(finmind, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(finmind, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        finmind.requests,
        "get",
        lambda *_args, **_kwargs: _Response(_monthly_rows()),
    )

    records = finmind.get_monthly_revenue_history("2330", months=24)

    assert len(records) == 24
    assert records[0]["revenue"] == 1000.0
    assert records[-1]["status"] == "fallback"
    assert records[-1]["data_value"]["unit"] == "TWD_thousand"
    assert records[-1]["yoy"] is not None


def test_finmind_quarterly_eps_keeps_quarterly_dates_and_provenance(monkeypatch):
    monkeypatch.setattr(finmind, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(finmind, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        finmind.requests,
        "get",
        lambda *_args, **_kwargs: _Response(_eps_rows()),
    )

    records = finmind.get_quarterly_eps("2330")

    assert [(item["year"], item["quarter"]) for item in records] == [
        (2024, 1),
        (2024, 2),
        (2024, 3),
        (2024, 4),
        (2025, 1),
        (2025, 2),
        (2025, 3),
        (2025, 4),
    ]
    assert records[-1]["eps"] == 8.0
    assert records[-1]["data_value"]["status"] == "fallback"


def test_revenue_data_uses_finmind_when_official_source_is_unavailable(monkeypatch):
    fallback = [
        {
            "year": 2024 + ordinal // 12,
            "month": ordinal % 12 + 1,
            "revenue": 1000 + ordinal,
            "mom": 1.0,
            "yoy": 2.0,
            "source": "FinMind TaiwanStockMonthRevenue (fallback)",
            "status": "fallback",
        }
        for ordinal in range(24)
    ]
    monkeypatch.setattr(
        stock_data,
        "get_official_revenue",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OfficialNetworkError("offline")
        ),
    )
    monkeypatch.setattr(
        stock_data,
        "get_finmind_monthly_revenue_history",
        lambda *_args, **_kwargs: fallback,
    )
    monkeypatch.setattr(
        stock_data, "_plot_revenue_chart", lambda *_args, **_kwargs: None
    )

    records, chart = stock_data.get_revenue_data("2330", market="上市")

    assert records == fallback
    assert chart is None


def test_eps_data_fills_missing_yahoo_quarters_from_finmind(monkeypatch):
    fallback = [
        {
            "year": 2024 + ordinal // 4,
            "quarter": ordinal % 4 + 1,
            "eps": float(ordinal + 1),
            "label": f"Q{ordinal % 4 + 1} {2024 + ordinal // 4}",
            "source": "FinMind TaiwanStockFinancialStatements (fallback)",
            "status": "fallback",
        }
        for ordinal in range(8)
    ]
    monkeypatch.setattr(stock_data, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stock_data, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(stock_data, "_fetch_eps_yfinance", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        stock_data, "get_finmind_quarterly_eps", lambda *_args: fallback
    )
    monkeypatch.setattr(stock_data, "_plot_eps_chart", lambda *_args, **_kwargs: None)

    records, chart = stock_data.get_eps_data("2330", market="上市")

    assert len(records) == 8
    assert records[-1]["eps"] == 8.0
    assert records[-1]["source"].startswith("FinMind")
    assert chart is None
