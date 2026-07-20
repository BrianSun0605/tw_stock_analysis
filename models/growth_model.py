"""Runtime contract for the experimental 12-month revenue growth model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

import numpy as np

from models.growth_features import extract_growth_features, feature_vector


ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "growth_revenue_v2.json"


def _reference_grade(prediction: float, probability: float) -> str:
    """Return a transparent educational tier, not a validated credit grade.

    The thresholds are stored with the model artifact and combine the model's
    expected 12-month revenue growth with its empirical positive-growth share.
    They remain available even while the stricter *formal* deployment gate is
    incomplete, because hiding a useful, clearly labelled reference tier does
    not improve the underlying evidence.
    """
    if prediction >= 0.15 and probability >= 0.80:
        return "A"
    if prediction >= 0.08 and probability >= 0.70:
        return "B"
    if prediction >= 0 and probability >= 0.58:
        return "C"
    if probability >= 0.42:
        return "D"
    if probability >= 0.30:
        return "E"
    return "F"


def unavailable(status: str, note: str) -> Dict[str, Any]:
    return {
        "rating": None,
        "reference_rating": None,
        "experimental_rating": None,
        "status": status,
        "target": "未來連續 12 個月營收成長",
        "prediction": None,
        "prediction_interval_80": None,
        "positive_growth_probability": None,
        "confidence": "none",
        "secondary_eps_target": {
            "status": "not_validated",
            "target": "未來 EPS 成長",
            "note": "目前沒有通過 point-in-time 回測的台股 EPS 預測模型。",
        },
        "formula": None,
        "disclaimer": "本項為研究與教學參考，不構成投資建議或報酬保證。",
        "note": note,
    }


def assess_revenue_growth(
    records: List[Mapping[str, Any]],
    stock_info: Mapping[str, Any],
) -> Dict[str, Any]:
    asset_type = stock_info.get("asset_type") or (
        "etf" if stock_info.get("is_etf") else "stock"
    )
    if asset_type == "etf":
        return unavailable("not_applicable", "ETF 不套用公司營收成長模型。")
    if asset_type not in {"stock", "tdr"}:
        return unavailable(
            "specialized_product_model_pending",
            "ETN、REIT 與特別股不套用普通股公司營收模型；專用模型尚未完成。",
        )
    if not ARTIFACT_PATH.is_file():
        return unavailable("model_missing", "找不到已驗證的成長模型 artifact。")
    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    ordered = sorted(records, key=lambda item: (item["year"], item["month"]))
    required_history = int(artifact.get("history_months", 24))
    if required_history < 24 or required_history > 60:
        return unavailable("model_incompatible", "成長模型的歷史資料需求設定無效。")
    if len(ordered) < required_history:
        return unavailable(
            "insufficient_data", f"至少需要連續 {required_history} 個月官方營收。"
        )
    window = ordered[-required_history:]
    periods = [int(item["year"]) * 12 + int(item["month"]) - 1 for item in window]
    if any(current - previous != 1 for previous, current in zip(periods, periods[1:])):
        return unavailable("insufficient_data", "最近 24 個月營收不連續。")
    features = extract_growth_features([float(item["revenue"]) for item in window])
    if features is None:
        return unavailable("insufficient_data", "營收資料包含負值或無法計算。")
    vector = feature_vector(features)
    mean = np.asarray(artifact["feature_mean"], dtype=float)
    std = np.asarray(artifact["feature_std"], dtype=float)
    coefficients = np.asarray(artifact["coefficients"], dtype=float)
    if not (vector.shape == mean.shape == std.shape == coefficients.shape):
        return unavailable(
            "model_incompatible", "成長模型的特徵定義與 artifact 不一致。"
        )
    standardized = (vector - mean) / std
    raw_prediction = float(
        np.clip(
            float(artifact["intercept"]) + standardized @ coefficients,
            -0.8,
            3.0,
        )
    )
    shrinkage = float(artifact.get("shrinkage", 1.0))
    calibration_offset = float(artifact.get("median_calibration_offset", 0.0))
    prediction = float(
        np.clip(raw_prediction * shrinkage + calibration_offset, -0.8, 3.0)
    )
    residuals = np.asarray(artifact["residual_quantiles"], dtype=float)
    probability = float(np.mean(prediction + residuals > 0))
    low = float(np.clip(prediction + residuals[10], -0.8, 3.0))
    high = float(np.clip(prediction + residuals[90], -0.8, 3.0))
    in_distribution = bool(np.max(np.abs(standardized)) <= 4)
    gate_passed = bool(artifact.get("deployment_gate", {}).get("passed"))
    confidence = "low"
    if gate_passed and in_distribution:
        confidence = "high" if high - low <= 0.25 else "medium"
    formula = dict(artifact.get("formula") or {})
    formula.update(
        {
            "history_months": required_history,
            "intercept": float(artifact["intercept"]),
            "shrinkage": shrinkage,
            "median_calibration_offset": calibration_offset,
            "features": [
                {
                    "name": name,
                    "coefficient": float(coefficient),
                    "mean": float(center),
                    "std": float(scale),
                    "value": float(features[name]),
                }
                for name, coefficient, center, scale in zip(
                    artifact.get("features", []), coefficients, mean, std
                )
            ],
        }
    )
    failed_checks = [
        key
        for key, check in (
            artifact.get("deployment_gate", {}).get("checks") or {}
        ).items()
        if not check.get("passed")
    ]
    reference_rating = _reference_grade(prediction, probability)
    source_names = sorted(
        {str(item.get("source") or "") for item in window if item.get("source")}
    )
    input_source = ", ".join(source_names) if source_names else "Revenue data"
    uses_fallback = any(str(item.get("status") or "") == "fallback" for item in window)
    return {
        # ``rating`` deliberately remains reserved for a future formal grade.
        # The product now shows this usable tier under its honest label rather
        # than blocking all output on a stricter research-deployment gate.
        "rating": _reference_grade(prediction, probability) if gate_passed else None,
        "reference_rating": reference_rating,
        "experimental_rating": reference_rating,
        "rating_scheme": "revenue_growth_reference_tier_v1",
        "status": "validated" if gate_passed else "reference_estimate",
        "target": artifact["target"],
        "prediction": prediction,
        "prediction_pct": round(prediction * 100, 2),
        "prediction_interval_80": {
            "low": low,
            "high": high,
            "low_pct": round(low * 100, 2),
            "high_pct": round(high * 100, 2),
        },
        "positive_growth_probability": probability,
        "confidence": confidence,
        "observed_through": f"{window[-1]['year']}-{int(window[-1]['month']):02d}",
        "model_version": artifact["model_version"],
        "test_metrics": artifact["test_metrics"],
        "deployment_gate": artifact["deployment_gate"],
        "feature_values": features,
        "formula": formula,
        "input_source": input_source,
        "input_uses_fallback": uses_fallback,
        "secondary_eps_target": {
            "status": "not_validated",
            "target": "未來 EPS 成長",
            "note": "官方季度 EPS 歷史尚未完成 point-in-time 回測，因此不產生第二個預測數字。",
        },
        "disclaimer": "本項為研究與教學參考，不構成投資建議或報酬保證。",
        "note": (
            "正式評級仍停用：未通過的部署門檻為 "
            + "、".join(failed_checks)
            + "。目前僅顯示可追溯公式的參考估計，不預測股價或投資報酬。"
            if not gate_passed
            else ""
        ),
    }
