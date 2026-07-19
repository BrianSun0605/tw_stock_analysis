#!/usr/bin/env python3
"""Build a research-only monthly revenue panel from official MOPS archives."""

from __future__ import annotations

import argparse
import gzip
import os
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import HEADERS, TIMEOUT  # noqa: E402


ARCHIVE_URL = (
    "https://mopsov.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}_0.html"
)
RAW_DIR = ROOT / "research" / "data" / "raw"


def _number(value: str) -> float:
    return float(str(value).replace(",", "").strip())


def parse_archive(
    content: bytes, *, market: str, year: int, month: int, source_url: str
) -> List[Dict]:
    """Parse data rows by stable column position; labels are decoded only for validation."""
    text = content.decode("cp950", errors="strict")
    soup = BeautifulSoup(text, "lxml")
    rows = []
    seen = set()
    # Older archives do not use the hasBorder class. Iterating every tr exactly
    # once handles both generations without recursively duplicating nested tables.
    for tr in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in tr.find_all(["th", "td"], recursive=False)
        ]
        if len(cells) < 3:
            continue
        stock_id = cells[0].replace(" ", "").upper()
        if not re.fullmatch(r"[0-9A-Z]{4,6}", stock_id):
            continue
        try:
            revenue = _number(cells[2])
        except ValueError:
            continue
        if stock_id in seen:
            raise ValueError(f"duplicate security {stock_id} in {source_url}")
        seen.add(stock_id)
        rows.append(
            {
                "stock_id": stock_id,
                "market": "上市" if market == "sii" else "上櫃",
                "year": year,
                "month": month,
                "revenue_thousand": revenue,
                "source_url": source_url,
            }
        )
    if len(rows) < 500:
        raise ValueError(
            f"official archive returned only {len(rows)} rows: {source_url}"
        )
    return rows


def fetch_month(market: str, year: int, month: int, retries: int = 3) -> List[Dict]:
    url = ARCHIVE_URL.format(market=market, roc_year=year - 1911, month=month)
    raw_path = RAW_DIR / f"{market}_{year}_{month:02d}.html.gz"
    if raw_path.is_file():
        with gzip.open(raw_path, "rb") as handle:
            content = handle.read()
        return parse_archive(
            content, market=market, year=year, month=month, source_url=url
        )
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            rows = parse_archive(
                response.content,
                market=market,
                year=year,
                month=month,
                source_url=url,
            )
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            temp_path = raw_path.with_suffix(".tmp")
            with gzip.open(temp_path, "wb") as handle:
                handle.write(response.content)
            os.replace(temp_path, raw_path)
            return rows
        except (requests.RequestException, UnicodeDecodeError, ValueError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.0 + attempt)
    raise RuntimeError(f"failed official archive {url}: {last_error}")


def build_panel(start_year: int, end_year: int, workers: int = 2) -> pd.DataFrame:
    jobs = [
        (market, year, month)
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
        for market in ("sii", "otc")
    ]
    records = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as executor:
        futures = {
            executor.submit(fetch_month, market, year, month): (market, year, month)
            for market, year, month in jobs
        }
        for completed, future in enumerate(as_completed(futures), 1):
            records.extend(future.result())
            if completed % 12 == 0 or completed == len(futures):
                print(f"completed {completed}/{len(futures)} archives", flush=True)
    frame = pd.DataFrame.from_records(records)
    frame.sort_values(["stock_id", "year", "month", "market"], inplace=True)
    duplicates = frame.duplicated(["stock_id", "year", "month"], keep=False)
    if duplicates.any():
        sample = (
            frame.loc[duplicates, ["stock_id", "year", "month"]]
            .head()
            .to_dict("records")
        )
        raise RuntimeError(f"duplicate stock-month records: {sample}")
    expected_months = (end_year - start_year + 1) * 12
    if frame[["year", "month"]].drop_duplicates().shape[0] != expected_months:
        raise RuntimeError("official panel has missing calendar months")
    return frame


def write_atomic(frame: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".revenue-", suffix=".csv.gz", delete=False
        ) as handle:
            temp_path = Path(handle.name)
        frame.to_csv(temp_path, index=False, compression="gzip")
        with open(temp_path, "rb+") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research" / "data" / "official_monthly_revenue.csv.gz",
    )
    args = parser.parse_args(argv)
    if args.start_year > args.end_year:
        parser.error("start-year must be <= end-year")
    frame = build_panel(args.start_year, args.end_year, args.workers)
    write_atomic(frame, args.output)
    print(
        f"wrote {len(frame)} rows / {frame.stock_id.nunique()} securities "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
