import base64
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import yfinance as yf

import stock.normalizer as stock_normalizer
from news.aggregator import NewsAggregator
from report.generator import PDFReport
from stock.calendar import get_calendar_events
from stock.data import (
    _suffix,
    get_basic_stock_info,
    get_eps_data,
    get_price_data,
    get_revenue_data,
)
from stock.dividend import get_dividend_data
from stock.peers import get_peers_comparison
from valuation.analyzer import ValuationAnalyzer
from stock.yf_errors import YFINANCE_EXCEPTIONS


class AnalysisError(RuntimeError):
    """A user-facing analysis failure with no internal traceback disclosure."""


@dataclass
class AnalysisResult:
    stock_info: Dict[str, Any]
    preview: Dict[str, Any]
    output_path: Optional[str]
    valuation: Dict[str, Any]


def _image_data_url(path: Optional[str]) -> Optional[str]:
    if not path or not os.path.isfile(path):
        return None
    extension = os.path.splitext(path)[1].lower()
    mime = "image/jpeg" if extension in (".jpg", ".jpeg") else "image/png"
    with open(path, "rb") as handle:
        return f"data:{mime};base64," + base64.b64encode(handle.read()).decode("ascii")


def _resolve_stock(query: str) -> Dict[str, Any]:
    stock_info = stock_normalizer.normalize(query)
    if stock_info.get("stock_id"):
        return stock_info
    results = stock_normalizer.search_stock(query)
    if not results:
        raise AnalysisError(f"查不到「{query}」相關的上市櫃股票。")
    return results[0]


def _price_date(price_data: Dict[str, Any]) -> Optional[str]:
    for period in ("1y", "6m", "3m"):
        frame = price_data.get(period, {}).get("df")
        if frame is not None and not frame.empty:
            return str(frame.index[-1].date())
    return None


def _build_preview(
    basic_info,
    stock_info,
    price_data,
    price_info,
    revenue_data,
    revenue_chart,
    eps_data,
    eps_chart,
    news_data,
    valuation,
    dividend_data,
    calendar_events,
    peers_data,
):
    fair = valuation.get("fair_price_range") or {}
    health = valuation.get("health_score") or {}
    peg = valuation.get("peg") or {}
    quality = valuation.get("quality_score") or {}
    rating = valuation.get("overall_rating") or {}
    preview = {
        "is_etf": bool(valuation.get("is_etf")),
        "stock": {
            "name": basic_info.get("name") or stock_info.get("name"),
            "name_en": basic_info.get("name_en"),
            "stock_id": stock_info["stock_id"],
            "industry": basic_info.get("industry") or stock_info.get("industry", ""),
            "sector": basic_info.get("sector", ""),
            "market": stock_info.get("market", ""),
            "current_price": basic_info.get("current_price"),
            "day_change_pct": basic_info.get("day_change_pct"),
            "market_cap": basic_info.get("market_cap"),
            "pe": price_info.get("trailingPE"),
            "price_date": _price_date(price_data),
            "description": basic_info.get("description", ""),
            "country": basic_info.get("country", ""),
            "website": basic_info.get("website", ""),
            "employees": basic_info.get("employees"),
        },
        "financials": {
            field: basic_info[field]
            for field in (
                "grossMargins", "operatingMargins", "profitMargins",
                "returnOnEquity", "returnOnAssets", "debtToEquity",
                "freeCashflow", "totalCash", "totalDebt", "revenueGrowth",
                "earningsGrowth", "revenuePerShare", "bookValue", "forwardPE",
                "dividendYield", "payoutRatio", "beta", "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
            )
            if basic_info.get(field) is not None
        },
        "fair_price": {
            "cheap": fair.get("cheap"),
            "fair": fair.get("fair"),
            "expensive": fair.get("expensive"),
            "current": fair.get("current_price"),
            "current_pe": fair.get("current_pe"),
            "eps_growth_decimal": fair.get("eps_growth_rate"),
            "eps_growth_pct": (
                round(fair["eps_growth_rate"] * 100, 2)
                if fair.get("eps_growth_rate") is not None else None
            ),
            "sample_size": fair.get("sample_size"),
        } if fair else None,
        "health_score": {
            "score": health.get("total_score"),
            "level": health.get("level"),
            "coverage": health.get("coverage"),
            "components": health.get("components", {}),
        } if health else None,
        "overall_rating": {
            "score": rating.get("score"),
            "rating": rating.get("rating"),
            "color": rating.get("color"),
            "coverage": rating.get("coverage", health.get("coverage")),
            "components": rating.get("components", {}),
        } if rating else None,
        "peg": {
            "peg": peg.get("peg"),
            "verdict": peg.get("verdict"),
            "eps_growth_decimal": peg.get("eps_growth_decimal"),
            "eps_growth_pct": peg.get("eps_growth_pct"),
        } if peg else None,
        "quality_score": quality or None,
        "risk_warnings": valuation.get("risk_warnings", []),
        "dividend": {
            "yield": dividend_data.get("latest_yield"),
            "yield_basis": dividend_data.get("latest_yield_basis"),
            "last_completed_year": dividend_data.get("last_completed_year"),
            "ytd_yield": dividend_data.get("ytd_yield"),
            "consecutive_years": dividend_data.get("consecutive_years"),
        } if dividend_data.get("has_dividend") else None,
        "revenue": {
            "latest_yoy": revenue_data[-1].get("yoy"),
            "month": revenue_data[-1].get("month"),
            "year": revenue_data[-1].get("year"),
        } if revenue_data else None,
        "eps": {
            "eps": eps_data[-1].get("eps"),
            "year": eps_data[-1].get("year"),
            "quarter": eps_data[-1].get("quarter"),
        } if eps_data else None,
        "etf_data": {
            "nav_price": basic_info.get("nav_price"),
            "expense_ratio": basic_info.get("expense_ratio"),
            "total_assets": basic_info.get("total_assets"),
            "etf_category": basic_info.get("etf_category"),
            "fund_family": basic_info.get("fund_family"),
            "avg_volume": basic_info.get("avg_volume"),
            "etf_yield": basic_info.get("etf_yield"),
            "premium_pct": (
                round((basic_info["current_price"] - basic_info["nav_price"]) / basic_info["nav_price"] * 100, 2)
                if basic_info.get("current_price") and basic_info.get("nav_price") else None
            ),
        } if basic_info.get("is_etf") else None,
        "peers": peers_data,
        "calendar": calendar_events,
        "news": [
            {
                "title": item.title,
                "source": item.source,
                "date": item.publish_date,
                "summary": item.summary,
                "sentiment": item.sentiment,
                "url": item.url,
                "matched_keyword": item.matched_keyword,
                "is_fallback": item.is_fallback,
            }
            for item in news_data.get("items", [])[:10]
        ],
        "news_sentiment": news_data.get("sentiment", {}),
        "sentiment_method": news_data.get("sentiment_method"),
        "provider_status": news_data.get("provider_status", {}),
        "chart_revenue": _image_data_url(revenue_chart),
        "chart_eps": _image_data_url(eps_chart),
        "chart_price": None,
        "charts_price": {},
        "data_quality": {
            "stock_mapping_source": stock_normalizer.STOCK_DB_SOURCE,
            "health_coverage": health.get("coverage"),
            "piotroski_coverage": (quality.get("piotroski_details") or {}).get("coverage"),
            "eps_source": eps_data[-1].get("source") if eps_data else None,
            "revenue_source": revenue_data[-1].get("source") if revenue_data else None,
        },
    }
    for period in ("1y", "6m", "3m"):
        chart = price_data.get(period, {}).get("chart")
        if chart and preview["chart_price"] is None:
            preview["chart_price"] = _image_data_url(chart)
        variants = price_data.get(period, {}).get("charts", {})
        if variants:
            preview["charts_price"] = {
                name: _image_data_url(path)
                for name, path in variants.items()
            }
            break
    return preview


