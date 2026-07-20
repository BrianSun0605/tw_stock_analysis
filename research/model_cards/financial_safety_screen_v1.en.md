# Financial Safety Screen v1

> **Historical version / not the current implementation.** Arbitrary 0–100 weighting and experimental A–F are no longer used. See [`financial_structure_reference_v3.en.md`](financial_structure_reference_v3.en.md) for the active ordinary-company rule; financial and inapplicable assets must still stop rather than be filled with an old score.

## Plain-Language Conclusion

- This is a financial-ratio screen for ordinary companies. It is not a guarantee that a company will not fail in the future, nor is it a calibrated bankruptcy probability.
- A–F only indicates the relative strength of buffers under the same rule set. The interface must also show “experimental screen” and data coverage.
- Financial holding companies, banks, securities firms, and insurers do not use the ordinary-company formula. Version 1 returns “specialized model not complete.”
- ETFs use a separate structural-safety screen and do not display company-style growth ratings.

## Inputs for Ordinary Companies

- Total liabilities / total assets.
- Current assets / current liabilities.
- Retained earnings / total assets.
- Operating margin.
- Net margin attributable to the parent company.

At least 60% of fields are required before outputting A–F. Missing data is not replaced with zero points.

## Objective and Validation Status

- Intended question: is the risk of a company encountering financial problems in the next 12 months relatively high?
- Current answer only: are the financial buffers in the latest official financial statements relatively weak?
- Scope: ordinary listed/OTC companies. Financial holding companies, banks, securities firms, insurers, and ETFs are handled separately.
- Benchmark: no Taiwan point-in-time distress labels exist to establish a predictive benchmark. It can currently be compared only with “do not issue a rating,” so it must not claim predictive superiority.
- Update frequency: recalculate after every official quarterly financial-statement update. If a historical model is completed in the future, retrain and recalibrate at least annually.
- Taiwan point-in-time financial statements, delisting/restructuring/financial-distress outcome labels, and temporally ordered out-of-sample tests are still missing. Therefore the status is `experimental_not_validated`; formal grades remain blank and only an explicitly labeled experimental grade is shown.
- Before labels and out-of-sample validation are complete, do not call the score a bankruptcy probability or treat Grade A as investment advice.

## ETF Boundary

Version 1 of the ETF screen considers only fund size, trading volume, expense ratio, premium/discount, and disclosure of the tracked asset. It does not assess future growth of constituents or guarantee market-price safety.
