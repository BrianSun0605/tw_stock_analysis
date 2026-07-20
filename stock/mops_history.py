"""On-demand official company revenue history from MOPS individual queries."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup

from config import HEADERS, TIMEOUT
from stock.official_financials import (
    OfficialDataMissing,
    OfficialNetworkError,
    OfficialSchemaError,
)
from utils.cache import cache_get, cache_set


MOPS_PAGE_URL = "https://mopsov.twse.com.tw/mops/web/t05st10_ifrs"
MOPS_QUERY_URL = "https://mopsov.twse.com.tw/mops/web/ajax_t05st10_ifrs"
MOPS_ARCHIVE_URL = (
    "https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}_0.html"
)


def _number(value: Any) -> Optional[float]:
    try:
        text = str(value or "").replace(",", "").strip()
        return float(text) if text else None
    except (TypeError, ValueError, OverflowError):
        return None


def parse_month_html(html: str, *, year: int, month: int) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    if "FOR SECURITY REASONS" in soup.get_text(" ", strip=True):
        raise OfficialNetworkError("MOPS 拒絕本次歷史月營收工作階段")
    values: Dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"], recursive=False)
            ]
            if len(cells) >= 2 and cells[0] in {
                "本月",
                "去年同期",
                "增減百分比",
                "本年累計",
                "去年累計",
            }:
                values.setdefault(cells[0], cells[1])
    revenue = _number(values.get("本月"))
    if revenue is None:
        raise OfficialDataMissing(f"MOPS 查無 {year}-{month:02d} 月營收")
    return {
        "year": year,
        "month": month,
        "revenue": revenue,
        "last_year_revenue": _number(values.get("去年同期")),
        "yoy": _number(values.get("增減百分比")),
        "source": "MOPS official company query",
        "source_url": MOPS_QUERY_URL,
        "observed_at": f"{year:04d}-{month:02d}",
        "unit": "TWD_thousand",
        "currency": "TWD",
        "status": "official",
    }


def _periods(end_year: int, end_month: int, months: int) -> List[Tuple[int, int]]:
    end = end_year * 12 + end_month - 1
    return [divmod(period, 12) for period in range(end - months + 1, end + 1)]


def _parse_archive(content: bytes, source_url: str) -> Dict[str, float]:
    try:
        text = content.decode("cp950", errors="strict")
    except UnicodeDecodeError as exc:
        raise OfficialSchemaError(f"MOPS 歷史封存編碼改變：{source_url}") from exc
    soup = BeautifulSoup(text, "lxml")
    result: Dict[str, float] = {}
    for row in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["th", "td"], recursive=False)
        ]
        if len(cells) < 3:
            continue
        stock_id = cells[0].replace(" ", "").upper()
        if not re.fullmatch(r"[0-9A-Z]{4,6}", stock_id):
            continue
        revenue = _number(cells[2])
        if revenue is not None:
            result[stock_id] = revenue
    if len(result) < 500:
        raise OfficialSchemaError(f"MOPS 歷史封存只有 {len(result)} 筆：{source_url}")
    return result


def _archive_month(market: str, year: int, month: int) -> Dict[str, float]:
    market_path = "sii" if market == "上市" else "otc"
    key = f"{market_path}:{year:04d}{month:02d}"
    cached = cache_get("official_archive", key, max_age_sec=30 * 86400)
    if cached is not None:
        return cached
    url = MOPS_ARCHIVE_URL.format(
        market=market_path,
        roc_year=year - 1911,
        month=month,
    )
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OfficialNetworkError(
            f"MOPS 歷史封存連線失敗：{url}（{type(exc).__name__}）"
        ) from exc
    result = _parse_archive(response.content, url)
    cache_set("official_archive", key, result)
    return result


def _history_from_archives(
    stock_id: str,
    market: str,
    periods: Sequence[Tuple[int, int]],
) -> List[Dict[str, Any]]:
    def fetch(period):
        year, zero_based_month = period
        month = zero_based_month + 1
        mapping = _archive_month(market, year, month)
        revenue = mapping.get(stock_id)
        if revenue is None:
            return None
        return {
            "year": year,
            "month": month,
            "revenue": revenue,
            "source": "MOPS official monthly archive",
            "source_url": MOPS_ARCHIVE_URL.format(
                market="sii" if market == "上市" else "otc",
                roc_year=year - 1911,
                month=month,
            ),
            "observed_at": f"{year:04d}-{month:02d}",
            "unit": "TWD_thousand",
            "currency": "TWD",
            "status": "official",
        }

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(fetch, periods))
    return [item for item in results if item is not None]


def _enrich_comparisons(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Derive comparable monthly fields absent from the archive download."""
    by_period = {
        item["year"] * 12 + item["month"] - 1: item
        for item in records
        if item.get("year") is not None and item.get("month") is not None
    }
    for period, item in by_period.items():
        revenue = _number(item.get("revenue"))
        previous = by_period.get(period - 1)
        year_ago = by_period.get(period - 12)
        previous_revenue = _number((previous or {}).get("revenue"))
        year_ago_revenue = _number((year_ago or {}).get("revenue"))
        item.setdefault("prev_month_revenue", previous_revenue)
        item.setdefault("last_year_revenue", year_ago_revenue)
        if item.get("mom") is None and revenue is not None and previous_revenue:
            item["mom"] = (revenue / previous_revenue - 1) * 100
        else:
            item.setdefault("mom", None)
        if item.get("yoy") is None and revenue is not None and year_ago_revenue:
            item["yoy"] = (revenue / year_ago_revenue - 1) * 100
        else:
            item.setdefault("yoy", None)
    return records


