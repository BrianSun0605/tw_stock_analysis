from datetime import datetime

import pandas as pd

from valuation.analyzer import ValuationAnalyzer, _calc_ttm_eps, _get_ttm_for_date


def _eps(year, quarter, value=1.0):
    return {
        "year": year,
        "quarter": quarter,
        "eps": value,
        "label": f"Q{quarter} {year}",
    }


def _analyzer(eps_data=None, stock_info=None, price_info=None):
    prices = pd.DataFrame(
        {"close": [100.0] * 12},
        index=pd.date_range("2025-01-01", periods=12, freq="D"),
    )
    return ValuationAnalyzer(
        "2330",
        eps_data or [],
        {"1y": {"df": prices}},
        [],
        stock_info or {"name": "測試公司"},
        price_info or {"currentPrice": 100.0},
    )


def test_ttm_eps_requires_four_consecutive_quarters():
    data = [_eps(2024, 1), _eps(2024, 2), _eps(2024, 4), _eps(2025, 1)]
    ttm_map, _ = _calc_ttm_eps(data)
    assert ttm_map == {}


def test_historical_pe_uses_only_financials_available_on_that_date():
    data = [_eps(2024, 1), _eps(2024, 2), _eps(2024, 3), _eps(2024, 4), _eps(2025, 1)]
    ttm_map, eps_sorted = _calc_ttm_eps(data)
    assert _get_ttm_for_date(datetime(2025, 5, 14), ttm_map, eps_sorted) == 4.0
    assert _get_ttm_for_date(datetime(2025, 5, 15), ttm_map, eps_sorted) == 4.0


def test_eps_growth_requires_two_complete_ttm_windows():
    analyzer = _analyzer([_eps(2024, q, q) for q in range(1, 5)])
    assert analyzer._calc_eps_growth_rate() is None


def test_eps_growth_rejects_quarter_gaps():
    data = [_eps(2023, q) for q in range(1, 5)] + [
        _eps(2024, 1),
        _eps(2024, 2),
        _eps(2024, 4),
        _eps(2025, 1),
    ]
    analyzer = _analyzer(data)
    assert analyzer._calc_eps_growth_rate() is None


def test_financial_industry_is_excluded_from_altman_in_chinese():
    analyzer = _analyzer(stock_info={"name": "測試金控", "industry": "金融保險業"})
    assert analyzer._is_financial is True
    assert analyzer._calc_altman_z_score() is None


def test_etf_score_is_unavailable_when_data_coverage_is_too_low():
    analyzer = _analyzer(stock_info={"name": "測試 ETF", "is_etf": True})
    score = analyzer._calculate_etf_health_score()
    assert score["total_score"] is None
    assert score["coverage"] == 0


def test_piotroski_does_not_award_missing_history():
    analyzer = _analyzer(
        price_info={"currentPrice": 100, "returnOnAssets": 0.12, "totalCash": 10}
    )
    details = analyzer._calc_piotroski_details()
    assert details["score"] is None
    assert details["available_count"] < 9


def test_overall_rating_does_not_fill_missing_models_with_neutral_scores():
    analyzer = _analyzer(
        price_info={
            "currentPrice": 100,
            "earningsGrowth": 0.1,
            "returnOnEquity": 0.15,
            "profitMargins": 0.1,
            "returnOnAssets": 0.08,
            "freeCashflow": 1_000_000,
            "operatingCashflow": 1_000_000,
            "netIncomeToCommon": 800_000,
        }
    )
    analyzer.price_data["3m"] = {"df": analyzer.price_data["1y"]["df"]}
    assert analyzer.calculate_health_score()["total_score"] is not None
    rating = analyzer.calculate_overall_rating()
    assert rating["score"] is None
    assert rating["rating"] == "N/A"
    assert rating["coverage"] < 0.5


def test_health_score_is_unavailable_when_only_53_percent_is_covered():
    analyzer = _analyzer(
        price_info={
            "currentPrice": 100,
            "earningsGrowth": 0,
            "returnOnEquity": 0,
            "totalCash": 10,
        }
    )
    health = analyzer.calculate_health_score()
    assert health["coverage"] == 0.53
    assert health["total_score"] is None
    assert health["level"] == "資料不足"


def test_analysis_text_reports_missing_score_without_none_literal():
    text = _analyzer().generate_analysis_text()
    assert "資料不足" in text
    assert "None 分" not in text


def test_full_analysis_exposes_altman_status():
    quality = _analyzer().full_analysis()["quality_score"]
    assert quality["altman_status"] == "unavailable"


def test_etf_analysis_text_never_formats_none_as_score():
    analyzer = _analyzer(stock_info={"name": "測試 ETF", "is_etf": True})
    text = analyzer._generate_etf_analysis_text()
    assert "None 分" not in text
    assert "資料不足" in text
