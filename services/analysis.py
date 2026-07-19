import base64
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import stock.normalizer as stock_normalizer
from news.aggregator import NewsAggregator
from models.growth_model import assess_revenue_growth, unavailable as growth_unavailable
from models.safety_model import assess_company_safety, assess_etf_structure
from report.generator import PDFReport
from stock.calendar import get_calendar_events
from stock.data import (
    get_basic_stock_info,
    get_eps_data,
    get_price_data,
    get_revenue_data,
)
from stock.dividend import get_dividend_data
from stock.peers import get_peers_comparison
from stock.official_financials import (
    OfficialDataMissing,
    OfficialNetworkError,
    OfficialSchemaError,
    get_official_financials,
)
from stock.mops_history import get_monthly_revenue_history
from services.market_snapshot import MarketDataSnapshot
from valuation.analyzer import ValuationAnalyzer
from config import TASK_ARTIFACT_DIR


class AnalysisError(RuntimeError):
    """A user-facing analysis failure with no internal traceback disclosure."""


class AnalysisCancelled(AnalysisError):
    """The user cancelled the task or its deadline elapsed."""


SUPPORTED_ANALYSIS_ASSET_TYPES = {"stock", "tdr", "etf"}
ASSET_TYPE_NAMES = {
    "etn": "ETN",
    "reit": "REIT",
    "preferred_stock": "特別股",
}


