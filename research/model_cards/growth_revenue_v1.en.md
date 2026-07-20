# Growth Revenue Model v1

> **Historical version / not the current implementation.** The active model is [`growth_revenue_v2.en.md`](growth_revenue_v2.en.md). Version 2 fixes the revenue-scale feature, uses ridge plus shrinkage and median-residual calibration, and documents an explicit research/education growth reference tier. Formal A–F has still not passed its deployment gates.

## Plain-Language Conclusion

- Objective: the growth rate of the next rolling 12-month revenue total relative to the prior rolling 12-month revenue total.
- Test period: observed 2024-01 to 2024-12; targets end <= 2025-12; 6,619 records in total.
- Model MAE: 0.182; best baseline MAE: 0.179.
- Direction accuracy: 0.629; positive-growth precision/recall: 0.630/0.977.
- Brier score: 0.231; 80% prediction-interval coverage: 0.825.
- Deployment gate: not passed.

## Data and Splits

- Data: official historical-archive HTML for monthly revenue of listed/OTC companies from the Market Observation Post System.
- Scope: listed/OTC companies and TDRs; ETFs do not apply.
- Benchmarks: a zero-growth seasonal baseline and a continuation baseline using the most recent 12-month growth rate; the lower-MAE baseline is used.
- Update frequency: individual-security estimates can update after official monthly revenue announcements; the model itself must be retrained at least annually and pass the deployment gate again.
- Data SHA-256: `f06d65842ed77e913971a74d163834cc71e1cc9a162aaa17573d9529e87407ab`.
- Training: observed <= 2021-12; targets end <= 2022-12.
- Tuning: observed 2023-01 to 2023-12.
- Final test: observed 2024-01 to 2024-12; targets end <= 2025-12.
- Only the 24 months of revenue before the observation date are used; the target uses the following 12 months.
- Training targets end no later than 2022-12; validation begins only from 2023-01.

## Pre-Specified Gates

- Passed `sample_count`: 6619 (threshold >= 1,000)
- Did not pass `mae_vs_best_baseline`: 0.1824 (threshold <= 0.1699 (beat by 5%))
- Passed `direction_accuracy`: 0.6289 (threshold >= 0.55)
- Passed `brier_score`: 0.2312 (threshold <= 0.24)
- Passed `interval_80_coverage`: 0.8249 (threshold 0.75 to 0.85)
- Did not pass `point_in_time_archive`: False (threshold must be true)

## Important Limitations

- Official archive files are revised versions downloaded at the present time, not immutable snapshots saved when each month was announced; point-in-time completeness is not passed.
- Revenue history alone cannot foresee mergers, disposals, production stoppages, sudden exchange-rate changes, regulation, or one-off orders.
- Structural extreme samples with future 12-month growth below -80% or above 300% are excluded.
- This model forecasts company revenue, not stock-price return, and does not include transaction costs.
- ETFs do not apply; financial-company safety requires a specialized model.
- Until genuinely point-in-time data and more rolling out-of-sample years are obtained, the model can only be labeled experimental.
