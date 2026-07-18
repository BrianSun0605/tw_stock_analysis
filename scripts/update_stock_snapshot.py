#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock.normalizer import _fetch_stock_list_from_twse, _fetch_tpex_stock_list


def main() -> int:
    listed = _fetch_stock_list_from_twse()
    otc = _fetch_tpex_stock_list()
    if len(listed) < 800 or len(otc) < 700:
        raise RuntimeError(
            f"refusing partial snapshot: listed={len(listed)}, otc={len(otc)}"
        )
    payload = {
        "schema_version": 1,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "listed": "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
            "otc": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
        },
        "stocks": {**listed, **otc},
    }
    target = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "stock",
        "official_stock_snapshot.json",
    )
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
