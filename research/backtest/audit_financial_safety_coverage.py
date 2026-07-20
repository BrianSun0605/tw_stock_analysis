#!/usr/bin/env python3
"""Audit current official-statement coverage for the financial-safety formula.

This is an operational-coverage audit only.  It deliberately does not claim
predictive accuracy: that requires point-in-time historical statements and
objectively labelled financial-distress outcomes.
"""

# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import HEADERS, TIMEOUT  # noqa: E402
from stock.official_financials import (
    TPEX_BALANCE_URL,
    TPEX_INCOME_URL,
    TWSE_BALANCE_URL,
    TWSE_INCOME_URL,
)  # noqa: E402


def _number(value: Any) -> Optional[float]:
    try:
        text = str(value or "").replace(",", "").strip()
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _code(row: Mapping[str, Any]) -> str:
    return str(row.get("公司代號") or row.get("SecuritiesCompanyCode") or "").strip()


def _first(row: Mapping[str, Any], aliases: Iterable[str]) -> Optional[float]:
    for alias in aliases:
        value = _number(row.get(alias))
        if value is not None:
            return value
    return None


def _get(url: str) -> list[Dict[str, Any]]:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"expected a JSON list from {url}")
    return [row for row in payload if isinstance(row, dict)]


def _market_rows(market: str, income_url: str, balance_url: str) -> Dict[str, int]:
    income = {_code(row): row for row in _get(income_url) if _code(row)}
    balance = {_code(row): row for row in _get(balance_url) if _code(row)}
    common = sorted(set(income) & set(balance))
    complete_balance = 0
    exact_ebit = 0
    operating_income = 0
    complete_statement_formula = 0
    for code in common:
        income_row, balance_row = income[code], balance[code]
        balance_values = [
            _first(balance_row, ("資產總額", "資產總計")),
            _first(balance_row, ("流動資產",)),
            _first(balance_row, ("流動負債",)),
            _first(balance_row, ("保留盈餘",)),
            _first(balance_row, ("負債總額", "負債總計")),
        ]
        has_balance = all(value is not None for value in balance_values)
        if has_balance:
            complete_balance += 1
        ebit = _first(income_row, ("息前稅前淨利", "EBIT"))
        operating = _first(income_row, ("營業利益（損失）", "營業利益"))
        sales = _first(income_row, ("營業收入", "收益", "利息淨收益"))
        if ebit is not None:
            exact_ebit += 1
        if operating is not None:
            operating_income += 1
        if has_balance and ebit is not None and sales is not None:
            complete_statement_formula += 1
    return {
        "income_rows": len(income),
        "balance_rows": len(balance),
        "matched_issuers": len(common),
        "complete_balance_inputs": complete_balance,
        "exact_ebit_available": exact_ebit,
        "operating_income_available": operating_income,
        "complete_statement_inputs_before_market_cap": complete_statement_formula,
    }


def main() -> int:
    listed = _market_rows(
        "listed",
        TWSE_INCOME_URL.format(report_type="ci"),
        TWSE_BALANCE_URL.format(report_type="ci"),
    )
    otc = _market_rows(
        "otc",
        TPEX_INCOME_URL.format(report_type="ci"),
        TPEX_BALANCE_URL.format(report_type="ci"),
    )
    total = {
        key: listed.get(key, 0) + otc.get(key, 0) for key in set(listed) | set(otc)
    }
    print(
        json.dumps(
            {
                "purpose": "current official-statement operational coverage only; not predictive validation",
                "report_type": "ci (ordinary company format)",
                "listed": listed,
                "otc": otc,
                "total": total,
                "limitations": [
                    "Financial companies use different report types and are intentionally excluded.",
                    "Market capitalization is not included in these statement endpoints.",
                    "Current-period coverage does not test future distress prediction.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
