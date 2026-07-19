"""Separate A-F financial-safety screens for companies and ETF structure."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


MODEL_VERSION = "financial_safety_screen_v1"


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    if score >= 25:
        return "E"
    return "F"


def _is_financial(stock_info: Mapping[str, Any]) -> bool:
    value = f"{stock_info.get('name', '')} {stock_info.get('industry', '')} {stock_info.get('sector', '')}".lower()
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
        )
    )


def _unavailable(status: str, note: str, model: str = MODEL_VERSION) -> Dict[str, Any]:
    return {
        "rating": None,
        "score": None,
        "status": status,
        "confidence": "none",
        "coverage": 0.0,
        "target": "未來 12 個月公司財務出問題的風險篩檢",
        "model_version": model,
        "components": {},
        "note": note,
    }


def _component(
    value: Optional[float], score: Optional[float], explanation: str
) -> Dict[str, Any]:
    return {
        "value": value,
        "score": round(_clamp(score), 2) if score is not None else None,
        "status": "available" if score is not None else "missing",
        "explanation": explanation,
    }


def assess_company_safety(
    stock_info: Mapping[str, Any],
    price_info: Mapping[str, Any],
) -> Dict[str, Any]:
    asset_type = stock_info.get("asset_type") or (
        "etf" if stock_info.get("is_etf") else "stock"
    )
    if asset_type == "etf":
        return _unavailable("wrong_model", "ETF 應使用結構安全模型。")
    if asset_type not in {"stock", "tdr"}:
        return _unavailable(
            "specialized_product_model_pending",
            "ETN、REIT 與特別股不套用普通股公司財務公式；專用模型尚未完成。",
        )
    if _is_financial(stock_info):
        return _unavailable(
            "specialized_model_pending",
            "金融、金控、銀行與保險不套一般公司公式；專用監理模型尚未完成。",
        )

    assets = price_info.get("totalAssets")
    liabilities = price_info.get("totalLiabilities")
    current_assets = price_info.get("currentAssets")
    current_liabilities = price_info.get("currentLiabilities")
    retained = price_info.get("retainedEarnings")
    revenue = price_info.get("totalRevenue")
    operating_income = price_info.get("operatingIncome")
    net_income = price_info.get("netIncomeToCommon")

    debt_ratio = (
        liabilities / assets
        if assets and liabilities is not None and assets > 0
        else None
    )
    current_ratio = (
        current_assets / current_liabilities
        if current_assets is not None
        and current_liabilities
        and current_liabilities > 0
        else None
    )
    retained_ratio = (
        retained / assets if retained is not None and assets and assets > 0 else None
    )
    operating_margin = (
        operating_income / revenue
        if operating_income is not None and revenue and revenue > 0
        else None
    )
    net_margin = (
        net_income / revenue
        if net_income is not None and revenue and revenue > 0
        else None
    )

    components = {
        "leverage": _component(
            debt_ratio,
            100 - debt_ratio * 110 if debt_ratio is not None else None,
            "負債總額／資產總額；越低通常緩衝越大。",
        ),
        "liquidity": _component(
            current_ratio,
            min(current_ratio / 2 * 100, 100) if current_ratio is not None else None,
            "流動資產／流動負債；低於 1 代表短期償債緩衝較弱。",
        ),
        "retained_earnings": _component(
            retained_ratio,
            50 + retained_ratio * 180 if retained_ratio is not None else None,
            "保留盈餘／資產；負值代表累積虧損風險。",
        ),
        "operating_profitability": _component(
            operating_margin,
            50 + operating_margin * 250 if operating_margin is not None else None,
            "營業利益率；持續負值是營運風險訊號。",
        ),
        "net_profitability": _component(
            net_margin,
            50 + net_margin * 250 if net_margin is not None else None,
            "母公司業主淨利率；只作當期篩檢，不代表未來獲利。",
        ),
    }
    available = [
        item["score"] for item in components.values() if item["score"] is not None
    ]
    coverage = len(available) / len(components)
    if coverage < 0.6:
        result = _unavailable(
            "insufficient_data",
            "一般公司財務安全至少需要 60% 核心欄位。",
        )
        result["coverage"] = round(coverage, 2)
        result["components"] = components
        return result
    score = sum(available) / len(available)
    return {
        "rating": None,
        "experimental_rating": _grade(score),
        "score": round(score, 2),
        "status": "experimental_not_validated",
        "confidence": "low",
        "coverage": round(coverage, 2),
        "target": "未來 12 個月公司財務出問題的風險篩檢（尚未校準成機率）",
        "model_version": MODEL_VERSION,
        "components": components,
        "note": (
            "這是官方財報比率篩檢，不是破產機率；尚無台灣 point-in-time "
            "distress 標籤完成歷史驗證。"
        ),
    }


def assess_etf_structure(basic_info: Mapping[str, Any]) -> Dict[str, Any]:
    aum = basic_info.get("total_assets")
    volume = basic_info.get("avg_volume")
    expense = basic_info.get("expense_ratio")
    premium = basic_info.get("premium_pct")
    tracking_index = basic_info.get("tracking_index")
    components = {
        "fund_size": _component(
            aum,
            min(100, 30 + 20 * max(0, __import__("math").log10(aum / 1e8)))
            if aum and aum > 0
            else None,
            "基金規模較大通常清算與流動性風險較低；不代表價格不會下跌。",
        ),
        "liquidity": _component(
            volume,
            min(100, 25 + 20 * max(0, __import__("math").log10(volume / 1e4)))
            if volume and volume > 0
            else None,
            "平均成交量只反映交易便利性。",
        ),
        "cost": _component(
            expense,
            100 - float(expense) * (10000 if float(expense) < 1 else 100)
            if expense is not None
            else None,
            "費用率越高，長期追蹤拖累通常越大。",
        ),
        "premium_discount": _component(
            premium,
            100 - abs(float(premium)) * 12 if premium is not None else None,
            "市價相對 NAV 的溢折價絕對值越小越好。",
        ),
        "tracking_disclosure": _component(
            1.0 if tracking_index else None,
            80 if tracking_index else None,
            "有官方追蹤指數資訊只代表結構可辨識，不代表成分安全。",
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
        result["target"] = "ETF 結構與交易風險篩檢"
        result["coverage"] = round(coverage, 2)
        result["components"] = components
        return result
    score = sum(available) / len(available)
    return {
        "rating": None,
        "experimental_rating": _grade(score),
        "score": round(score, 2),
        "status": "experimental_not_validated",
        "confidence": "low",
        "coverage": round(coverage, 2),
        "target": "ETF 結構與交易風險篩檢（不是成分股價格安全）",
        "model_version": "etf_structure_screen_v1",
        "components": components,
        "note": "不評估成分股未來成長、信用風險、追蹤誤差歷史或極端市場流動性。",
    }
