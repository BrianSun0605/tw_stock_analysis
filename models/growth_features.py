"""Feature contract shared by revenue-growth research and runtime inference."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

import numpy as np


FEATURE_NAMES = [
    "growth_3m_yoy",
    "growth_6m_yoy",
    "growth_12m_yoy",
    "growth_acceleration",
    "recent_momentum",
    "monthly_yoy_volatility",
    "log_revenue_trend_annualized",
    "seasonality_variation",
    "log_trailing_revenue",
]


def period_index(year: int, month: int) -> int:
    return int(year) * 12 + int(month) - 1


def extract_growth_features(values: Iterable[float]) -> Optional[Dict[str, float]]:
    history = np.asarray(list(values), dtype=float)
    if (
        history.shape != (24,)
        or not np.all(np.isfinite(history))
        or np.any(history < 0)
    ):
        return None
    previous = history[:12]
    current = history[12:]
    if previous.sum() <= 0 or current.sum() <= 0:
        return None

    def growth(months: int) -> float:
        denominator = previous[-months:].sum()
        return current[-months:].sum() / denominator - 1 if denominator > 0 else 0.0

    growth_3m = growth(3)
    growth_6m = growth(6)
    growth_12m = growth(12)
    previous_three = current[-6:-3].sum()
    momentum = current[-3:].sum() / previous_three - 1 if previous_three > 0 else 0.0
    monthly_yoy = (
        np.divide(
            current,
            previous,
            out=np.zeros_like(current),
            where=previous > 0,
        )
        - 1
    )
    x = np.arange(12, dtype=float)
    slope = float(np.polyfit(x, np.log1p(current), 1)[0])
    annualized_trend = float(np.expm1(np.clip(slope * 12, -3, 3)))
    mean_current = float(current.mean())
    seasonality = float(current.std() / mean_current) if mean_current > 0 else 0.0
    raw = {
        "growth_3m_yoy": growth_3m,
        "growth_6m_yoy": growth_6m,
        "growth_12m_yoy": growth_12m,
        "growth_acceleration": growth_3m - growth_12m,
        "recent_momentum": momentum,
        "monthly_yoy_volatility": float(np.std(np.clip(monthly_yoy, -3, 5))),
        "log_revenue_trend_annualized": annualized_trend,
        "seasonality_variation": seasonality,
        "log_trailing_revenue": float(np.log1p(current.sum())),
    }
    return {name: float(np.clip(raw[name], -5.0, 8.0)) for name in FEATURE_NAMES}


def feature_vector(features: Mapping[str, float]) -> np.ndarray:
    return np.asarray([float(features[name]) for name in FEATURE_NAMES], dtype=float)
