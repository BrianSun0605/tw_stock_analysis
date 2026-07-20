"""Explicitly-labelled FinMind fallback for public-cloud data outages.

TWSE/MOPS remains the preferred source.  This adapter is used only when the
official endpoints are temporarily unreachable from a hosting provider.  Its
records retain a ``fallback`` status and an evidence note so presentation and
reports never represent them as direct official responses.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Mapping

import requests

from config import HEADERS, TIMEOUT
from models.data_value import DataValue
from utils.cache import cache_get, cache_set


FINMIND_DATA_URL = "https://api.finmindtrade.com/api/v4/data"
FINMIND_DOCS_URL = "https://api.finmindtrade.com/docs"
_STOCK_ID_PATTERN = re.compile(r"^[0-9A-Za-z]{4,6}$")
_FALLBACK_NOTE = (
    "Third-party structured fallback while the official TWSE/MOPS source is "
    "unavailable; verify material decisions against official disclosures."
)


class FinMindSourceError(RuntimeError):
    """The explicitly-labelled fallback source could not be used."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _validate_stock_id(stock_id: str) -> str:
    normalized = str(stock_id or "").strip().upper()
    if not _STOCK_ID_PATTERN.fullmatch(normalized):
        raise FinMindSourceError("invalid security code for fallback data request")
    return normalized


def _fetch_dataset(
    stock_id: str,
    dataset: str,
    *,
    start_date: str,
) -> List[Mapping[str, Any]]:
    """Fetch one documented public dataset and validate its envelope."""
    try:
        response = requests.get(
            FINMIND_DATA_URL,
            params={
                "dataset": dataset,
                "data_id": _validate_stock_id(stock_id),
                "start_date": start_date,
                "end_date": date.today().isoformat(),
            },
            headers={**HEADERS, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise FinMindSourceError(
            f"FinMind {dataset} request failed ({type(exc).__name__})"
        ) from exc
    if not isinstance(payload, dict) or int(payload.get("status") or 0) != 200:
        raise FinMindSourceError(f"FinMind {dataset} returned an invalid response")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise FinMindSourceError(f"FinMind {dataset} did not contain a data list")
    return [row for row in rows if isinstance(row, dict)]


def _month_ordinal(year: int, month: int) -> int:
    return year * 12 + month - 1


def get_monthly_revenue_history(
    stock_id: str,
    *,
    months: int = 36,
) -> List[Dict[str, Any]]:
    """Return recent monthly revenue in the app's TWD-thousand contract."""
    cache_name = f"finmind_monthly_revenue_v1:{months}"
    cached = cache_get(stock_id, cache_name, max_age_sec=24 * 3600)
    if isinstance(cached, list):
        return cached

    start_year = max(2000, date.today().year - max(3, (months + 11) // 12 + 1))
    rows = _fetch_dataset(
        stock_id,
        "TaiwanStockMonthRevenue",
        start_date=f"{start_year:04d}-01-01",
    )
    by_period: Dict[tuple[int, int], float] = {}
    for row in rows:
        try:
            year = int(row.get("revenue_year"))
            month = int(row.get("revenue_month"))
        except (TypeError, ValueError):
            continue
        revenue_twd = _number(row.get("revenue"))
        if not (2000 <= year <= 3000 and 1 <= month <= 12 and revenue_twd is not None):
            continue
        # FinMind's documented financial values are in TWD; the existing
        # official/MOPS contract is TWD thousand, so normalize before models
        # and charts consume the values.
        by_period[(year, month)] = revenue_twd / 1000.0

    periods = sorted(by_period)[-months:]
    fetched_at = _now_iso()
    records: List[Dict[str, Any]] = []
    for year, month in periods:
        revenue = by_period[(year, month)]
        previous = by_period.get((year, month - 1))
        if month == 1:
            previous = by_period.get((year - 1, 12))
        year_ago = by_period.get((year - 1, month))
        data_value = DataValue(
            value=revenue,
            source="FinMind TaiwanStockMonthRevenue (fallback)",
            observed_at=f"{year:04d}-{month:02d}",
            fetched_at=fetched_at,
            unit="TWD_thousand",
            currency="TWD",
            status="fallback",
            note=_FALLBACK_NOTE,
        ).to_dict()
        records.append(
            {
                "year": year,
                "month": month,
                "revenue": revenue,
                "prev_month_revenue": previous,
                "last_year_revenue": year_ago,
                "mom": (revenue / previous - 1) * 100 if previous else None,
                "yoy": (revenue / year_ago - 1) * 100 if year_ago else None,
                "source": data_value["source"],
                "source_url": FINMIND_DOCS_URL,
                "source_date": "",
                "observed_at": data_value["observed_at"],
                "fetched_at": fetched_at,
                "unit": "TWD_thousand",
                "status": "fallback",
                "note": _FALLBACK_NOTE,
                "data_value": data_value,
            }
        )
    cache_set(stock_id, cache_name, records)
    return records


def get_quarterly_eps(stock_id: str) -> List[Dict[str, Any]]:
    """Return direct quarterly EPS values from the documented fallback feed."""
    cache_name = "finmind_quarterly_eps_v1"
    cached = cache_get(stock_id, cache_name, max_age_sec=24 * 3600)
    if isinstance(cached, list):
        return cached

    rows = _fetch_dataset(
        stock_id,
        "TaiwanStockFinancialStatements",
        start_date=f"{max(2000, date.today().year - 4):04d}-01-01",
    )
    by_period: Dict[tuple[int, int], tuple[str, float]] = {}
    for row in rows:
        if row.get("type") != "EPS":
            continue
        try:
            observed = date.fromisoformat(str(row.get("date")))
        except ValueError:
            continue
        if observed.month not in (3, 6, 9, 12):
            continue
        eps = _number(row.get("value"))
        if eps is None:
            continue
        by_period[(observed.year, (observed.month - 1) // 3 + 1)] = (
            observed.isoformat(),
            eps,
        )

    fetched_at = _now_iso()
    records: List[Dict[str, Any]] = []
    for (year, quarter), (observed_at, eps) in sorted(by_period.items()):
        data_value = DataValue(
            value=round(eps, 4),
            source="FinMind TaiwanStockFinancialStatements (fallback)",
            observed_at=observed_at,
            fetched_at=fetched_at,
            unit="TWD_per_share",
            currency="TWD",
            status="fallback",
            note=_FALLBACK_NOTE,
        ).to_dict()
        records.append(
            {
                "year": year,
                "quarter": quarter,
                "eps": data_value["value"],
                "label": f"Q{quarter} {year}",
                "source": data_value["source"],
                "source_url": FINMIND_DOCS_URL,
                "observed_at": observed_at,
                "fetched_at": fetched_at,
                "unit": "TWD_per_share",
                "status": "fallback",
                "note": _FALLBACK_NOTE,
                "data_value": data_value,
            }
        )
    cache_set(stock_id, cache_name, records)
    return records
