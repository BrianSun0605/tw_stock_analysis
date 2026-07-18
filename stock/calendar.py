from datetime import datetime
import yfinance as yf
from utils.logger import get_logger

logger = get_logger(__name__)


def _suffix(market: str) -> str:
    return ".TWO" if market == "上櫃" else ".TW"


def get_calendar_events(stock_id: str, market: str = "",
                        dividend_history: list | None = None) -> dict:
    result = {"earnings": [], "ex_dividend": None, "dividend_months": []}
    try:
        ticker = yf.Ticker(stock_id + _suffix(market))
        info = ticker.info
        ex_div_ts = info.get("exDividendDate")
        if ex_div_ts:
            dt = datetime.fromtimestamp(ex_div_ts)
            result["ex_dividend"] = dt.strftime("%Y-%m-%d")
        earn_ts = info.get("earningsTimestamp")
        if earn_ts:
            dt = datetime.fromtimestamp(earn_ts)
            result["earnings"].append({"date": dt.strftime("%Y-%m-%d"), "label": "近期待公布財報"})
    except Exception as e:
        logger.debug("calendar fetch failed for %s: %s", stock_id, e)

    if dividend_history:
        months = set()
        for r in dividend_history:
            try:
                m = datetime.strptime(str(r.get("year", "")) + str(r.get("month", 1)), "%Y%m").month
                months.add(m)
            except (ValueError, TypeError):
                pass
        sorted_months = sorted(months)
        result["dividend_months"] = [f"{m}月" for m in sorted_months]
    return result
