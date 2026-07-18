from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf

from stock.data import _suffix, _yield_as_decimal
from stock.yf_errors import YFINANCE_EXCEPTIONS
from stock.normalizer import STOCK_DB
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_peer(stock_id: str, stock: dict) -> dict:
    name = stock.get("name", stock_id)
    result = {
        "stock_id": stock_id,
        "name": name,
        "pe": None,
        "price": None,
        "dividend_yield": None,
        "market_cap": None,
    }
    try:
        ticker = yf.Ticker(stock_id + _suffix(stock.get("market")))
        info = ticker.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        result.update({
            "pe": round(float(info["trailingPE"]), 2) if info.get("trailingPE") is not None else None,
            "price": round(float(price), 2) if price is not None else None,
            "market_cap": info.get("marketCap"),
        })
        normalized_yield = _yield_as_decimal(
            info.get("dividendYield"),
            info.get("dividendRate"),
            price,
        )
        if normalized_yield is not None:
            result["dividend_yield"] = round(normalized_yield * 100, 2)
    except YFINANCE_EXCEPTIONS as exc:
        logger.debug("peer fetch failed for %s: %s", stock_id, exc)
    return result


def get_peers_comparison(
    stock_id: str,
    industry: str,
    market: str = "",
    max_peers: int = 5,
) -> list[dict]:
    if not industry:
        return []
    cache_key = f"peers:{industry}:{market}"
    cached = cache_get(cache_key, "peers", max_age_sec=3600)
    if cached is not None:
        return cached

    candidates = [
        (candidate_id, info)
        for candidate_id, info in STOCK_DB.items()
        if candidate_id != stock_id
        and info.get("industry") == industry
        and (not market or info.get("market") == market)
    ][:max_peers]
    if not candidates:
        return []

    indexed = {candidate_id: index for index, (candidate_id, _) in enumerate(candidates)}
    results = []
    with ThreadPoolExecutor(max_workers=min(5, len(candidates))) as executor:
        futures = {
            executor.submit(_fetch_peer, candidate_id, info): candidate_id
            for candidate_id, info in candidates
        }
        for future in as_completed(futures):
            candidate_id = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.debug("peer worker failed for %s: %s", candidate_id, exc)
    results.sort(key=lambda item: indexed.get(item["stock_id"], 999))
    cache_set(cache_key, "peers", results)
    return results
