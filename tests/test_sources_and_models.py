from datetime import datetime, timezone


from news.aggregator import NewsAggregator
from news.base_provider import NewsItem
from news.providers.google_news import BingNewsProvider
from stock import normalizer, peers
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


class _InfoSnapshot:
    def __init__(self, info):
        self._info = info

    def info(self):
        return self._info


def _analyzer(revenue=None, price_info=None):
    return ValuationAnalyzer(
        "2330", [], {}, revenue or [], {"name": "測試"}, price_info or {}
    )


def test_filing_date_prevents_q1_lookahead():
    eps = [{"year": 2024, "quarter": q, "eps": 1.0} for q in range(1, 5)] + [
        {"year": 2025, "quarter": 1, "eps": 5.0}
    ]
    ttm_map, eps_sorted = _calc_ttm_eps(eps)
    assert _get_ttm_for_date(datetime(2025, 5, 14), ttm_map, eps_sorted) == 4.0
    assert _get_ttm_for_date(datetime(2025, 5, 15), ttm_map, eps_sorted) == 8.0


def test_flat_negative_revenue_is_stable():
    revenue = [{"year": 2025, "month": month, "yoy": -10.0} for month in range(1, 7)]
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
    mapping = _parse_official_rows(
        [
            {
                "SecuritiesCompanyCode": "2330",
                "CompanyAbbreviation": "台積電*",
                "CompanyName": "台灣積體電路製造股份有限公司",
                "SecuritiesIndustryCode": "24",
            }
        ],
        "上市",
    )
    assert mapping["2330"]["name"] == "台積電"
    assert mapping["2330"]["market"] == "上市"
    assert mapping["2330"]["industry"] == "半導體"
    assert mapping["2330"]["aliases"] == [
        "TSMC",
        "台GG",
        "台灣積體電路製造股份有限公司",
    ]


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


def test_basic_info_keeps_official_etf_identity_and_tpex_aum_on_yahoo_failure(
    monkeypatch,
):
    class _FailingSnapshot:
        def info(self):
            raise RuntimeError("Yahoo temporarily unavailable")

    monkeypatch.setattr(stock_data, "YFINANCE_EXCEPTIONS", (RuntimeError,))
    result = stock_data.get_basic_stock_info(
        "006201",
        {
            "name": "元大富櫃50",
            "industry": "ETF",
            "market": "上櫃",
            "asset_type": "etf",
            "aum": 937_201_799,
            "tracking_index": "櫃買富櫃50指數",
            "official_source": "https://official.example/etf",
        },
        snapshot=_FailingSnapshot(),
    )

    assert result["is_etf"] is True
    assert result["total_assets"] == 937_201_799
    assert result["tracking_index"] == "櫃買富櫃50指數"


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
    result = get_calendar_events(
        "2330",
        snapshot=_InfoSnapshot({}),
        dividend_events=[
            {"year": 2024, "month": 6},
            {"year": 2024, "month": 12},
        ],
    )
    assert result["dividend_months"] == ["6月", "12月"]


def test_twse_fund_rows_are_parsed_as_etfs():
    parsed = normalizer._parse_twse_fund_rows(
        [
            {  # noqa: SLF001
                "基金代號": "0050",
                "基金簡稱": "元大台灣50",
                "基金類型": "國內成分證券指數股票型基金",
                "基金中文名稱": "元大台灣卓越50證券投資信託基金",
                "基金英文名稱": "Yuanta Taiwan Top 50 ETF",
                "標的指數/追蹤指數名稱": "臺灣50指數",
                "上市日期": "0920630",
            }
        ]
    )
    assert parsed["0050"]["asset_type"] == "etf"
    assert parsed["0050"]["listing_date"] == "2003-06-30"
    assert "元大台灣卓越50證券投資信託基金" in parsed["0050"]["aliases"]


def test_tpex_monthly_payload_is_parsed_as_official_etfs():
    payload = {
        "date": "20260618",
        "stat": "ok",
        "tables": [
            {
                "fields": ["證券代號", "證券名稱", "基金規模(元)"],
                "data": [["006201", "元大富櫃50", "937,201,799"]],
            }
        ],
    }
    parsed = normalizer._parse_tpex_etf_payload(payload)  # noqa: SLF001
    assert parsed["006201"]["asset_type"] == "etf"
    assert parsed["006201"]["market"] == "上櫃"
    assert parsed["006201"]["aum"] == 937_201_799


def test_emerging_company_rows_keep_market_and_official_source():
    parsed = normalizer._parse_official_rows(
        [
            {
                "Date": "1150718",
                "SecuritiesCompanyCode": "1260",
                "CompanyName": "富味鄉食品股份有限公司",
                "CompanyAbbreviation": "富味鄉",
                "SecuritiesIndustryCode": "02",
                "DateOfListing": "20121126",
            }
        ],
        "興櫃",
    )

    assert parsed["1260"]["market"] == "興櫃"
    assert parsed["1260"]["asset_type"] == "stock"
    assert parsed["1260"]["official_source"] == normalizer.TPEX_EMERGING_URL
    assert parsed["1260"]["source_updated_at"] == "2026-07-18"


