from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests
import yfinance as yf

from stock.data import _suffix
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

logger = get_logger(__name__)

_DIV_CACHE_TTL = 43200  # 12 hours


def get_dividend_data(stock_id: str, market: Optional[str] = None) -> Dict[str, Any]:
    cached = cache_get(stock_id, "dividend", max_age_sec=_DIV_CACHE_TTL)
    if cached is not None:
        return cached
    try:
        ticker = yf.Ticker(f"{stock_id}{_suffix(market)}")
        hist = ticker.history(period="5y")
        if hist.empty:
            return _empty_result()

        dividends = hist["Dividends"]
        positive_div = dividends[dividends > 0]
        if positive_div.empty:
            return _empty_result()

        yearly: Dict[int, float] = {}
        for date, amt in dividends.items():
            y = date.year
            yearly[y] = yearly.get(y, 0) + amt

        years = sorted(yearly.keys(), reverse=True)
        history = [{"year": y, "dividend": round(yearly[y], 2)} for y in years]

        # consecutive_years: walk calendar years from most recent back,
        # break when a year is missing from yearly dict (=> no dividend that
        # calendar year). Previously yearly had >0 filter applied upstream
        # which made yearly[y] > 0 always true and the else branch unreachable.
        consecutive = 0
        if years:
            most_recent = years[0]
            for y in range(most_recent, most_recent - 11, -1):
                amt = yearly.get(y, 0)
                if amt > 0:
                    consecutive += 1
                else:
                    break

        info = ticker.info or {}
        current_price = info.get("currentPrice") or hist["Close"].iloc[-1]
        latest_yield = None
        if years and current_price:
            latest_yield = round(yearly[years[0]] / current_price * 100, 2)

        avg_yield = None
        if len(years) >= 3:
            total_div = sum(yearly[y] for y in years[:3])
            # 3-year avg price matches the 3-year dividend window (was 5y mean before).
            end_ts = hist.index[-1]
            start_ts = end_ts - timedelta(days=365 * 3)
            recent_price = hist["Close"][hist.index >= start_ts]
            avg_price = recent_price.mean() if not recent_price.empty else hist["Close"].mean()
            if avg_price:
                avg_yield = round(total_div / 3 / avg_price * 100, 2)

        result = {
            "has_dividend": True,
            "history": history,
            "consecutive_years": consecutive,
            "latest_yield": latest_yield,
            "avg_yield_3y": avg_yield,
            "current_price": round(float(current_price), 2) if current_price else None,
        }
        cache_set(stock_id, "dividend", result)
        return result
    except (KeyError, ValueError, AttributeError, IndexError,
            requests.RequestException) as e:
        logger.warning("dividend data fetch failed for %s: %s", stock_id, e, exc_info=True)
        return _empty_result()


def _empty_result() -> Dict[str, Any]:
    return {"has_dividend": False, "history": [], "consecutive_years": 0,
            "latest_yield": None, "avg_yield_3y": None, "current_price": None}
