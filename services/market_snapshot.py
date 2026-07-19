import threading
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
import yfinance as yf

from stock.data import _suffix


_MISSING = object()


class MarketDataSnapshot:
    """One-analysis lazy cache around a single yfinance Ticker instance."""

    def __init__(self, stock_id: str, market: str = ""):
        self.stock_id = stock_id
        self.market = market
        self.symbol = f"{stock_id}{_suffix(market)}"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._ticker = yf.Ticker(self.symbol)
        self._values: Dict[str, Any] = {}
        self._history: Dict[tuple, pd.DataFrame] = {}
        self._lock = threading.RLock()

    def _property(self, key: str, attribute: str):
        with self._lock:
            value = self._values.get(key, _MISSING)
            if value is _MISSING:
                value = getattr(self._ticker, attribute)
                self._values[key] = value
            return value

    def info(self) -> Dict[str, Any]:
        value = self._property("info", "info")
        return value or {}

    def history(self, **kwargs) -> pd.DataFrame:
        key = tuple(sorted(kwargs.items()))
        with self._lock:
            if key not in self._history:
                self._history[key] = self._ticker.history(**kwargs)
            return self._history[key]

    def quarterly_income_stmt(self) -> pd.DataFrame:
        value = self._property("quarterly_income_stmt", "quarterly_income_stmt")
        return value if value is not None else pd.DataFrame()

    def balance_sheet(self) -> pd.DataFrame:
        value = self._property("balance_sheet", "balance_sheet")
        return value if value is not None else pd.DataFrame()

    def financials(self) -> pd.DataFrame:
        value = self._property("financials", "financials")
        return value if value is not None else pd.DataFrame()
