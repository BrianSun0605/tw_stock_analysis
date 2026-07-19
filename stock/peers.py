from concurrent.futures import ThreadPoolExecutor, as_completed
import math

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
        result.update(
            {
                "pe": round(float(info["trailingPE"]), 2)
                if info.get("trailingPE") is not None
                else None,
                "price": round(float(price), 2) if price is not None else None,
                "market_cap": info.get("marketCap"),
            }
        )
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


def _target_peer(stock_id: str, stock: dict, data: dict) -> dict:
    price = (
        data.get("currentPrice")
        or data.get("regularMarketPrice")
        or data.get("current_price")
    )
    market_cap = data.get("marketCap") or data.get("market_cap")
    normalized_yield = _yield_as_decimal(
        data.get("dividendYield"),
        data.get("dividendRate"),
        price,
    )
    return {
        "stock_id": stock_id,
        "name": stock.get("name", stock_id),
        "pe": round(float(data["trailingPE"]), 2)
        if data.get("trailingPE") is not None
        else None,
        "price": round(float(price), 2) if price is not None else None,
        "dividend_yield": round(normalized_yield * 100, 2)
        if normalized_yield is not None
        else None,
        "market_cap": market_cap,
    }


def get_peers_comparison(
    stock_id: str,
    industry: str,
    market: str = "",
    max_peers: int = 5,
    target_data: dict | None = None,
) -> list[dict]:
    if not industry:
        return []
    cache_key = f"peers:{stock_id}:{industry}:{market}:{max_peers}"
    cached = cache_get(cache_key, "peers", max_age_sec=3600)
    if cached is not None:
        return cached

    target = STOCK_DB.get(stock_id)
    if not target:
        return []
    target_type = target.get("asset_type")
    candidates = [
        (candidate_id, info)
        for candidate_id, info in STOCK_DB.items()
        if candidate_id != stock_id
        and info.get("industry") == industry
        and (not market or info.get("market") == market)
        and (not target_type or info.get("asset_type") == target_type)
    ]

    target_capital = target.get("paid_in_capital")

    def similarity_key(item):
        candidate_id, info = item
        capital = info.get("paid_in_capital")
        if target_capital and capital and target_capital > 0 and capital > 0:
            size_distance = abs(math.log(float(capital) / float(target_capital)))
        else:
            size_distance = float("inf")
        return (size_distance, candidate_id)

    candidates.sort(key=similarity_key)
    selected = [(stock_id, target), *candidates[:max_peers]]

    indexed = {candidate_id: index for index, (candidate_id, _) in enumerate(selected)}
    results = []
    candidates_to_fetch = selected
    if target_data is not None:
        target_result = _target_peer(stock_id, target, target_data)
        target_result["is_target"] = True
        results.append(target_result)
        candidates_to_fetch = selected[1:]
    with ThreadPoolExecutor(max_workers=min(5, len(selected))) as executor:
        futures = {
            executor.submit(_fetch_peer, candidate_id, info): candidate_id
            for candidate_id, info in candidates_to_fetch
        }
        for future in as_completed(futures):
            candidate_id = futures[future]
            try:
                result = future.result()
                result["is_target"] = candidate_id == stock_id
                results.append(result)
            except Exception as exc:
                logger.debug("peer worker failed for %s: %s", candidate_id, exc)
    results.sort(key=lambda item: indexed.get(item["stock_id"], 999))
    cache_set(cache_key, "peers", results)
    return results
