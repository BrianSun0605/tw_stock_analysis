# Financial-Structure Reference Formula v2

> **Historical version / not the current implementation.** The active rule is [`financial_structure_reference_v3.en.md`](financial_structure_reference_v3.en.md), using same-period fields available from current official quarterly data and transparent A/C/E Z-ref reference tiers. Version 2 remains as a research record of the exact-EBIT availability limitation and the annual original-Altman-Z path.

## Plain-language conclusion

- This version removes the arbitrary 0–100 weighting that previously produced A–F grades.
- Ordinary non-financial TWSE/TPEx companies now use the traceable original public-company Altman Z formula. It outputs an original-formula reference band, not a formal Taiwan financial-safety grade.
- The formula examines financial structure. It is not a 12-month bankruptcy probability, credit rating, share-price forecast, or investment recommendation.
- Financial holding companies, banks, securities firms, insurers, ETFs, ETNs, REITs, and preferred shares do not use this company formula. A blank result is more correct than an inapplicable score.

## Formula, inputs, and bands

```text
Z = 1.2 × (working capital / total assets)
  + 1.4 × (retained earnings / total assets)
  + 3.3 × (EBIT / total assets)
  + 0.6 × (market value of equity / total liabilities)
  + 1.0 × (annual sales / total assets)
```

- Working capital = current assets − current liabilities.
- All five ratios must be available, and the balance sheet and income statement must be verifiably aligned to the same annual period. A missing value is never replaced with a neutral or proxy score.
- Original public-company reference bands: `Z > 2.99` is above the safe reference; `1.81 ≤ Z ≤ 2.99` is the gray zone; `Z < 1.81` is below the distress reference.
- The interface must show each ratio, coefficient, contribution, statement period, and the complete formula. A band label is not a formal A–F grade.

## Rationale and scope boundary

- The five inputs represent liquidity, accumulated profitability/company maturity, operating profitability, market-equity buffer, and asset-use efficiency. They were not selected arbitrarily because they produce a favorable result for one company.
- The coefficients and bands originate in Altman's public-company Z-Score research on listed manufacturing companies. Taiwan industries, accounting structures, and definitions of distress may differ, so this can only be an interpretable financial-structure reference.
- Original source: Altman, E. I. (1968), *Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy*, *The Journal of Finance*, 23(4), 589–609, https://doi.org/10.1111/j.1540-6261.1968.tb00843.x.
- Financial firms are excluded because their leverage, liquidity, and capital adequacy require a specialized model and regulatory measures.

## Market-wide data audit and claims that cannot yet be made

- A field-coverage audit was run against the current TWSE/TPEx official `ci` ordinary-company financial-statement OpenAPIs: 1,043 listed issuers and 884 OTC issuers, 1,927 paired income/balance statements in total. All 1,927 had the five required balance-sheet fields.
- In the same official OpenAPI audit, an exact `EBIT` field was available for zero issuers. Therefore the app must not claim that the original annual Altman formula can be rebuilt market-wide using only that current OpenAPI. The code calculates only when all five required inputs are available in reconcilable annual statements.
- Market capitalization is also absent from those statement APIs and needs price data with a stated date. The app exposes input periods and must not silently mix periods.
- This is an operational audit of currently available fields, not a predictive-accuracy backtest.

## Formal deployment gates

Until all three conditions below are fulfilled, `rating` must remain blank and only `reference_band` may be displayed:

1. A Taiwan-company point-in-time annual/quarterly statement panel with an availability date for every observation.
2. Objective, auditable financial-distress outcome labels. Delisting lists must distinguish bankruptcy, reorganization, and financial abnormality from mergers, voluntary delistings, and other non-distress reasons.
3. Chronological train, validation, and held-out tests that compare calibration, discrimination, and error against “issue no rating” and other predeclared baselines.

Official outcome-data starting points include the TWSE [de-listed companies list](https://www.twse.com.tw/zh/listed/suspend-listing.html) and TPEx [de-listed companies list](https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html). No implementation may treat every delisting as bankruptcy before reason classification and financial-statement alignment are complete.

## Disclaimer

This feature is for research and education only. It is not investment advice, a return guarantee, a credit rating, or a bankruptcy probability. Even a result above the original safe reference cannot prevent a share-price decline or corporate event that financial statements do not promptly capture.
