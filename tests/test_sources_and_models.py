from datetime import datetime, timezone

import pandas as pd

from news.providers.google_news import BingNewsProvider
from stock import data as stock_data
from stock.calendar import _timestamp_to_taipei_date, get_calendar_events
from stock.normalizer import _parse_official_rows
from valuation.analyzer import ValuationAnalyzer, _calc_ttm_eps, _get_ttm_for_date


class _Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class _InfoTicker:
    def __init__(self, info):
        self.info = info


def _analyzer(revenue=None, price_info=None):
    return ValuationAnalyzer(
        "2330", [], {}, revenue or [], {"name": "測試"}, price_info or {}
    )


def test_filing_date_prevents_q1_lookahead():
    eps = [
        {"year": 2024, "quarter": q, "eps": 1.0}
        for q in range(1, 5)
    ] + [{"year": 2025, "quarter": 1, "eps": 5.0}]
    ttm_map, eps_sorted = _calc_ttm_eps(eps)
    assert _get_ttm_for_date(datetime(2025, 5, 14), ttm_map, eps_sorted) == 4.0
    assert _get_ttm_for_date(datetime(2025, 5, 15), ttm_map, eps_sorted) == 8.0


def test_flat_negative_revenue_is_stable():
    revenue = [
        {"year": 2025, "month": month, "yoy": -10.0}
        for month in range(1, 7)
    ]
    result = _analyzer(revenue=revenue).assess_revenue_growth()
    assert result["stable"] is True
    assert result["accelerating"] is False
    assert result["decelerating"] is False


def test_revenue_streak_breaks_when_month_is_missing():
    revenue = [
        {"year": 2025, "month": 1, "yoy": 5.0},
        {"year": 2025, "month": 2, "yoy": 5.0},
        {"year": 2025, "month": 4, "yoy": 5.0},
        {"year": 2025, "month": 5, "yoy": 5.0},
    ]
    result = _analyzer(revenue=revenue).assess_revenue_growth()
    assert result["consecutive_positive_months"] == 2


def test_altman_requires_all_inputs():
    analyzer = _analyzer(price_info={"totalAssets": 100})
    assert analyzer._calc_altman_z_score() is None


def test_official_mapping_uses_market_and_company_fields():
    mapping = _parse_official_rows([
        {
            "SecuritiesCompanyCode": "2330",
            "CompanyAbbreviation": "台積電*",
            "CompanyName": "台灣積體電路製造股份有限公司",
            "SecuritiesIndustryCode": "24",
        }
    ], "上市")
    assert mapping["2330"]["name"] == "台積電"
    assert mapping["2330"]["market"] == "上市"
    assert mapping["2330"]["industry"] == "半導體"
    assert mapping["2330"]["aliases"] == ["TSMC", "台GG", "台灣積體電路製造股份有限公司"]


def test_basic_info_preserves_official_name_and_normalizes_percent(monkeypatch):
    info = {
        "longName": "Taiwan Semiconductor Manufacturing Company Limited",
        "sector": "Technology",
        "regularMarketChange": -18,
        "previousClose": 1000,
        "currentPrice": 982,
        "dividendRate": 20,
        "dividendYield": 2.04,
    }
    monkeypatch.setattr(stock_data.yf, "Ticker", lambda _symbol: _InfoTicker(info))
    result = stock_data.get_basic_stock_info(
        "2330", {"name": "台積電", "industry": "半導體", "market": "上市"}
    )
    assert result["name"] == "台積電"
    assert result["name_en"].startswith("Taiwan Semiconductor")
    assert result["industry"] == "半導體"
    assert result["day_change_pct"] == -1.8
    assert round(result["dividendYield"], 5) == round(20 / 982, 5)


def test_bing_provider_parses_rss_items(monkeypatch):
    rss = b"""<?xml version="1.0"?>
    <rss><channel><item>
      <title>Test headline</title>
      <link>https://example.com/article</link>
      <pubDate>Fri, 18 Jul 2025 08:30:00 GMT</pubDate>
      <description><![CDATA[<b>Summary</b> text]]></description>
    </item></channel></rss>"""
    monkeypatch.setattr(
        "news.providers.google_news.requests.get",
        lambda *args, **kwargs: _Response(rss),
    )
    items = BingNewsProvider().search("2330")
    assert len(items) == 1
    assert items[0].publish_date == "2025-07-18"
    assert items[0].summary == "Summary text"


def test_timestamp_conversion_is_timezone_explicit():
    timestamp = datetime(2025, 1, 1, 16, 30, tzinfo=timezone.utc).timestamp()
    assert _timestamp_to_taipei_date(timestamp) == "2025-01-02"


def test_calendar_uses_real_dividend_event_months(monkeypatch):
    monkeypatch.setattr(
        "stock.calendar.yf.Ticker",
        lambda _symbol: _InfoTicker({}),
    )
    result = get_calendar_events(
        "2330",
        dividend_events=[
            {"year": 2024, "month": 6},
            {"year": 2024, "month": 12},
        ],
    )
    assert result["dividend_months"] == ["6月", "12月"]
