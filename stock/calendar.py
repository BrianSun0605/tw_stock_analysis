from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from stock.yf_errors import YFINANCE_EXCEPTIONS
from utils.logger import get_logger

logger = get_logger(__name__)
TAIPEI = ZoneInfo("Asia/Taipei")


def _timestamp_to_taipei_date(value: Any) -> Optional[str]:
    try:
        return (
            datetime.fromtimestamp(float(value), tz=timezone.utc)
            .astimezone(TAIPEI)
            .date()
            .isoformat()
        )
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def get_calendar_events(
    stock_id: str,
    market: str = "",
    dividend_history: Optional[List[Dict[str, Any]]] = None,
    dividend_events: Optional[List[Dict[str, Any]]] = None,
    snapshot: Optional[Any] = None,
) -> Dict[str, Any]:
    result = {"earnings": [], "ex_dividend": None, "dividend_months": []}
    try:
        if snapshot is None:
            from services.market_snapshot import MarketDataSnapshot

            snapshot = MarketDataSnapshot(stock_id, market)
        info = snapshot.info()
        result["ex_dividend"] = _timestamp_to_taipei_date(info.get("exDividendDate"))
        earnings_date = _timestamp_to_taipei_date(info.get("earningsTimestamp"))
        if earnings_date:
            today = datetime.now(TAIPEI).date().isoformat()
            label = "已公布財報" if earnings_date < today else "預計公布財報"
            result["earnings"].append({"date": earnings_date, "label": label})
    except YFINANCE_EXCEPTIONS as exc:
        logger.debug("calendar fetch failed for %s: %s", stock_id, exc)

    months = {
        int(event["month"])
        for event in (dividend_events or [])
        if event.get("month") is not None and 1 <= int(event["month"]) <= 12
    }
    if not months:
        for record in dividend_history or []:
            for month in record.get("months", []):
                if 1 <= int(month) <= 12:
                    months.add(int(month))
    result["dividend_months"] = [f"{month}月" for month in sorted(months)]
    return result