def test_twse_etn_product_payloads_are_deduplicated_and_typed():
    payloads = {
        "domestic": {
            "stat": "ok",
            "fields": ["證券代號", "證券簡稱"],
            "data": [["020029", "元大ESG高股息N"]],
        },
        "lever_inverse": {
            "stat": "ok",
            "fields": ["證券代號", "證券簡稱"],
            "data": [["02001L", "富邦蘋果正二N"]],
        },
    }
    parsed = normalizer._parse_twse_etn_payloads(payloads, source_date="2026-07-19")

    assert set(parsed) == {"020029", "02001L"}
    assert parsed["020029"]["asset_type"] == "etn"
    assert parsed["02001L"]["etn_type"] == "lever_inverse"
    assert parsed["02001L"]["source_updated_at"] == "2026-07-19"


def test_daily_supplement_only_accepts_supported_security_types():
    known = {
        "2881": {"name": "富邦金", "industry": "金融", "market": "上市"},
    }
    rows = [
        {"Date": "1150717", "Code": "2881A", "Name": "富邦特"},
        {"Date": "1150717", "Code": "01001T", "Name": "土銀富邦R1"},
        {"Date": "1150717", "Code": "009999", "Name": "測試ETF"},
        {"Date": "1150717", "Code": "020099", "Name": "測試ETN"},
        {"Date": "1150717", "Code": "700019", "Name": "權證不得納入"},
    ]
    parsed = normalizer._parse_supplemental_security_rows(rows, "上市", known)

    assert parsed["2881A"]["asset_type"] == "preferred_stock"
    assert parsed["2881A"]["issuer_stock_id"] == "2881"
    assert parsed["01001T"]["asset_type"] == "reit"
    assert parsed["009999"]["asset_type"] == "etf"
    assert parsed["020099"]["asset_type"] == "etn"
    assert "700019" not in parsed
    assert {item["source_updated_at"] for item in parsed.values()} == {"2026-07-17"}


def test_tpex_daily_supplement_recognizes_preferred_stock():
    known = {
        "8349": {"name": "恒耀", "industry": "電機", "market": "上櫃"},
    }
    parsed = normalizer._parse_supplemental_security_rows(
        [
            {
                "Date": "1150717",
                "SecuritiesCompanyCode": "8349A",
                "CompanyName": "恒耀甲特",
            }
        ],
        "上櫃",
        known,
    )

    assert parsed["8349A"]["asset_type"] == "preferred_stock"
    assert parsed["8349A"]["market"] == "上櫃"


def test_peers_are_target_specific_include_target_and_rank_by_size(monkeypatch):
    monkeypatch.setattr(
        peers,
        "STOCK_DB",
        {
            "1101": {
                "name": "甲",
                "industry": "水泥",
                "market": "上市",
                "paid_in_capital": 1_000,
            },
            "1102": {
                "name": "乙",
                "industry": "水泥",
                "market": "上市",
                "paid_in_capital": 900,
            },
            "1103": {
                "name": "丙",
                "industry": "水泥",
                "market": "上市",
                "paid_in_capital": 5_000,
            },
        },
    )
    stored = {}
    monkeypatch.setattr(
        peers, "cache_get", lambda key, kind, max_age_sec: stored.get((key, kind))
    )
    monkeypatch.setattr(
        peers,
        "cache_set",
        lambda key, kind, value: stored.__setitem__((key, kind), value),
    )
    monkeypatch.setattr(
        peers,
        "_fetch_peer",
        lambda stock_id, stock: {
            "stock_id": stock_id,
            "name": stock["name"],
            "market_cap": stock["paid_in_capital"],
            "pe": None,
            "price": None,
            "dividend_yield": None,
        },
    )

    first = peers.get_peers_comparison("1101", "水泥", market="上市", max_peers=1)
    second = peers.get_peers_comparison("1102", "水泥", market="上市", max_peers=1)

    assert [item["stock_id"] for item in first] == ["1101", "1102"]
    assert first[0]["is_target"] is True
    assert [item["stock_id"] for item in second] == ["1102", "1101"]
    assert len(stored) == 2


def test_calendar_labels_past_earnings_as_published(monkeypatch):
    old_timestamp = datetime(2020, 1, 2, tzinfo=timezone.utc).timestamp()
    result = get_calendar_events(
        "2330", snapshot=_InfoSnapshot({"earningsTimestamp": old_timestamp})
    )
    assert result["earnings"] == [{"date": "2020-01-02", "label": "已公布財報"}]


def test_news_search_uses_primary_name_and_at_most_two_aliases():
    class RecordingProvider:
        name = "recording"

        def __init__(self):
            self.queries = []

        def search(self, query, _stock_info):
            self.queries.append(query)
            return [
                NewsItem(title=query, url=f"https://example.test/{len(self.queries)}")
            ]

    provider = RecordingProvider()
    aggregator = NewsAggregator()
    aggregator.providers = [provider]
    result = aggregator.collect(
        {
            "stock_id": "2330",
            "name": "台積電",
            "aliases": ["TSMC", "台灣積體電路", "第四個別名"],
        }
    )

    assert sorted(provider.queries) == sorted(["台積電 2330", "TSMC", "台灣積體電路"])
    assert result["total"] == 3
    assert result["provider_status"]["recording"]["queries"] == 3
