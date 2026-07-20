# Audit Report — English Edition

Updated: 2026-07-20. The Chinese audit report remains the source-preserving evidence log: [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md).

## Current conclusion

The application is a local, research-oriented beta with official-source prioritization, explicit source status, task/resource limits, and regression tests. It must not be represented as a validated stock-prediction or bankruptcy-prediction product.

## 2026-07-20 post-audit update

The body of the Chinese audit report preserves the 2026-07-18/19 evidence and decisions and is not retroactively presented as a new audit. Later feature, model-reference, bilingual, and test progress is synchronized in [PROGRESS.en.md](PROGRESS.en.md) and [DEVELOPMENT_HANDOFF.en.md](DEVELOPMENT_HANDOFF.en.md). The latest full automated check after this documentation sync is 123 pytest tests passed, plus Ruff, compilation, and `pip check`.

- English UI, CSV, Investment Learning Lab, and PDFs have been completed. English PDF PEG, risk-signal, and analysis narrative text is built from structured data in English, while company names, news, and other raw source text remain unchanged.
- Investment Learning Lab now contains seven tracks, 44 concepts, and 220 local bilingual questions with track/level selection, missed-question review, starred key questions, and clear-answer-records. Source verification rules are in `docs/INVESTMENT_LEARNING_SOURCES.en.md`.
- Growth shows only a constrained research/education reference tier. Ordinary-company financial safety uses the transparent `financial_structure_reference_v3` Z-ref A/C/E reference. Neither is a formal validated rating; the audit's existing concerns about point-in-time data, distress labels, and validation remain applicable.

## Latest verified fixes

| ID | Outcome | Evidence |
|---|---|---|
| DBG-041 | PDF Chinese-glyph corruption fixed with a TrueType CIDFontType2 path. | `report/`, `tests/test_report_render.py` |
| DBG-042 | Official revenue charts now join the latest OpenAPI period with 24 months of MOPS history. | `stock/data.py`, `stock/mops_history.py` |
| DBG-043 | ETF identity/AUM survives Yahoo failure; company-only cards are not used for ETFs. | `stock/data.py`, `static/js/render.js` |
| DBG-044 | Beginner KPI groups distinguish price/valuation, business health/growth, and income; ETF groups use NAV, fund structure, and trading/income. | `templates/`, `static/` |
| DBG-045 | Language selection is retained per task; an English PDF path and English UI foundation were added while preserving raw official text. | `static/js/i18n.js`, `webui.py`, `report/generator.py` |

## Remaining high-priority work

1. Build reproducible point-in-time data and walk-forward validation before enabling formal grades.
2. Define auditable financial-distress labels for the safety model.
3. Obtain stable, authorized ETF holdings data before building holdings-weighted ETF analysis.
4. Complete accessibility and Windows signing work before broad public distribution.
