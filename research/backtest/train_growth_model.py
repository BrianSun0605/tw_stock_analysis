#!/usr/bin/env python3
"""Train and time-test an inspectable 12-month revenue growth model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from models.growth_features import FEATURE_NAMES, extract_growth_features, period_index  # noqa: E402


MODEL_VERSION = "growth_revenue_v1"
TARGET_DESCRIPTION = "未來連續 12 個月營收總和相對過去連續 12 個月營收總和的成長率"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_samples(frame: pd.DataFrame) -> pd.DataFrame:
    records = []
    for stock_id, group in frame.groupby("stock_id", sort=True):
        values = {
            period_index(row.year, row.month): float(row.revenue_thousand)
            for row in group.itertuples(index=False)
        }
        markets = {
            period_index(row.year, row.month): row.market
            for row in group.itertuples(index=False)
        }
        for observed in sorted(values):
            month = observed % 12 + 1
            if month not in (3, 6, 9, 12):
                continue
            history_periods = list(range(observed - 23, observed + 1))
            future_periods = list(range(observed + 1, observed + 13))
            if not all(period in values for period in history_periods + future_periods):
                continue
            history = [values[period] for period in history_periods]
            future = np.asarray(
                [values[period] for period in future_periods], dtype=float
            )
            features = extract_growth_features(history)
            trailing_sum = float(np.sum(history[-12:]))
            future_sum = float(future.sum())
            if features is None or trailing_sum < 120_000 or future_sum < 0:
                continue
            target = future_sum / trailing_sum - 1
            if not -0.8 <= target <= 3.0:
                continue
            year, observed_month = divmod(observed, 12)
            records.append(
                {
                    "stock_id": stock_id,
                    "market": markets[observed],
                    "observed_year": year,
                    "observed_month": observed_month + 1,
                    "observed_period": observed,
                    "target_growth": target,
                    **features,
                }
            )
    result = pd.DataFrame.from_records(records)
    if result.empty:
        raise RuntimeError("no model samples were created")
    return result


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> Tuple[float, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(
        design.T @ design + alpha * penalty,
        design.T @ y,
    )
    return float(coefficients[0]), coefficients[1:]


def predict(x: np.ndarray, intercept: float, coefficients: np.ndarray) -> np.ndarray:
    return np.clip(intercept + x @ coefficients, -0.8, 3.0)


def positive_probabilities(
    predictions: np.ndarray, residuals: np.ndarray
) -> np.ndarray:
    return np.asarray([float(np.mean(value + residuals > 0)) for value in predictions])


def regression_metrics(y: np.ndarray, predictions: np.ndarray) -> Dict:
    error = predictions - y
    return {
        "mae": float(np.mean(np.abs(error))),
        "median_absolute_error": float(np.median(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
    }


def classification_metrics(
    y: np.ndarray, predictions: np.ndarray, probabilities: np.ndarray
) -> Dict:
    actual = y > 0
    predicted = predictions > 0
    true_positive = int(np.sum(actual & predicted))
    false_positive = int(np.sum(~actual & predicted))
    false_negative = int(np.sum(actual & ~predicted))
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    return {
        "direction_accuracy": float(np.mean(actual == predicted)),
        "positive_precision": float(precision),
        "positive_recall": float(recall),
        "brier_score": float(np.mean((probabilities - actual.astype(float)) ** 2)),
    }


def atomic_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".model-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def write_model_card(path: Path, artifact: Dict) -> None:
    metrics = artifact["test_metrics"]
    baseline = artifact["baseline_metrics"]
    gates = artifact["deployment_gate"]
    lines = [
        "# Growth Revenue Model v1",
        "",
        "## 白話結論",
        "",
        f"- 目標：{TARGET_DESCRIPTION}。",
        f"- 測試期間：{artifact['splits']['test']}，共 {metrics['sample_count']:,} 筆。",
        f"- 模型 MAE：{metrics['mae']:.3f}；最佳基準 MAE：{baseline['best_mae']:.3f}。",
        f"- 方向命中率：{metrics['direction_accuracy']:.3f}；正成長 precision／recall：{metrics['positive_precision']:.3f}／{metrics['positive_recall']:.3f}。",
        f"- Brier score：{metrics['brier_score']:.3f}；80% 預測區間覆蓋率：{metrics['interval_80_coverage']:.3f}。",
        f"- 部署門檻：{'通過' if gates['passed'] else '未通過'}。",
        "",
        "## 資料與切分",
        "",
        "- 資料：公開資訊觀測站上市／上櫃公司每月營收官方歷史封存 HTML。",
        "- 適用範圍：上市／上櫃公司與 TDR；ETF 不適用。",
        "- 比較基準：零成長季節性基準與最近 12 個月成長率延續基準，取 MAE 較佳者。",
        "- 更新頻率：官方月營收公布後可更新個股估計；模型本身至少每年重訓並重新通過部署門檻。",
        f"- 資料 SHA-256：{artifact['training_data_sha256']}。",
        f"- 訓練：{artifact['splits']['train']}。",
        f"- 調參：{artifact['splits']['validation']}。",
        f"- 最後測試：{artifact['splits']['test']}。",
        "- 只使用觀測日以前 24 個月營收；target 使用其後 12 個月。",
        "- 訓練 target 最晚結束於 2022-12，驗證從 2023-01 才開始。",
        "",
        "## 事先門檻",
        "",
    ]
    for name, item in gates["checks"].items():
        mark = "通過" if item["passed"] else "未通過"
        lines.append(f"- {mark} {name}：{item['value']}（門檻 {item['threshold']}）")
    lines.extend(
        [
            "",
            "## 重要限制",
            "",
            "- 官方封存檔是本次下載時的修訂後版本，不是各月份當時保存的不可變快照；point-in-time 完整性未通過。",
            "- 只用營收歷史，無法預知併購、處分、停產、匯率突變、法規與一次性訂單。",
            "- 排除未來 12 個月成長低於 -80% 或高於 300% 的結構性極端樣本。",
            "- 本模型預測公司營收，不預測股價報酬，也未納入交易成本。",
            "- ETF 不適用；金融公司財務安全另用專用模型。",
            "- 取得真正 point-in-time 資料及更多滾動樣本外年份前，只能標示為實驗性模型。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def train(data_path: Path) -> Dict:
    frame = pd.read_csv(data_path, dtype={"stock_id": str})
    samples = build_samples(frame)
    train_set = samples[samples.observed_period <= period_index(2021, 12)]
    validation_set = samples[
        (samples.observed_period >= period_index(2023, 1))
        & (samples.observed_period <= period_index(2023, 12))
    ]
    test_set = samples[
        (samples.observed_period >= period_index(2024, 1))
        & (samples.observed_period <= period_index(2024, 12))
    ]
    if min(len(train_set), len(validation_set), len(test_set)) < 500:
        raise RuntimeError(
            f"insufficient time split: train={len(train_set)}, "
            f"validation={len(validation_set)}, test={len(test_set)}"
        )

    x_train_raw = train_set[FEATURE_NAMES].to_numpy(float)
    mean = x_train_raw.mean(axis=0)
    std = x_train_raw.std(axis=0)
    std[std < 1e-9] = 1.0

    def standardize(values):
        return (values - mean) / std

    x_train = standardize(x_train_raw)
    x_validation = standardize(validation_set[FEATURE_NAMES].to_numpy(float))
    x_test = standardize(test_set[FEATURE_NAMES].to_numpy(float))
    y_train = train_set.target_growth.to_numpy(float)
    y_validation = validation_set.target_growth.to_numpy(float)
    y_test = test_set.target_growth.to_numpy(float)

    candidates = []
    for alpha in (0.1, 1.0, 10.0, 100.0, 1000.0):
        intercept, coefficients = fit_ridge(x_train, y_train, alpha)
        validation_prediction = predict(x_validation, intercept, coefficients)
        candidates.append(
            (
                float(np.mean(np.abs(validation_prediction - y_validation))),
                alpha,
                intercept,
                coefficients,
                validation_prediction,
            )
        )
    _, alpha, intercept, coefficients, validation_prediction = min(
        candidates, key=lambda item: item[0]
    )
    residuals = y_validation - validation_prediction
    test_prediction = predict(x_test, intercept, coefficients)
    test_probabilities = positive_probabilities(test_prediction, residuals)
    metrics = {
        "sample_count": int(len(test_set)),
        **regression_metrics(y_test, test_prediction),
        **classification_metrics(y_test, test_prediction, test_probabilities),
    }
    low_residual, high_residual = np.quantile(residuals, [0.1, 0.9])
    metrics["interval_80_coverage"] = float(
        np.mean(
            (y_test >= test_prediction + low_residual)
            & (y_test <= test_prediction + high_residual)
        )
    )

    zero_mae = regression_metrics(y_test, np.zeros_like(y_test))["mae"]
    trailing_mae = regression_metrics(
        y_test, test_set["growth_12m_yoy"].to_numpy(float)
    )["mae"]
    best_baseline_mae = min(zero_mae, trailing_mae)
    baseline = {
        "seasonal_naive_zero_growth_mae": zero_mae,
        "trailing_12m_growth_mae": trailing_mae,
        "best_mae": best_baseline_mae,
    }
    checks = {
        "sample_count": {
            "value": int(len(test_set)),
            "threshold": ">= 1,000",
            "passed": len(test_set) >= 1000,
        },
        "mae_vs_best_baseline": {
            "value": round(metrics["mae"], 4),
            "threshold": f"<= {best_baseline_mae * 0.95:.4f} (beat by 5%)",
            "passed": metrics["mae"] <= best_baseline_mae * 0.95,
        },
        "direction_accuracy": {
            "value": round(metrics["direction_accuracy"], 4),
            "threshold": ">= 0.55",
            "passed": metrics["direction_accuracy"] >= 0.55,
        },
        "brier_score": {
            "value": round(metrics["brier_score"], 4),
            "threshold": "<= 0.24",
            "passed": metrics["brier_score"] <= 0.24,
        },
        "interval_80_coverage": {
            "value": round(metrics["interval_80_coverage"], 4),
            "threshold": "0.75 to 0.85",
            "passed": 0.75 <= metrics["interval_80_coverage"] <= 0.85,
        },
        "point_in_time_archive": {
            "value": False,
            "threshold": "must be true",
            "passed": False,
        },
    }
    return {
        "schema_version": 1,
        "model_version": MODEL_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": TARGET_DESCRIPTION,
        "applicable_assets": ["stock", "tdr"],
        "not_applicable_assets": ["etf"],
        "status": "experimental",
        "update_frequency": {
            "inference": "after official monthly revenue release",
            "retrain": "at least annually with a fresh deployment gate",
        },
        "benchmark": "best MAE of zero-growth and trailing-12-month-growth baselines",
        "features": FEATURE_NAMES,
        "feature_mean": mean.tolist(),
        "feature_std": std.tolist(),
        "intercept": intercept,
        "coefficients": coefficients.tolist(),
        "alpha": alpha,
        "residual_quantiles": [
            float(value) for value in np.quantile(residuals, np.linspace(0, 1, 101))
        ],
        "training_data_sha256": file_sha256(data_path),
        "source_url_pattern": (
            "https://mopsov.twse.com.tw/nas/t21/{sii|otc}/"
            "t21sc03_{roc_year}_{month}_0.html"
        ),
        "splits": {
            "train": "observed <= 2021-12; targets end <= 2022-12",
            "validation": "observed 2023-01 to 2023-12",
            "test": "observed 2024-01 to 2024-12; targets end <= 2025-12",
        },
        "split_sample_counts": {
            "train": int(len(train_set)),
            "validation": int(len(validation_set)),
            "test": int(len(test_set)),
        },
        "test_metrics": metrics,
        "baseline_metrics": baseline,
        "deployment_gate": {
            "passed": all(item["passed"] for item in checks.values()),
            "checks": checks,
        },
        "limitations": [
            "official archive is revision-latest, not immutable point-in-time data",
            "revenue-only model cannot anticipate structural corporate events",
            "extreme target growth outside -80% to +300% is out of scope",
            "does not predict stock returns",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "research" / "data" / "official_monthly_revenue.csv.gz",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT / "models" / "artifacts" / f"{MODEL_VERSION}.json",
    )
    parser.add_argument(
        "--model-card",
        type=Path,
        default=ROOT / "research" / "model_cards" / f"{MODEL_VERSION}.md",
    )
    args = parser.parse_args(argv)
    artifact = train(args.data)
    atomic_json(args.artifact, artifact)
    write_model_card(args.model_card, artifact)
    metrics = artifact["test_metrics"]
    print(
        json.dumps(
            {
                "gate_passed": artifact["deployment_gate"]["passed"],
                "samples": metrics["sample_count"],
                "mae": metrics["mae"],
                "direction_accuracy": metrics["direction_accuracy"],
                "brier_score": metrics["brier_score"],
                "interval_80_coverage": metrics["interval_80_coverage"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
