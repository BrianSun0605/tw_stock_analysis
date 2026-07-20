"""Transparent financial-structure reference screens.

Company safety deliberately does *not* invent a Taiwan bankruptcy probability.
It exposes the public-company Altman Z calculation, its input coverage, and
its applicability limits until a Taiwan point-in-time outcome backtest exists.
ETF structure remains a separate, non-company screen.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


MODEL_VERSION = "financial_structure_reference_v3"
ALTMAN_PUBLIC_COMPANY_FORMULA = "altman_z_public_company_v1"
OFFICIAL_QUARTERLY_REFERENCE_FORMULA = (
    "taiwan_official_quarterly_structure_reference_v1"
)


def _number(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _is_financial(stock_info: Mapping[str, Any]) -> bool:
    value = " ".join(
        str(stock_info.get(key, "")) for key in ("name", "industry", "sector")
    ).lower()
    return any(
        keyword in value
        for keyword in (
            "金融",
            "銀行",
            "保險",
            "證券",
            "金控",
            "financial",
            "bank",
            "insurance",
            "securities",
        )
    )


def _unavailable(status: str, note: str, model: str = MODEL_VERSION) -> Dict[str, Any]:
    return {
        "rating": None,
        "reference_rating": None,
        "experimental_rating": None,
        "reference_band": None,
        "score": None,
        "score_label": "Altman Z-Score",
        "status": status,
        "confidence": "none",
        "coverage": 0.0,
        "target": "公司財務結構參考篩檢（不是未來 12 個月破產機率）",
        "model_version": model,
        "components": {},
        "formula": None,
        "disclaimer": "本項僅供研究與教學參考，不構成投資建議、信用評等或破產機率。",
        "note": note,
    }


def _frame_value(frame: Any, labels: Iterable[str]) -> Tuple[Optional[float], str]:
    """Read the newest annual statement value without silently mixing periods."""
    if frame is None or getattr(frame, "empty", True) or not len(frame.columns):
        return None, ""
    column = frame.columns[0]
    for label in labels:
        if label not in frame.index:
            continue
        value = frame.loc[label, column]
        # A duplicate row label would yield a Series and is not safe to choose.
        if hasattr(value, "iloc"):
            return None, ""
        parsed = _number(value)
        if parsed is not None:
            try:
                observed = str(column.date())
            except AttributeError:
                observed = str(column)
            return parsed, observed
    return None, ""


def _annual_statement_inputs(
    price_info: Mapping[str, Any],
    balance_sheet: Any,
    financials: Any,
) -> Tuple[Dict[str, Optional[float]], Dict[str, str], bool]:
    """Return period-aligned annual inputs for an Altman public-company screen."""
    balance_fields = {
        "total_assets": ("Total Assets",),
        "current_assets": ("Current Assets",),
        "current_liabilities": ("Current Liabilities",),
        "retained_earnings": ("Retained Earnings",),
        "total_liabilities": (
            "Total Liabilities Net Minority Interest",
            "Total Liabilities",
        ),
    }
    income_fields = {
        "ebit": ("EBIT",),
        "sales": ("Total Revenue",),
    }
    values: Dict[str, Optional[float]] = {}
    periods: Dict[str, str] = {}
    for name, labels in balance_fields.items():
        values[name], periods[name] = _frame_value(balance_sheet, labels)
    for name, labels in income_fields.items():
        values[name], periods[name] = _frame_value(financials, labels)
    values["market_value_equity"] = _number(price_info.get("marketCap"))
    periods["market_value_equity"] = str(price_info.get("price_date") or "")

    # No annual statements means there is no safe way to use a current-quarter
    # OpenAPI value in an annual-sales formula.  Leave it unavailable rather
    # than silently combining mismatched periods.
    statement_periods = {
        value
        for key, value in periods.items()
        if key != "market_value_equity" and value
    }
    aligned = (
        bool(statement_periods) and len({value[:4] for value in statement_periods}) == 1
    )
    return values, periods, aligned


def _official_quarterly_inputs(
    price_info: Mapping[str, Any], financial_snapshot: Mapping[str, Any]
) -> Tuple[Dict[str, Optional[float]], Dict[str, str], bool, float]:
    """Build a current-period reference from fields available in TWSE/TPEx.

    The official endpoints expose operating income, rather than a directly
    comparable EBIT field, and publish year-to-date income-statement values.
    We annualize only those two flow variables by ``4 / reported_quarter``;
    balance-sheet values remain period-end values.  This is deliberately named
    a *financial-structure reference*, not an original Altman Z score or a
    Taiwan bankruptcy probability.
    """
    fields = financial_snapshot.get("fields") or {}
    observed_at = str(financial_snapshot.get("observed_at") or "")
    try:
        quarter = int(financial_snapshot.get("quarter"))
    except (TypeError, ValueError):
        quarter = 0
    annualization_factor = 4.0 / quarter if quarter in (1, 2, 3, 4) else 1.0
    aliases = {
        "total_assets": "totalAssets",
        "current_assets": "currentAssets",
        "current_liabilities": "currentLiabilities",
        "retained_earnings": "retainedEarnings",
        "total_liabilities": "totalLiabilities",
        "operating_income": "operatingIncome",
        "sales": "totalRevenue",
    }
    values = {name: _number(fields.get(field)) for name, field in aliases.items()}
    values["market_value_equity"] = _number(price_info.get("marketCap"))
    periods = {name: observed_at for name in aliases}
    periods["market_value_equity"] = str(price_info.get("price_date") or "")
    complete = bool(observed_at and quarter in (1, 2, 3, 4)) and all(
        value is not None for value in values.values()
    )
    return values, periods, complete, annualization_factor


def _component(
    value: Optional[float], coefficient: float, explanation: str
) -> Dict[str, Any]:
    return {
        "value": round(float(value), 6) if value is not None else None,
        "coefficient": coefficient,
        "contribution": round(float(value) * coefficient, 6)
        if value is not None
        else None,
        "status": "available" if value is not None else "missing",
        "explanation": explanation,
    }


def _altman_formula(
    *,
    components: Mapping[str, Mapping[str, Any]],
    periods: Mapping[str, str],
) -> Dict[str, Any]:
    return {
        "type": ALTMAN_PUBLIC_COMPANY_FORMULA,
        "equation": "Z = 1.2×(working capital/total assets) + 1.4×(retained earnings/total assets) + 3.3×(EBIT/total assets) + 0.6×(market value of equity/total liabilities) + 1.0×(sales/total assets)",
        "band_rule": {
            "safe_reference": "Z > 2.99",
            "gray_zone_reference": "1.81 ≤ Z ≤ 2.99",
            "distress_reference": "Z < 1.81",
        },
        "inputs": components,
        "periods": dict(periods),
        "applicability": "Original public-company manufacturing reference; financial companies, ETFs, and business models with materially different accounting structures are excluded or require a specialized model.",
        "validation_requirement": "A Taiwan point-in-time statement panel, objectively defined financial-distress outcomes, and chronological out-of-sample tests are required before issuing a formal local rating.",
    }


def _financial_structure_formula(
    *,
    components: Mapping[str, Mapping[str, Any]],
    periods: Mapping[str, str],
    formula_type: str,
    annualization_factor: float = 1.0,
) -> Dict[str, Any]:
    """Expose both the exact and the available-data reference contracts."""
    is_quarterly_reference = formula_type == OFFICIAL_QUARTERLY_REFERENCE_FORMULA
    if is_quarterly_reference:
        equation = (
            "Z-ref = 1.2*(working capital/total assets) + 1.4*(retained earnings/total assets) + "
            f"3.3*(({annualization_factor:.4g} × year-to-date operating income)/total assets) + "
            "0.6*(market value of equity/total liabilities) + "
            f"1.0*(({annualization_factor:.4g} × year-to-date revenue)/total assets)"
        )
        applicability = (
            "Latest official Taiwan ordinary-company quarterly statement. Year-to-date operating income "
            "and revenue are annualized by 4 / reported quarter; balance-sheet values are period-end. "
        )
        profitability_input = "annualized_operating_income"
    else:
        equation = (
            "Z = 1.2*(working capital/total assets) + 1.4*(retained earnings/total assets) + "
            "3.3*(EBIT/total assets) + 0.6*(market value of equity/total liabilities) + "
            "1.0*(sales/total assets)"
        )
        applicability = "Original public-company manufacturing reference. "
        profitability_input = "ebit"
    return {
        "type": formula_type,
        "equation": equation,
        "band_rule": {
            "safe_reference": "Z or Z-ref > 2.99",
            "gray_zone_reference": "1.81 <= Z or Z-ref <= 2.99",
            "distress_reference": "Z or Z-ref < 1.81",
        },
        "reference_rating_rule": {
            "A": "above 2.99: stable financial-structure reference",
            "C": "1.81 to 2.99: watch reference",
            "E": "below 1.81: elevated-risk reference",
        },
        "profitability_input": profitability_input,
        "annualization_factor": annualization_factor
        if is_quarterly_reference
        else None,
        "inputs": components,
        "periods": dict(periods),
        "applicability": applicability
        + "Financial companies, ETFs, and materially different accounting structures are excluded or require a specialized model.",
        "validation_requirement": "A/C/E is a transparent reference tier only. A Taiwan point-in-time statement panel, objectively defined financial-distress outcomes, and chronological out-of-sample tests are required before issuing a formal local rating.",
    }


def assess_company_safety(
    stock_info: Mapping[str, Any],
    price_info: Mapping[str, Any],
    *,
    balance_sheet: Any = None,
    financials: Any = None,
    financial_snapshot: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate a public-company Altman Z reference without overclaiming.

    The formula is not applied to banks, insurers, ETFs, ETNs, REITs, or
    preferred shares.  A blank result is preferable to a false precision.
    """
    asset_type = stock_info.get("asset_type") or (
        "etf" if stock_info.get("is_etf") else "stock"
    )
    if asset_type == "etf":
        return _unavailable(
            "wrong_model", "ETF 應使用基金結構篩檢，不使用公司 Altman 公式。"
        )
    if asset_type not in {"stock", "tdr"}:
        return _unavailable(
            "specialized_product_model_pending",
            "ETN、REIT 與特別股不使用普通股公司的 Altman 公式；專用模型尚未完成。",
        )
    if _is_financial(stock_info):
        return _unavailable(
            "specialized_model_pending",
            "金融、銀行、保險與證券公司的資產負債表結構不同，不使用一般公司 Altman 公式。",
        )

    if financial_snapshot:
        values, periods, aligned, annualization_factor = _official_quarterly_inputs(
            price_info, financial_snapshot
        )
        formula_type = OFFICIAL_QUARTERLY_REFERENCE_FORMULA
        profitability_key = "operating_income"
    else:
        values, periods, aligned = _annual_statement_inputs(
            price_info, balance_sheet, financials
        )
        annualization_factor = 1.0
        formula_type = ALTMAN_PUBLIC_COMPANY_FORMULA
        profitability_key = "ebit"
    assets = values["total_assets"]
    liabilities = values["total_liabilities"]
    ratios = {
        "working_capital_to_assets": (
            (values["current_assets"] - values["current_liabilities"]) / assets
            if assets is not None
            and assets > 0
            and values["current_assets"] is not None
            and values["current_liabilities"] is not None
            else None
        ),
        "retained_earnings_to_assets": (
            values["retained_earnings"] / assets
            if assets is not None
            and assets > 0
            and values["retained_earnings"] is not None
            else None
        ),
        "ebit_to_assets": (
            (values[profitability_key] * annualization_factor) / assets
            if assets is not None
            and assets > 0
            and values[profitability_key] is not None
            else None
        ),
        "market_value_equity_to_total_liabilities": (
            values["market_value_equity"] / liabilities
            if liabilities is not None
            and liabilities > 0
            and values["market_value_equity"] is not None
            else None
        ),
        "sales_to_assets": (
            values["sales"] / assets
            if assets is not None and assets > 0 and values["sales"] is not None
            else None
        ),
    }
    components = {
        "working_capital_to_assets": _component(
            ratios["working_capital_to_assets"],
            1.2,
            "流動資產減流動負債，再除以總資產。",
        ),
        "retained_earnings_to_assets": _component(
            ratios["retained_earnings_to_assets"],
            1.4,
            "保留盈餘除以總資產。",
        ),
        "ebit_to_assets": _component(
            ratios["ebit_to_assets"], 3.3, "EBIT 除以總資產。"
        ),
        "market_value_equity_to_total_liabilities": _component(
            ratios["market_value_equity_to_total_liabilities"],
            0.6,
            "市值除以總負債。",
        ),
        "sales_to_assets": _component(
            ratios["sales_to_assets"], 1.0, "年度營收除以總資產。"
        ),
    }
    available = [
        item["contribution"]
        for item in components.values()
        if item["contribution"] is not None
    ]
    coverage = len(available) / len(components)
    formula = _financial_structure_formula(
        components=components,
        periods=periods,
        formula_type=formula_type,
        annualization_factor=annualization_factor,
    )
    if not aligned:
        result = _unavailable(
            "annual_statement_unavailable",
            "Altman 公式需要期間一致的年度財報；目前無法取得可核對的年度資產負債表與損益表。",
        )
        result.update(
            {
                "coverage": round(coverage, 2),
                "components": components,
                "formula": formula,
            }
        )
        return result
    if coverage < 1.0:
        result = _unavailable(
            "insufficient_data",
            "Altman 公式的五個必要比率未齊全，系統不以部分欄位代替完整公式。",
        )
        result.update(
            {
                "coverage": round(coverage, 2),
                "components": components,
                "formula": formula,
            }
        )
        return result

    score = round(sum(float(value) for value in available), 3)
    reference_band = (
        "safe_reference"
        if score > 2.99
        else "gray_zone_reference"
        if score >= 1.81
        else "distress_reference"
    )
    return {
        "rating": None,
        "reference_rating": (
            "A"
            if reference_band == "safe_reference"
            else "C"
            if reference_band == "gray_zone_reference"
            else "E"
        ),
        "experimental_rating": None,
        "reference_band": reference_band,
        "score": score,
        "score_label": (
            "Taiwan official quarterly financial-structure Z-ref"
            if formula_type == OFFICIAL_QUARTERLY_REFERENCE_FORMULA
            else "Altman Z-Score"
        ),
        "status": "reference_rating",
        "confidence": "reference_only",
        "coverage": 1.0,
        "target": "公司財務結構參考篩檢（不是未來 12 個月破產機率）",
        "model_version": MODEL_VERSION,
        "components": components,
        "formula": formula,
        "statement_period": next(
            (
                period
                for key, period in periods.items()
                if key != "market_value_equity" and period
            ),
            "",
        ),
        "disclaimer": "本項僅供研究與教學參考，不構成投資建議、信用評等或破產機率。",
        "note": (
            "採用可追溯的原始公開公司 Altman Z 公式與原始區間作參考；"
            "尚未完成台灣 point-in-time 財報與財務危機結果的樣本外校準，"
            "因此不產生正式 A–F 評級。"
        ),
        "deployment_gate": {
            "passed": False,
            "checks": {
                "taiwan_point_in_time_statements": False,
                "objective_distress_outcomes": False,
                "chronological_out_of_sample_validation": False,
            },
        },
    }