def _checkpoint(cancel_event=None, deadline: Optional[float] = None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise AnalysisCancelled("工作已由使用者取消。")
    if deadline is not None and time.time() > deadline:
        raise AnalysisCancelled("工作超過允許時間，已停止以避免持續佔用資源。")


@dataclass
class AnalysisResult:
    stock_info: Dict[str, Any]
    preview: Dict[str, Any]
    output_path: Optional[str]
    valuation: Dict[str, Any]
    report_context: Dict[str, Any]


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


def _ensure_supported_analysis_type(stock_info: Dict[str, Any]) -> None:
    asset_type = str(stock_info.get("asset_type") or "")
    if asset_type and asset_type not in SUPPORTED_ANALYSIS_ASSET_TYPES:
        product_name = ASSET_TYPE_NAMES.get(asset_type, asset_type)
        raise AnalysisError(
            f"{product_name} 已納入官方搜尋主檔，但專用分析模型尚未完成；"
            "為避免套用錯誤公式，目前不產生評級或 PDF。"
        )


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
    model_assessments=None,
    financial_snapshot=None,
    snapshot_created_at=None,
):
    fair = valuation.get("fair_price_range") or {}
    health = valuation.get("health_score") or {}
    peg = valuation.get("peg") or {}
    quality = valuation.get("quality_score") or {}
    model_assessments = model_assessments or {}
    financial_provenance = dict(price_info.get("_field_provenance", {}))
    units = {
        "grossMargins": "ratio",
        "operatingMargins": "ratio",
        "profitMargins": "ratio",
        "returnOnEquity": "ratio",
        "returnOnAssets": "ratio",
        "debtToEquity": "percent",
        "freeCashflow": "TWD",
        "totalCash": "TWD",
        "totalDebt": "TWD",
        "revenueGrowth": "ratio",
        "earningsGrowth": "ratio",
        "revenuePerShare": "TWD_per_share",
        "bookValue": "TWD_per_share",
        "forwardPE": "multiple",
        "dividendYield": "ratio",
        "payoutRatio": "ratio",
        "beta": "ratio",
        "fiftyTwoWeekHigh": "TWD",
        "fiftyTwoWeekLow": "TWD",
        "fiftyDayAverage": "TWD",
        "twoHundredDayAverage": "TWD",
    }
    for field, unit in units.items():
        if field in financial_provenance or basic_info.get(field) is None:
            continue
        financial_provenance[field] = {
            "value": basic_info[field],
            "source": "Yahoo Finance info",
            "observed_at": _price_date(price_data) or "",
            "fetched_at": snapshot_created_at or "",
            "unit": unit,
            "currency": "TWD" if unit.startswith("TWD") else None,
            "status": "fallback",
            "note": "Yahoo 未提供此欄位的獨立觀測日期；日期以本次分析快照標示。",
        }
    preview = {
        "is_etf": bool(valuation.get("is_etf")),
        "stock": {
            "name": basic_info.get("name") or stock_info.get("name"),
            "name_en": basic_info.get("name_en"),
            "stock_id": stock_info["stock_id"],
            "industry": basic_info.get("industry") or stock_info.get("industry", ""),
            "sector": basic_info.get("sector", ""),
            "market": stock_info.get("market", ""),
            "asset_type": stock_info.get("asset_type", ""),
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
                "grossMargins",
                "operatingMargins",
                "profitMargins",
                "returnOnEquity",
                "returnOnAssets",
                "debtToEquity",
                "freeCashflow",
                "totalCash",
                "totalDebt",
                "revenueGrowth",
                "earningsGrowth",
                "revenuePerShare",
                "bookValue",
                "forwardPE",
                "dividendYield",
                "payoutRatio",
                "beta",
                "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow",
                "fiftyDayAverage",
                "twoHundredDayAverage",
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
                if fair.get("eps_growth_rate") is not None
                else None
            ),
            "sample_size": fair.get("sample_size"),
        }
        if fair
        else None,
        "health_score": {
            "score": health.get("total_score"),
            "level": health.get("level"),
            "coverage": health.get("coverage"),
            "components": health.get("components", {}),
        }
        if health
        else None,
        "model_assessments": model_assessments,
        "peg": {
            "peg": peg.get("peg"),
            "verdict": peg.get("verdict"),
            "eps_growth_decimal": peg.get("eps_growth_decimal"),
            "eps_growth_pct": peg.get("eps_growth_pct"),
        }
        if peg
        else None,
        "quality_score": quality or None,
        "risk_warnings": valuation.get("risk_warnings", []),
        "dividend": {
            "yield": dividend_data.get("latest_yield"),
            "yield_basis": dividend_data.get("latest_yield_basis"),
            "last_completed_year": dividend_data.get("last_completed_year"),
            "ytd_yield": dividend_data.get("ytd_yield"),
            "consecutive_years": dividend_data.get("consecutive_years"),
        }
        if dividend_data.get("has_dividend")
        else None,
        "revenue": {
            "latest_yoy": revenue_data[-1].get("yoy"),
            "month": revenue_data[-1].get("month"),
            "year": revenue_data[-1].get("year"),
        }
        if revenue_data
        else None,
        "eps": {
            "eps": eps_data[-1].get("eps"),
            "year": eps_data[-1].get("year"),
            "quarter": eps_data[-1].get("quarter"),
        }
        if eps_data
        else None,
        "etf_data": {
            "nav_price": basic_info.get("nav_price"),
            "expense_ratio": basic_info.get("expense_ratio"),
            "total_assets": basic_info.get("total_assets"),
            "etf_category": basic_info.get("etf_category"),
            "fund_family": basic_info.get("fund_family"),
            "avg_volume": basic_info.get("avg_volume"),
            "etf_yield": basic_info.get("etf_yield"),
            "premium_pct": (
                round(
                    (basic_info["current_price"] - basic_info["nav_price"])
                    / basic_info["nav_price"]
                    * 100,
                    2,
                )
                if basic_info.get("current_price") and basic_info.get("nav_price")
                else None
            ),
        }
        if basic_info.get("is_etf")
        else None,
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
            "stock_mapping_status": stock_normalizer.STOCK_DB_STATUS,
            "stock_mapping_updated_at": stock_normalizer.STOCK_DB_UPDATED_AT,
            "health_coverage": health.get("coverage"),
            "piotroski_coverage": (quality.get("piotroski_details") or {}).get(
                "coverage"
            ),
            "eps_source": eps_data[-1].get("source") if eps_data else None,
            "revenue_source": revenue_data[-1].get("source") if revenue_data else None,
            "official_financial_status": (financial_snapshot or {}).get("status"),
            "official_financial_note": (financial_snapshot or {}).get("note"),
        },
        "data_provenance": {
            "current_price": {
                "value": basic_info.get("current_price"),
                "source": "Yahoo Finance",
                "observed_at": _price_date(price_data) or "",
                "fetched_at": snapshot_created_at or "",
                "unit": "TWD",
                "currency": "TWD",
                "status": "fallback",
                "note": "目前即時／歷史價格來源為 Yahoo Finance。",
            },
            "latest_revenue": revenue_data[-1].get("data_value")
            if revenue_data
            else None,
            "latest_eps": eps_data[-1].get("data_value") if eps_data else None,
            "financial_fields": financial_provenance,
            "official_cumulative_eps": (financial_snapshot or {}).get(
                "official_cumulative_eps"
            ),
        },
    }
    for period in ("1y", "6m", "3m"):
        chart = price_data.get(period, {}).get("chart")
        if chart and preview["chart_price"] is None:
            preview["chart_price"] = _image_data_url(chart)
        variants = price_data.get(period, {}).get("charts", {})
        if variants:
            preview["charts_price"] = {
                name: _image_data_url(path) for name, path in variants.items()
            }
            break
    return preview


