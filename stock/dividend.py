from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from stock.yf_errors import YFINANCE_EXCEPTIONS
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

logger = get_logger(__name__)
_DIV_CACHE_TTL = 43200


def get_dividend_data(
    stock_id: str,
    market: Optional[str] = None,
    snapshot: Optional[Any] = None,
) -> Dict[str, Any]:
    cached = cache_get(stock_id, "dividend_v2", max_age_sec=_DIV_CACHE_TTL)
    if cached is not None:
        return cached
    try:
        if snapshot is None:
            from services.market_snapshot import MarketDataSnapshot

            snapshot = MarketDataSnapshot(stock_id, market or "")
        history_frame = snapshot.history(period="10y")
        if history_frame.empty or "Dividends" not in history_frame:
            return _empty_result()
        positive = history_frame["Dividends"][history_frame["Dividends"] > 0]
        if positive.empty:
            return _empty_result()

        events = [
            {
                "date": index.date().isoformat(),
                "year": int(index.year),
                "month": int(index.month),
                "dividend": round(float(amount), 4),
            }
            for index, amount in positive.items()
        ]
        yearly: Dict[int, float] = {}
        months: Dict[int, set[int]] = {}
        for event in events:
            year = event["year"]
            yearly[year] = yearly.get(year, 0.0) + event["dividend"]
            months.setdefault(year, set()).add(event["month"])

        current_year = datetime.now().year
        completed_years = sorted(
            (year for year in yearly if year < current_year), reverse=True
        )
        history = [
            {
                "year": year,
                "dividend": round(yearly[year], 2),
                "months": sorted(months[year]),
                "status": "complete",
            }
            for year in completed_years
        ]
        if current_year in yearly:
            history.insert(
                0,
                {
                    "year": current_year,
                    "dividend": round(yearly[current_year], 2),
                    "months": sorted(months[current_year]),
                    "status": "ytd",
                },
            )

        consecutive = 0
        last_complete_year = current_year - 1
        oldest_covered_year = int(history_frame.index.min().year)
        for year in range(last_complete_year, oldest_covered_year - 1, -1):
            if yearly.get(year, 0) <= 0:
                break
            consecutive += 1

        info = snapshot.info()
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None and not history_frame["Close"].empty:
            current_price = history_frame["Close"].iloc[-1]

        last_complete_dividend = (
            yearly.get(completed_years[0]) if completed_years else None
        )
        latest_yield = (
            round(last_complete_dividend / current_price * 100, 2)
            if last_complete_dividend is not None and current_price
            else None
        )
        ytd_dividend = round(yearly.get(current_year, 0), 2)
        ytd_yield = (
            round(ytd_dividend / current_price * 100, 2)
            if ytd_dividend and current_price
            else None
        )

        avg_yield = None
        if len(completed_years) >= 3:
            total_dividend = sum(yearly[year] for year in completed_years[:3])
            cutoff = history_frame.index[-1] - timedelta(days=365 * 3)
            recent_prices = history_frame["Close"][history_frame.index >= cutoff]
            average_price = recent_prices.mean() if not recent_prices.empty else None
            if average_price:
                avg_yield = round(total_dividend / 3 / average_price * 100, 2)

        result = {
            "has_dividend": True,
            "events": events,
            "history": history,
            "consecutive_years": consecutive,
            "latest_yield": latest_yield,
            "latest_yield_basis": "last_completed_year",
            "last_completed_year": completed_years[0] if completed_years else None,
            "ytd_dividend": ytd_dividend,
            "ytd_yield": ytd_yield,
            "avg_yield_3y": avg_yield,
            "current_price": round(float(current_price), 2) if current_price else None,
        }
        cache_set(stock_id, "dividend_v2", result)
        return result
    except YFINANCE_EXCEPTIONS as exc:
        logger.warning(
            "dividend data fetch failed for %s: %s", stock_id, exc, exc_info=True
        )
        return _empty_result()


def _empty_result() -> Dict[str, Any]:
    return {
        "has_dividend": False,
        "events": [],
        "history": [],
        "consecutive_years": 0,
        "latest_yield": None,
        "latest_yield_basis": None,
        "last_completed_year": None,
        "ytd_dividend": 0,
        "ytd_yield": None,
        "avg_yield_3y": None,
        "current_price": None,
    }