def assess_etf_structure(basic_info: Mapping[str, Any]) -> Dict[str, Any]:
    """Keep ETF structural checks separate from company financial safety."""
    aum = _number(basic_info.get("total_assets"))
    volume = _number(basic_info.get("avg_volume"))
    expense = _number(basic_info.get("expense_ratio"))
    premium = _number(basic_info.get("premium_pct"))
    tracking_index = basic_info.get("tracking_index")

    def item(
        value: Optional[float], score: Optional[float], note: str
    ) -> Dict[str, Any]:
        return {
            "value": value,
            "score": round(_clamp(score), 2) if score is not None else None,
            "status": "available" if score is not None else "missing",
            "explanation": note,
        }

    components = {
        "fund_size": item(
            aum,
            min(100, 30 + 20 * max(0, math.log10(aum / 1e8)))
            if aum and aum > 0
            else None,
            "較大的資產規模通常有較高的營運持續性，但不代表報酬安全。",
        ),
        "liquidity": item(
            volume,
            min(100, 25 + 20 * max(0, math.log10(volume / 1e4)))
            if volume and volume > 0
            else None,
            "成交量只是交易便利性的近似指標。",
        ),
        "cost": item(
            expense,
            100 - expense * (10000 if expense < 1 else 100)
            if expense is not None
            else None,
            "費用率越高，長期持有成本通常越高。",
        ),
        "premium_discount": item(
            premium,
            100 - abs(premium) * 12 if premium is not None else None,
            "折溢價偏離 NAV 時需注意交易價格與基金淨值不同。",
        ),
        "tracking_disclosure": item(
            1.0 if tracking_index else None,
            80 if tracking_index else None,
            "有揭露追蹤指數不代表追蹤誤差或風險已被完整評估。",
        ),
    }
    available = [
        item["score"] for item in components.values() if item["score"] is not None
    ]
    coverage = len(available) / len(components)
    if coverage < 0.6:
        result = _unavailable(
            "insufficient_data",
            "ETF 結構安全至少需要 60% 核心欄位。",
            model="etf_structure_screen_v1",
        )
        result.update(
            {
                "target": "ETF 結構與交易風險篩檢（不是成分股價格安全）",
                "coverage": round(coverage, 2),
                "components": components,
            }
        )
        return result
    score = sum(available) / len(available)
    grade = (
        "A"
        if score >= 85
        else "B"
        if score >= 70
        else "C"
        if score >= 55
        else "D"
        if score >= 40
        else "E"
        if score >= 25
        else "F"
    )
    return {
        "rating": None,
        "experimental_rating": grade,
        "reference_band": None,
        "score": round(score, 2),
        "score_label": "ETF structure screen",
        "status": "experimental_not_validated",
        "confidence": "low",
        "coverage": round(coverage, 2),
        "target": "ETF 結構與交易風險篩檢（不是成分股價格安全）",
        "model_version": "etf_structure_screen_v1",
        "components": components,
        "formula": None,
        "disclaimer": "本項僅供研究與教學參考，不構成投資建議。",
        "note": "不評估成分股未來成長、信用風險、追蹤誤差歷史或極端市場流動性。",
    }