def analyze(
    query: str,
    *,
    generate_report: bool = True,
    artifact_id: Optional[str] = None,
    include_news: bool = True,
    progress: Optional[Callable[[str], None]] = None,
    preview_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    report_progress: Optional[Callable[[int, int, str], None]] = None,
    cancel_event=None,
    deadline: Optional[float] = None,
) -> AnalysisResult:
    emit = progress or (lambda _message: None)
    _checkpoint(cancel_event, deadline)
    stock_info = _resolve_stock(query)
    _ensure_supported_analysis_type(stock_info)
    stock_id = stock_info["stock_id"]
    market = stock_info.get("market", "")
    emit(f"開始分析：{stock_info.get('name', stock_id)} ({stock_id})")
    if not artifact_id or not re.fullmatch(r"[a-f0-9]{32}", artifact_id):
        artifact_id = uuid.uuid4().hex
    artifact_dir = os.path.join(TASK_ARTIFACT_DIR, artifact_id, "charts")
    os.makedirs(artifact_dir, exist_ok=True)
    snapshot = MarketDataSnapshot(stock_id, market)

    emit("[1/5] 取得基本資訊與股價資料")
    _checkpoint(cancel_event, deadline)
    basic_info = get_basic_stock_info(stock_id, stock_info, snapshot=snapshot)
    is_etf = bool(basic_info.get("is_etf"))
    stock_info = {**stock_info, "is_etf": is_etf}
    price_data, price_info = get_price_data(
        stock_id, market=market, artifact_dir=artifact_dir, snapshot=snapshot
    )
    if not any(
        item.get("df") is not None and not item["df"].empty
        for item in price_data.values()
    ):
        raise AnalysisError("無法取得股價資料，請稍後再試。")
    if basic_info.get("etf_yield") is not None:
        price_info["yield"] = basic_info["etf_yield"]

    emit("[2/5] 取得營收與 EPS")
    _checkpoint(cancel_event, deadline)
    financial_snapshot = None
    if is_etf:
        revenue_data, revenue_chart = [], None
        eps_data, eps_chart = [], None
    else:
        try:
            financial_snapshot = get_official_financials(stock_id, market, stock_info)
        except (OfficialNetworkError, OfficialDataMissing) as exc:
            emit(f"官方季度財報暫時無法使用，將以有標示的備援資料補足：{exc}")
        except OfficialSchemaError as exc:
            raise AnalysisError(
                f"官方財報格式已改變，已停止分析以避免誤判：{exc}"
            ) from exc
        try:
            revenue_data, revenue_chart = get_revenue_data(
                stock_id, market=market, artifact_dir=artifact_dir
            )
        except OfficialSchemaError as exc:
            raise AnalysisError(
                f"官方月營收格式已改變，已停止分析以避免誤判：{exc}"
            ) from exc
        eps_data, eps_chart = get_eps_data(
            stock_id,
            market=market,
            artifact_dir=artifact_dir,
            snapshot=snapshot,
            official_financials=financial_snapshot,
        )
        if not eps_data:
            raise AnalysisError("季度 EPS 資料不足，無法執行個股估值。")

    emit("[3/5] 取得財報並計算指標")
    _checkpoint(cancel_event, deadline)
    balance_sheet = None
    financials = None
    if not is_etf:
        if financial_snapshot:
            price_info.update(financial_snapshot.get("fields", {}))
            price_info.setdefault("_field_provenance", {}).update(
                financial_snapshot.get("field_values", {})
            )
        balance_sheet = snapshot.balance_sheet()
        financials = snapshot.financials()
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

    emit("[3/5] 計算成長性與財務安全（兩者不合併）")
    _checkpoint(cancel_event, deadline)
    model_stock_info = {**basic_info, **stock_info, "is_etf": is_etf}
    if is_etf:
        growth_assessment = growth_unavailable(
            "not_applicable", "ETF 不套用公司營收成長模型。"
        )
        etf_inputs = {**stock_info, **basic_info}
        if basic_info.get("current_price") and basic_info.get("nav_price"):
            etf_inputs["premium_pct"] = round(
                (basic_info["current_price"] - basic_info["nav_price"])
                / basic_info["nav_price"]
                * 100,
                4,
            )
        safety_assessment = assess_etf_structure(etf_inputs)
    else:
        growth_assessment = growth_unavailable(
            "insufficient_data", "沒有可供成長模型使用的官方月營收。"
        )
        if revenue_data:
            latest_revenue = revenue_data[-1]
            try:
                revenue_history = get_monthly_revenue_history(
                    stock_id,
                    end_year=int(latest_revenue["year"]),
                    end_month=int(latest_revenue["month"]),
                    market=market,
                    months=24,
                    latest_record=latest_revenue,
                )
                growth_assessment = assess_revenue_growth(
                    revenue_history, model_stock_info
                )
            except (OfficialNetworkError, OfficialDataMissing) as exc:
                growth_assessment = growth_unavailable(
                    "official_history_unavailable",
                    f"官方歷史月營收暫時無法完整取得：{exc}",
                )
            except OfficialSchemaError as exc:
                raise AnalysisError(
                    f"官方歷史月營收格式已改變，已停止成長估計：{exc}"
                ) from exc
        safety_assessment = assess_company_safety(model_stock_info, price_info)
    model_assessments = {
        "growth": growth_assessment,
        "safety": safety_assessment,
        "combined_rating": None,
        "separation_note": "成長性與財務安全可能互相衝突，系統不將兩者平均成單一總分。",
    }
    _checkpoint(cancel_event, deadline)

    emit("[4/5] 取得新聞、股利、行事曆與同業")
    _checkpoint(cancel_event, deadline)
    news_data = (
        NewsAggregator().collect(stock_info)
        if include_news
        else {
            "items": [],
            "sentiment": {},
            "provider_status": {},
            "sentiment_method": "keyword_heuristic",
        }
    )
    dividend_data = get_dividend_data(stock_id, market=market, snapshot=snapshot)
    calendar_events = get_calendar_events(
        stock_id,
        market=market,
        dividend_history=dividend_data.get("history"),
        dividend_events=dividend_data.get("events"),
        snapshot=snapshot,
    )
    peers_data = get_peers_comparison(
        stock_id,
        stock_info.get("industry", ""),
        market=market,
        target_data={**price_info, **basic_info},
    )

    emit("[5/5] 組裝分析結果")
    _checkpoint(cancel_event, deadline)
    preview = _build_preview(
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
        model_assessments,
        financial_snapshot,
        snapshot.created_at,
    )
    if preview_callback:
        preview_callback(preview)
    output_path = None
    report_context = {
        "stock_info": basic_info,
        "price_data": price_data,
        "price_info": price_info,
        "revenue_data": revenue_data,
        "revenue_chart": revenue_chart,
        "eps_data": eps_data,
        "eps_chart": eps_chart,
        "news_data": news_data,
        "valuation_analysis": valuation,
        "dividend_data": dividend_data,
        "peers_data": peers_data,
        "financial_snapshot": financial_snapshot,
        "model_assessments": model_assessments,
    }
    if generate_report:
        emit("[5/5] 分析結果已可查看，正在產生 PDF 報告")

        def guarded_report_progress(current, total, section):
            _checkpoint(cancel_event, deadline)
            if report_progress:
                report_progress(current, total, section)

        output_path = PDFReport(
            **report_context, progress_callback=guarded_report_progress
        ).generate()
    _checkpoint(cancel_event, deadline)
    return AnalysisResult(
        stock_info=stock_info,
        preview=preview,
        output_path=output_path,
        valuation=valuation,
        report_context=report_context,
    )


def generate_report(
    result: AnalysisResult,
    *,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_event=None,
    deadline: Optional[float] = None,
) -> str:
    _checkpoint(cancel_event, deadline)
    if not result.report_context:
        raise AnalysisError("分析資料已過期，請重新執行分析後再產生 PDF。")

    def guarded_progress(current, total, section):
        _checkpoint(cancel_event, deadline)
        if progress_callback:
            progress_callback(current, total, section)

    return PDFReport(
        **result.report_context,
        progress_callback=guarded_progress,
    ).generate()