def _fetch_chunk(
    stock_id: str, periods: Sequence[Tuple[int, int]]
) -> List[Dict[str, Any]]:
    session = requests.Session()
    headers = {**HEADERS, "Referer": MOPS_PAGE_URL}
    try:
        response = session.get(MOPS_PAGE_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OfficialNetworkError(
            f"MOPS 歷史查詢初始化失敗（{type(exc).__name__}）"
        ) from exc
    results = []
    for year, zero_based_month in periods:
        month = zero_based_month + 1
        for attempt in range(3):
            try:
                response = session.post(
                    MOPS_QUERY_URL,
                    headers=headers,
                    data={
                        "encodeURIComponent": "1",
                        "step": "1",
                        "firstin": "1",
                        "off": "1",
                        "co_id": stock_id,
                        "year": str(year - 1911),
                        "month": f"{month:02d}",
                    },
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                if attempt == 2:
                    raise OfficialNetworkError(
                        f"MOPS {stock_id} {year}-{month:02d} 連線失敗（{type(exc).__name__}）"
                    ) from exc
            else:
                try:
                    results.append(
                        parse_month_html(response.text, year=year, month=month)
                    )
                    break
                except OfficialDataMissing:
                    break
                except OfficialNetworkError:
                    if attempt == 2:
                        raise
            time.sleep(1.0 + attempt)
            session.get(MOPS_PAGE_URL, headers=headers, timeout=TIMEOUT)
        time.sleep(0.15)
    return results


def get_monthly_revenue_history(
    stock_id: str,
    *,
    end_year: int,
    end_month: int,
    market: str,
    months: int = 24,
    latest_record: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if months < 24 or months > 60:
        raise ValueError("history months must be between 24 and 60")
    cache_key = f"{end_year:04d}{end_month:02d}:{months}"
    cached = cache_get(
        stock_id, f"mops_revenue_history_v1:{cache_key}", max_age_sec=86400
    )
    if cached is not None:
        return _enrich_comparisons(cached)
    periods = _periods(end_year, end_month, months)
    records = _history_from_archives(stock_id, market, periods)
    if latest_record:
        records = [
            item
            for item in records
            if (item["year"], item["month"])
            != (latest_record.get("year"), latest_record.get("month"))
        ]
        records.append(latest_record)
    records.sort(key=lambda item: (item["year"], item["month"]))
    _enrich_comparisons(records)
    if len(records) < 24:
        raise OfficialDataMissing(
            f"MOPS {stock_id} 只有 {len(records)} 個月，成長模型至少需要 24 個月"
        )
    last_periods = [item["year"] * 12 + item["month"] - 1 for item in records[-24:]]
    if any(
        current - previous != 1
        for previous, current in zip(last_periods, last_periods[1:])
    ):
        raise OfficialSchemaError(f"MOPS {stock_id} 最近 24 個月資料不連續")
    cache_set(stock_id, f"mops_revenue_history_v1:{cache_key}", records)
    return records
