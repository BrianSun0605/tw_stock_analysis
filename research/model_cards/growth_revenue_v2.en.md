# Growth Revenue Model v2

## Plain-language conclusion

- Target: growth of the next rolling 12-month revenue total relative to the preceding rolling 12-month revenue total.
- Final untouched test period: observations from 2024-01 through 2024-12, with targets ending no later than 2025-12; 6,619 samples.
- Model MAE: 0.170; best predefined baseline MAE: 0.179.
- Validation-selected formula: ridge regression plus monotonic shrinkage and median-MAE calibration; 105 candidates; validation MAE: 0.177.
- Direction accuracy: 0.648; positive-growth precision/recall: 0.674 / 0.839.
- Brier score: 0.231; 80% interval coverage: 0.824.
- Deployment gate: not passed.

## Data and time split

- Data: official MOPS monthly-revenue archive HTML for TWSE-listed and TPEx-listed companies.
- Scope: listed/OTC companies and TDRs; ETFs do not apply.
- Baseline: the lower MAE of the zero-growth seasonal-naive baseline and the trailing-12-month-growth continuation baseline.
- Refresh: an individual reference estimate may refresh after an official monthly-revenue release. The model itself must be retrained at least annually and pass the deployment gate again.
- Data SHA-256: `f06d65842ed77e913971a74d163834cc71e1cc9a162aaa17573d9529e87407ab`.
- Train: observations through 2021-12; targets end no later than 2022-12.
- Validation: observations from 2023-01 through 2023-12.
- Final test: observations from 2024-01 through 2024-12; targets end no later than 2025-12.
- The formula uses only the 24 monthly revenues available on or before the observation date; its target uses the following 12 months.
- The training targets end no later than 2022-12, so validation begins only in 2023-01.
- Population coverage: 1,849 source issuers, 1,732 eligible issuers, and 1,696 listed/OTC issuers in the final test. This is a broad market panel, not a single-security or single-industry test.

## Formula and selection

The runtime calculation is intentionally inspectable:

```text
raw = clip(-0.80, 3.00, intercept + Σ coefficient_i × ((feature_i - mean_i) / std_i))
prediction = clip(-0.80, 3.00, shrinkage × raw + median_calibration_offset)
```

The nine features are 3-, 6-, and 12-month year-over-year revenue growth; growth acceleration; recent 3-month momentum; monthly YoY volatility; annualized log-revenue trend; seasonality variation; and log10 trailing-12-month revenue scale. The scale feature was corrected from a previously clipped natural-log value that was constant for eligible issuers.

The 105 predeclared candidates combine five ridge penalties with shrinkage values from 0 to 1 in 0.05 steps. Each candidate receives a median residual offset on the validation period because MAE is minimized by a median, not a mean. The 2024 test period is not used to select a candidate or its offset.

If all future deployment gates pass, the displayed A–F rule is:

- A: estimate at least 15% and positive-growth likelihood at least 80%.
- B: estimate at least 8% and positive-growth likelihood at least 70%.
- C: non-negative estimate and positive-growth likelihood at least 58%.
- D: positive-growth likelihood at least 42%.
- E: positive-growth likelihood at least 30%.
- F: otherwise.

Until then, this rule can produce only an explicitly labelled experimental reference, not a formal rating.

## Predefined gates

- Pass — `sample_count`: 6,619 (threshold `>= 1,000`).
- Fail — `mae_vs_best_baseline`: 0.1703 (threshold `<= 0.1699`, a 5% improvement).
- Pass — `direction_accuracy`: 0.6484 (threshold `>= 0.55`).
- Pass — `brier_score`: 0.2314 (threshold `<= 0.24`).
- Pass — `interval_80_coverage`: 0.8243 (threshold 0.75 to 0.85).
- Fail — `point_in_time_archive`: false (threshold must be true).

## Important limitations

- The official archive is the latest revision downloaded for this research, not an immutable snapshot captured on each historical date; therefore point-in-time integrity is not demonstrated.
- Revenue history alone cannot anticipate mergers, disposals, shutdowns, exchange-rate shocks, regulation, or one-off orders.
- Structural extremes with next-12-month growth below -80% or above +300% are outside the model's scope.
- The model estimates company revenue, not stock returns, and it does not include trading costs.
- ETFs do not apply; financial-company safety needs a specialized model.
- Until true point-in-time data and additional rolling out-of-sample years are available, the result remains experimental.
- This is for research and education only, not investment advice or a return guarantee.

## Current product display

The application now displays the existing A–F rule as a clearly labelled **growth reference tier** even while the stricter formal deployment gate remains incomplete. It is derived only from this model's revenue-growth estimate and empirical positive-growth likelihood. It is not a formal rating, price target, investment-return forecast, recommendation, or guarantee.