def analyze(
    query: str,
    *,
    generate_report: bool = True,
    include_news: bool = True,
    progress: Optional[Callable[[str], None]] = None,
) -> AnalysisResult:
    emit = progress or (lambda _message: None)
    stock_info = _resolve_stock(query)
    stock_id = stock_info["stock_id"]
    market = stock_info.get("market", "")
    emit(f"開始分析：{stock_info.get('name', stock_id)} ({stock_id})")

    emit("[1/5] 取得基本資訊與股價資料")
    basic_info = get_basic_stock_info(stock_id, stock_info)
    is_etf = bool(basic_info.get("is_etf"))
    stock_info = {**stock_info, "is_etf": is_etf}
    price_data, price_info = get_price_data(stock_id, market=market)
    if not any(
        item.get("df") is not None and not item["df"].empty
        for item in price_data.values()
    ):
        raise AnalysisError("無法取得股價資料，請稍後再試。")
    if basic_info.get("etf_yield") is not None:
        price_info["yield"] = basic_info["etf_yield"]

    emit("[2/5] 取得營收與 EPS")
    if is_etf:
        revenue_data, revenue_chart = [], None
        eps_data, eps_chart = [], None
    else:
        revenue_data, revenue_chart = get_revenue_data(stock_id, market=market)
        eps_data, eps_chart = get_eps_data(stock_id, market=market)
        if not eps_data:
            raise AnalysisError("季度 EPS 資料不足，無法執行個股估值。")

    emit("[3/5] 取得財報並計算指標")
    balance_sheet = None
    financials = None
    if not is_etf:
        try:
            ticker = yf.Ticker(stock_id + _suffix(market))
            balance_sheet = ticker.balance_sheet
            financials = ticker.financials
        except YFINANCE_EXCEPTIONS:
            pass
    analyzer = ValuationAnalyzer(
        stock_id,
        eps_data,
        price_data,
        revenue_data,
        stock_info,
        price_info,
        balance_sheet=balance_sheet,
        financials=financials,
    )
    valuation = analyzer.full_analysis()

    emit("[4/5] 取得新聞、股利、行事曆與同業")
    news_data = NewsAggregator().collect(stock_info) if include_news else {
        "items": [], "sentiment": {}, "provider_status": {}, "sentiment_method": "keyword_heuristic"
    }
    dividend_data = get_dividend_data(stock_id, market=market)
    calendar_events = get_calendar_events(
        stock_id,
        market=market,
        dividend_history=dividend_data.get("history"),
        dividend_events=dividend_data.get("events"),
    )
    peers_data = get_peers_comparison(
        stock_id,
        stock_info.get("industry", ""),
        market=market,
    )

    emit("[5/5] 組裝預覽與 PDF")
    preview = _build_preview(
        basic_info, stock_info, price_data, price_info,
        revenue_data, revenue_chart, eps_data, eps_chart,
        news_data, valuation, dividend_data, calendar_events, peers_data,
    )
    output_path = None
    if generate_report:
        report = PDFReport(
            stock_info=basic_info,
            price_data=price_data,
            price_info=price_info,
            revenue_data=revenue_data,
            revenue_chart=revenue_chart,
            eps_data=eps_data,
            eps_chart=eps_chart,
            news_data=news_data,
            valuation_analysis=valuation,
            dividend_data=dividend_data,
            peers_data=peers_data,
        )
        output_path = report.generate()
    return AnalysisResult(
        stock_info=stock_info,
        preview=preview,
        output_path=output_path,
        valuation=valuation,
    )
