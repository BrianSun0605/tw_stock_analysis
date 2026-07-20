"""Validated TWSE/TPEx financial data with last-known-good offline fallback."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests

from config import CACHE_DIR, HEADERS, TIMEOUT
from models.data_value import DataValue


TWSE_REVENUE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
TPEX_REVENUE_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O"
TWSE_INCOME_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap06_L_{report_type}"
TPEX_INCOME_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap06_O_{report_type}"
TWSE_BALANCE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap07_L_{report_type}"
TPEX_BALANCE_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap07_O_{report_type}"

SOURCE_TTL = timedelta(hours=24)
_SOURCE_DIR = os.path.join(CACHE_DIR, "official_sources")
_LOCK = threading.RLock()
# The official OpenAPI normally sends ``application/json``.  Explicitly
# requesting it avoids content negotiation falling back to an HTML response
# on some proxy/CDN paths used by public hosts.
OFFICIAL_API_HEADERS = {**HEADERS, "Accept": "application/json, text/plain, */*"}


class OfficialSourceError(RuntimeError):
    """Base class for expected official-source failures."""


class OfficialNetworkError(OfficialSourceError):
    """The official endpoint could not be reached."""


class OfficialSchemaError(OfficialSourceError):
    """The official endpoint returned an unexpected structure."""


class OfficialDataMissing(OfficialSourceError):
    """The endpoint is valid but contains no record for the security."""


@dataclass(frozen=True)
class OfficialDataset:
    rows: List[Dict[str, Any]]
    source_url: str
    fetched_at: str
    status: str
    note: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _source_path(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return os.path.join(_SOURCE_DIR, f"{digest}.json.gz")


def _read_state(url: str) -> Optional[Dict[str, Any]]:
    try:
        with gzip.open(_source_path(url), "rt", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except (OSError, EOFError, json.JSONDecodeError, TypeError):
        return None


def _write_state(url: str, state: Mapping[str, Any]) -> None:
    os.makedirs(_SOURCE_DIR, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=_SOURCE_DIR, prefix=".official-", suffix=".tmp", delete=False
        ) as raw:
            temp_path = raw.name
            with gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
                compressed.write(
                    json.dumps(state, ensure_ascii=False, separators=(",", ":")).encode(
                        "utf-8"
                    )
                )
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temp_path, _source_path(url))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _stored_error(state: Mapping[str, Any], url: str) -> OfficialSourceError:
    message = str(state.get("last_error") or f"official source unavailable: {url}")
    # Versions before the public-web compatibility fix stored non-JSON
    # responses as schema errors.  They were transport/availability errors,
    # not proof that the official JSON contract had changed, so allow the
    # caller to use its explicitly-labelled fallback instead of being blocked
    # by that cached classification for a full day.
    if "官方來源不是有效 JSON" in message:
        return OfficialNetworkError(message)
    if state.get("error_type") == "schema":
        return OfficialSchemaError(message)
    return OfficialNetworkError(message)


def _non_json_response_error(
    response: Any, url: str, exc: Exception
) -> OfficialSourceError:
    """Classify HTML/empty proxy responses as availability failures.

    A JSON decoding error alone does not establish that TWSE changed its
    schema.  Public-cloud egress can instead receive a gateway, rate-limit,
    or bot-protection document.  Those cases must remain recoverable so the
    analysis pipeline can use the existing, labelled fallback sources.
    """
    headers = getattr(response, "headers", {}) or {}
    content_type = str(headers.get("Content-Type") or "").lower()
    content = getattr(response, "content", b"")
    if isinstance(content, str):
        raw = content.encode("utf-8", errors="replace")
    else:
        raw = bytes(content or b"")
    trimmed = raw.lstrip()
    if not trimmed or "json" not in content_type or trimmed.startswith((b"<", b"<!")):
        detail = content_type or "missing Content-Type"
        return OfficialNetworkError(
            f"官方來源暫未回傳 JSON（{detail}）：{url}（{type(exc).__name__}）"
        )
    return OfficialSchemaError(f"官方來源不是有效 JSON：{url}（{type(exc).__name__}）")


def _validate_rows(
    payload: Any,
    url: str,
    required_groups: Sequence[Sequence[str]],
) -> List[Dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise OfficialSchemaError(f"官方來源格式異常（不是非空陣列）：{url}")
    if not all(isinstance(row, dict) for row in payload):
        raise OfficialSchemaError(f"官方來源格式異常（資料列不是物件）：{url}")
    sample = payload[0]
    missing = [
        "/".join(group)
        for group in required_groups
        if not any(field in sample for field in group)
    ]
    if missing:
        raise OfficialSchemaError(f"官方來源缺少必要欄位 {missing}：{url}")
    return payload


def _load_dataset(
    url: str,
    required_groups: Sequence[Sequence[str]],
) -> OfficialDataset:
    """Fetch at most once per 24 hours and retain the last valid response."""
    now = _now()
    with _LOCK:
        state = _read_state(url)
        last_attempt = _parse_iso((state or {}).get("last_attempt_at"))
        if state and last_attempt and now - last_attempt < SOURCE_TTL:
            rows = state.get("rows")
            if isinstance(rows, list) and rows:
                stale = bool(state.get("last_error"))
                return OfficialDataset(
                    rows=rows,
                    source_url=url,
                    fetched_at=str(state.get("fetched_at") or last_attempt.isoformat()),
                    status="stale" if stale else "official",
                    note=str(state.get("last_error") or ""),
                )
            raise _stored_error(state, url)

        try:
            response = requests.get(url, headers=OFFICIAL_API_HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            error: OfficialSourceError = OfficialNetworkError(
                f"官方來源連線失敗：{url}（{type(exc).__name__}）"
            )
        else:
            try:
                rows = _validate_rows(response.json(), url, required_groups)
            except (ValueError, json.JSONDecodeError) as exc:
                error = _non_json_response_error(response, url, exc)
            except OfficialSchemaError as exc:
                error = exc
            else:
                fetched_at = _iso(now)
                _write_state(
                    url,
                    {
                        "schema_version": 1,
                        "source_url": url,
                        "last_attempt_at": fetched_at,
                        "fetched_at": fetched_at,
                        "last_error": None,
                        "error_type": None,
                        "rows": rows,
                    },
                )
                return OfficialDataset(rows, url, fetched_at, "official")

        previous_rows = (state or {}).get("rows")
        fallback_state = {
            **(state or {}),
            "schema_version": 1,
            "source_url": url,
            "last_attempt_at": _iso(now),
            "last_error": str(error),
            "error_type": "schema"
            if isinstance(error, OfficialSchemaError)
            else "network",
        }
        _write_state(url, fallback_state)
        if isinstance(previous_rows, list) and previous_rows:
            return OfficialDataset(
                rows=previous_rows,
                source_url=url,
                fetched_at=str((state or {}).get("fetched_at") or ""),
                status="stale",
                note=str(error),
            )
        raise error


def _security_code(row: Mapping[str, Any]) -> str:
    return str(row.get("公司代號") or row.get("SecuritiesCompanyCode") or "").strip()


def _number(value: Any) -> Optional[float]:
    try:
        text = str(value or "").replace(",", "").strip()
        return float(text) if text else None
    except (TypeError, ValueError, OverflowError):
        return None


def _roc_date(value: Any) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    try:
        if len(digits) == 7:
            year, month, day = (
                int(digits[:3]) + 1911,
                int(digits[3:5]),
                int(digits[5:7]),
            )
        elif len(digits) == 8:
            year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
        else:
            return ""
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return ""


def _roc_period(value: Any) -> Tuple[int, int]:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 5:
        raise OfficialSchemaError(f"官方資料年月格式異常：{value!r}")
    year, month = int(digits[:3]) + 1911, int(digits[3:5])
    if not 1 <= month <= 12:
        raise OfficialSchemaError(f"官方資料月份超出範圍：{value!r}")
    return year, month


def get_official_revenue(stock_id: str, market: str) -> List[Dict[str, Any]]:
    url = TWSE_REVENUE_URL if market == "上市" else TPEX_REVENUE_URL
    dataset = _load_dataset(
        url,
        (
            ("公司代號", "SecuritiesCompanyCode"),
            ("資料年月",),
            ("營業收入-當月營收",),
            ("出表日期", "Date"),
        ),
    )
    row = next(
        (item for item in dataset.rows if _security_code(item) == stock_id), None
    )
    if row is None:
        raise OfficialDataMissing(f"官方月營收查無 {stock_id}")
    year, month = _roc_period(row.get("資料年月"))
    observed_at = f"{year:04d}-{month:02d}"
    source_date = _roc_date(row.get("出表日期") or row.get("Date"))
    revenue = _number(row.get("營業收入-當月營收"))
    if revenue is None:
        raise OfficialSchemaError(f"官方月營收數值格式異常：{stock_id}")
    value = DataValue(
        value=revenue,
        source="TWSE OpenAPI" if market == "上市" else "TPEx OpenAPI",
        observed_at=observed_at,
        fetched_at=dataset.fetched_at,
        unit="TWD_thousand",
        currency="TWD",
        status=dataset.status,
        note=dataset.note,
    ).to_dict()
    return [
        {
            "year": year,
            "month": month,
            "revenue": revenue,
            "prev_month_revenue": _number(row.get("營業收入-上月營收")),
            "last_year_revenue": _number(row.get("營業收入-去年當月營收")),
            "mom": _number(row.get("營業收入-上月比較增減(%)")),
            "yoy": _number(row.get("營業收入-去年同月增減(%)")),
            "source": value["source"],
            "source_url": dataset.source_url,
            "source_date": source_date,
            "observed_at": observed_at,
            "fetched_at": dataset.fetched_at,
            "unit": "TWD_thousand",
            "status": dataset.status,
            "note": dataset.note,
            "data_value": value,
        }
    ]


def report_type_candidates(stock_info: Mapping[str, Any]) -> List[str]:
    text = f"{stock_info.get('name', '')} {stock_info.get('industry', '')}"
    if "金控" in text or str(stock_info.get("name", "")).endswith("金"):
        preferred = ["fh"]
    elif "銀行" in text or "銀" in str(stock_info.get("name", "")):
        preferred = ["basi"]
    elif "證券" in text or "期貨" in text:
        preferred = ["bd"]
    elif "保險" in text:
        preferred = ["ins"]
    elif "金融" in text:
        preferred = ["mim", "basi", "fh", "bd", "ins"]
    else:
        preferred = ["ci"]
    return list(dict.fromkeys([*preferred, "ci", "basi", "bd", "fh", "ins", "mim"]))


def _financial_url(market: str, statement: str, report_type: str) -> str:
    if market == "上市":
        template = TWSE_INCOME_URL if statement == "income" else TWSE_BALANCE_URL
    else:
        template = TPEX_INCOME_URL if statement == "income" else TPEX_BALANCE_URL
    return template.format(report_type=report_type)


def _find_financial_row(
    stock_id: str,
    market: str,
    stock_info: Mapping[str, Any],
    statement: str,
) -> Tuple[Mapping[str, Any], OfficialDataset, str]:
    for report_type in report_type_candidates(stock_info):
        url = _financial_url(market, statement, report_type)
        required = [
            ("公司代號", "SecuritiesCompanyCode"),
            ("出表日期", "Date"),
            ("年度", "Year"),
            ("季別", "Season"),
        ]
        required.append(
            ("營業收入", "收益", "利息淨收益")
            if statement == "income"
            else ("資產總額", "資產總計")
        )
        try:
            dataset = _load_dataset(url, required)
        except OfficialNetworkError:
            raise
        row = next(
            (item for item in dataset.rows if _security_code(item) == stock_id), None
        )
        if row is not None:
            return row, dataset, report_type
    raise OfficialDataMissing(f"官方{statement}財報查無 {stock_id}")


def _year_quarter(row: Mapping[str, Any]) -> Tuple[int, int]:
    try:
        raw_year = int(str(row.get("年度") or row.get("Year") or "").strip())
        year = raw_year + 1911 if raw_year < 1911 else raw_year
        quarter = int(str(row.get("季別") or row.get("Season") or "").strip())
    except ValueError as exc:
        raise OfficialSchemaError("官方財報年度或季別格式異常") from exc
    if quarter not in (1, 2, 3, 4):
        raise OfficialSchemaError(f"官方財報季別超出範圍：{quarter}")
    return year, quarter


def _first_number(row: Mapping[str, Any], fields: Iterable[str]) -> Optional[float]:
    for field in fields:
        value = _number(row.get(field))
        if value is not None:
            return value
    return None


def _field_value(
    raw_value: Optional[float],
    *,
    dataset: OfficialDataset,
    source_name: str,
    observed_at: str,
    unit: str = "TWD",
    multiplier: float = 1.0,
) -> Optional[Dict[str, Any]]:
    if raw_value is None:
        return None
    return DataValue(
        value=raw_value * multiplier,
        source=source_name,
        observed_at=observed_at,
        fetched_at=dataset.fetched_at,
        unit=unit,
        currency="TWD",
        status=dataset.status,
        note=dataset.note,
    ).to_dict()


def get_official_financials(
    stock_id: str,
    market: str,
    stock_info: Mapping[str, Any],
) -> Dict[str, Any]:
    income, income_dataset, income_type = _find_financial_row(
        stock_id, market, stock_info, "income"
    )
    balance, balance_dataset, balance_type = _find_financial_row(
        stock_id, market, stock_info, "balance"
    )
    income_period = _year_quarter(income)
    balance_period = _year_quarter(balance)
    if income_period != balance_period:
        raise OfficialSchemaError(
            f"官方損益表與資產負債表期間不一致：{income_period} / {balance_period}"
        )
    year, quarter = income_period
    observed_at = f"{year}-Q{quarter}"
    source_name = "TWSE OpenAPI" if market == "上市" else "TPEx OpenAPI"

    income_fields = {
        "totalRevenue": ("營業收入", "收益", "利息淨收益"),
        "grossProfit": ("營業毛利（毛損）淨額", "營業毛利（毛損）"),
        "operatingIncome": ("營業利益（損失）",),
        "netIncomeToCommon": ("淨利（淨損）歸屬於母公司業主", "本期淨利（淨損）"),
    }
    balance_fields = {
        "totalAssets": ("資產總額", "資產總計"),
        "currentAssets": ("流動資產",),
        "currentLiabilities": ("流動負債",),
        "retainedEarnings": ("保留盈餘",),
        "totalLiabilities": ("負債總額", "負債總計"),
        "stockholdersEquity": ("歸屬於母公司業主之權益合計", "權益總額", "權益總計"),
    }
    field_values: Dict[str, Dict[str, Any]] = {}
    for field, aliases in income_fields.items():
        item = _field_value(
            _first_number(income, aliases),
            dataset=income_dataset,
            source_name=source_name,
            observed_at=observed_at,
            multiplier=1000.0,
        )
        if item:
            field_values[field] = item
    for field, aliases in balance_fields.items():
        item = _field_value(
            _first_number(balance, aliases),
            dataset=balance_dataset,
            source_name=source_name,
            observed_at=observed_at,
            multiplier=1000.0,
        )
        if item:
            field_values[field] = item
    book_value = _field_value(
        _first_number(balance, ("每股參考淨值",)),
        dataset=balance_dataset,
        source_name=source_name,
        observed_at=observed_at,
        unit="TWD_per_share",
    )
    if book_value:
        field_values["bookValue"] = book_value

    cumulative_eps = _field_value(
        _first_number(income, ("基本每股盈餘（元）", "基本每股盈餘")),
        dataset=income_dataset,
        source_name=source_name,
        observed_at=observed_at,
        unit="TWD_per_share",
    )
    source_urls = {
        "income": income_dataset.source_url,
        "balance": balance_dataset.source_url,
    }
    return {
        "year": year,
        "quarter": quarter,
        "observed_at": observed_at,
        "report_type": income_type
        if income_type == balance_type
        else f"{income_type}/{balance_type}",
        "fields": {name: item["value"] for name, item in field_values.items()},
        "field_values": field_values,
        "official_cumulative_eps": cumulative_eps,
        "source_urls": source_urls,
        "status": (
            "stale"
            if "stale" in (income_dataset.status, balance_dataset.status)
            else "official"
        ),
        "note": "; ".join(
            note for note in (income_dataset.note, balance_dataset.note) if note
        ),
    }
