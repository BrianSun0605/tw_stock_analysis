# Taiwan Official Quarterly Financial-Structure Reference v3

## Purpose and output contract

This rule uses the latest official TWSE/TPEx quarterly statement for an ordinary company and returns a traceable financial-structure *reference tier*. It is not a bankruptcy probability, credit rating, investment recommendation, or price forecast. The formal financial-safety rating remains blank until Taiwan historical validation is complete.

It applies only to ordinary companies and TDRs. Financial, insurance, and securities firms, ETFs, ETNs, REITs, and materially different accounting structures are out of scope; the system must stop rather than force a tier.

## Available data and formula

The TWSE/TPEx `ci` endpoints provide same-period total assets, current assets, current liabilities, retained earnings, total liabilities, operating income, and revenue. They do not provide original EBIT. v3 therefore does not claim to be original Altman Z: it explicitly uses operating income as an operating-profit proxy and annualizes year-to-date flow values by `4 / reported quarter`.

```text
Z-ref = 1.2 × (working capital / total assets)
      + 1.4 × (retained earnings / total assets)
      + 3.3 × ((4 / quarter) × year-to-date operating income / total assets)
      + 0.6 × (market value of equity / total liabilities)
      + 1.0 × ((4 / quarter) × year-to-date revenue / total assets)
```

Market capitalization is the latest available market value. Every other required input must come from the same official quarterly statement. Missing inputs are never replaced by zero, another period, or another ratio.

## Reference tiers

| Reference tier | Z-ref range | Display meaning |
|---|---:|---|
| A | Above 2.99 | Relatively stable financial-structure reference signal |
| C | 1.81 to 2.99 | Watch reference signal |
| E | Below 1.81 | Elevated financial-structure-risk reference signal |

These are transparent rule-based references, not probabilities calibrated to Taiwanese default, delisting, or bankruptcy outcomes. Annualization can be distorted by seasonality or one-off items and must not be used as a stand-alone trading decision.

## Coverage audit and limitations

The 2026-07-20 official-endpoint audit covered 1,927 TWSE/TPEx ordinary companies. The balance-sheet core fields and operating income were available, but original EBIT was available for zero issuers. v3 therefore names its proxy and disclaimer instead of silently substituting a field while claiming original Altman Z.

Until announcement-date-reproducible statements, objectively defined financial-distress outcomes, and chronological out-of-sample validation exist, A/C/E must not be presented as a formal Taiwan credit or bankruptcy rating.
