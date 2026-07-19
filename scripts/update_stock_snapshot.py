#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Mapping, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock.normalizer import (
    TPEX_COMPANY_URL,
    TPEX_DAILY_SECURITIES_URL,
    TPEX_EMERGING_URL,
    TPEX_ETF_URL,
    TWSE_COMPANY_URL,
    TWSE_DAILY_SECURITIES_URL,
    TWSE_ETN_URLS,
    TWSE_FUND_URL,
    fetch_official_security_groups,
)

MINIMUM_COUNTS = {
    "listed": 800,
    "otc": 700,
    "emerging": 250,
    "listed_funds": 200,
    "otc_funds": 80,
    "listed_etns": 5,
    "listed_supplemental": 20,
    "otc_supplemental": 5,
}
REQUIRED_FIELDS = {
    "asset_type",
    "market",
    "currency",
    "listing_date",
    "official_source",
    "source_updated_at",
}


def _validate_sources(
    sources: Mapping[str, Dict[str, dict]],
) -> Tuple[Dict[str, dict], Dict[str, int]]:
    counts = {name: len(records) for name, records in sources.items()}
    short = {
        name: (counts.get(name, 0), minimum)
        for name, minimum in MINIMUM_COUNTS.items()
        if counts.get(name, 0) < minimum
    }
    if short:
        details = ", ".join(
            f"{name}={actual}<{minimum}" for name, (actual, minimum) in short.items()
        )
        raise RuntimeError(f"refusing partial snapshot: {details}")

    owners: Dict[str, str] = {}
    merged: Dict[str, dict] = {}
    for source_name, records in sources.items():
        for stock_id, record in records.items():
            if stock_id in owners:
                raise RuntimeError(
                    f"duplicate security {stock_id} in {owners[stock_id]} and {source_name}"
                )
            missing = REQUIRED_FIELDS - set(record)
            if missing:
                raise RuntimeError(
                    f"security {stock_id} missing fields: {sorted(missing)}"
                )
            if not record.get("official_source") or not record.get("source_updated_at"):
                raise RuntimeError(f"security {stock_id} has empty provenance")
            owners[stock_id] = source_name
            merged[stock_id] = record
    return merged, counts


def _validate_count_drift(
    target: str, new_count: int, maximum_ratio: float = 0.25
) -> None:
    try:
        with open(target, "r", encoding="utf-8") as handle:
            old_count = len(json.load(handle).get("stocks", {}))
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return
    if old_count and abs(new_count - old_count) / old_count > maximum_ratio:
        raise RuntimeError(
            f"refusing unusual count change: old={old_count}, new={new_count}, "
            f"limit={maximum_ratio:.0%}"
        )


def _snapshot_is_fresh(target: str) -> bool:
    try:
        with open(target, "r", encoding="utf-8") as handle:
            fetched_at = datetime.fromisoformat(json.load(handle)["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - fetched_at < timedelta(hours=24)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true", help="ignore the 24-hour update window"
    )
    args = parser.parse_args(argv)
    target = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "stock",
        "official_stock_snapshot.json",
    )
    if not args.force and _snapshot_is_fresh(target):
        print(f"snapshot is less than 24 hours old; keeping {target}")
        return 0
    groups = fetch_official_security_groups()
    records, counts = _validate_sources(groups)
    _validate_count_drift(target, len(records))
    payload = {
        "schema_version": 4,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "listed": TWSE_COMPANY_URL,
            "otc": TPEX_COMPANY_URL,
            "emerging": TPEX_EMERGING_URL,
            "listed_funds": TWSE_FUND_URL,
            "otc_funds": TPEX_ETF_URL,
            "listed_etns": list(TWSE_ETN_URLS.values()),
            "listed_supplemental": TWSE_DAILY_SECURITIES_URL,
            "otc_supplemental": TPEX_DAILY_SECURITIES_URL,
        },
        "source_counts": counts,
        "stocks": records,
    }
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=os.path.dirname(target), delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path = handle.name
    os.replace(temp_path, target)
    print(f"wrote {len(payload['stocks'])} records to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
