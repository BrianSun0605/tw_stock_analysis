import yfinance as yf
from stock.normalizer import STOCK_DB
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

logger = get_logger(__name__)


def _suffix(market: str) -> str:
    return ".TWO" if market == "上櫃" else ".TW"


def get_peers_comparison(
    stock_id: str,
    industry: str,
    market: str = "",
    max_peers: int = 5,
) -> list[dict]:
    if not industry:
        return []

    cache_key = f"peers:{industry}:{market}"
    cached = cache_get(cache_key, "peers")
    if cached is not None:
        return cached

    peers = []
    for sid, info in STOCK_DB.items():
        if sid == stock_id:
            continue
        if info.get("industry") != industry:
            continue
        if market and info.get("market") != market:
            continue
        peers.append((sid, info["name"]))
        if len(peers) >= max_peers:
            break

    if not peers:
        return []

    suffix = _suffix(market) if market else ".TW"
    result = []
    for sid, name in peers:
        try:
            ticker = yf.Ticker(sid + suffix)
            info = ticker.info
            trailing_pe = info.get("trailingPE")
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            dividend_yield = info.get("dividendYield")
            market_cap = info.get("marketCap")
            if dividend_yield is not None:
                dividend_yield = round(dividend_yield * 100, 2)
            if current_price is not None:
                current_price = round(current_price, 2)
            if trailing_pe is not None:
                trailing_pe = round(trailing_pe, 2)
            result.append({
                "stock_id": sid,
                "name": name,
                "pe": trailing_pe,
                "price": current_price,
                "dividend_yield": dividend_yield,
                "market_cap": market_cap,
            })
        except Exception as e:
            logger.debug("peer fetch failed for %s: %s", sid, e)
            result.append({
                "stock_id": sid,
                "name": name,
                "pe": None,
                "price": None,
                "dividend_yield": None,
                "market_cap": None,
            })

    cache_set(cache_key, "peers", result)
    return result
