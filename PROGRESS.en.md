# Project Progress

Updated: 2026-07-20

## Completed

- [x] Phase 0: master-list search, peers, date fields, on-demand PDFs, single-worker operation, and file isolation.
- [x] Phase 1: official monthly revenue/financial statements, per-field provenance, Yahoo fallback, shared market snapshot, SQLite cache, three-day PDF retention, cancellation, and resource limits.
- [x] Safe-to-release parts of Phase 2: growth and safety contracts are fully separate and are not averaged; ETF and financial-sector applicability boundaries are implemented; formal A–F remains blank when historical gates are not passed.
- [x] Program-verifiable parts of Phase 3: separate fact/model sections, news section, comparison, combobox, focus, 44 px touch targets, UI rules, Noto OFL, third-party and privacy documentation, pinned versions, and CI.
- [x] Phase 4 portable and installer: LocalAppData, read-only bundle, single instance, loopback, on-demand PDFs, versioning, ZIP, Setup EXE, and SHA-256.
- [x] Official master expansion: schema 4 with 2,773 entries, including Emerging Stock Market securities, ETFs, ETNs, preferred shares, and REITs; warrants excluded; alphanumeric codes can be entered directly.
- [x] Complete checks: 127 pytest cases, Ruff, pip check, pip-audit, and 10 JavaScript syntax checks passed; a smoke test using 2330's official 24-month revenue and real 0050 ETF data passed.
- [x] Inno Setup 6.7.3 installer completed: actual installation, launch, duplicate launch, normal shutdown, and uninstall all passed; uninstallation retains user data.
- [x] Real browser acceptance completed: keyboard search, full analysis, 300 px mobile, 627 px tablet, 1187 px desktop, PDF 13/13, result focus, and console all passed.
- [x] Fixed full-page horizontal scrolling on mobile and a background EXE remaining after shutdown; both have regression tests, and the final packaged App was rerun for confirmation.
- [x] Fixed Traditional Chinese PDF garbling: PDF text now uses the Noto Sans TC TrueType font and is confirmed to be emitted as CIDFontType2; OTF remains in use for Matplotlib charts.
- [x] Fixed official monthly-revenue trends: the latest TWSE/TPEx period is combined with the MOPS official historical archive to complete 24 months, and MoM/YoY missing from archived data are derived.
- [x] ETF structure and beginner UI: official ETF identity, tracking index, and TPEx AUM remain available even when Yahoo fails. ETFs use market price and NAV/fund structure/trading and income; ordinary shares use price and valuation/company quality and growth/income groups.
- [x] Investment Basics MVP: 12 beginner interactive tasks, answer feedback and common misconceptions, quick lessons beside stock/ETF indicators, and local browser progress; educational content does not give buy/sell advice.

## Not Completed / Must Not Be Presented as Complete

- [ ] Growth data is still not a point-in-time version for each announcement, and the formal growth rating has not passed the pre-defined MAE threshold.
- [ ] Ordinary-company financial safety still lacks Taiwan historical-distress outcome labels and point-in-time statements. It currently shows only an Altman Z financial-structure reference band, not a bankruptcy probability or a formal Taiwan rating.
- [ ] An ETF constituent-weighted growth model and specialized regulatory models for financial/insurance companies remain to be built.
- [ ] ETNs, REITs, and preferred shares are searchable, but specialized analysis models are unfinished; processing explicitly stops rather than incorrectly applying ordinary-share formulas.
- [ ] Axe and a physical screen reader have not yet been run. Basic DOM accessibility checks in the browser passed, but are not represented as Axe or real assistive-technology acceptance.
- [ ] The Setup EXE and main executable currently have no Windows digital signature; public distribution may show a SmartScreen warning.
- [ ] Uninstallation removes all program contents but currently leaves an empty installation-data folder. It does not affect the program or user data and is recorded as a low-priority cleanup issue.
- [x] Formal open-source license: MIT License, Copyright (c) 2026 Fat Cat Game Studio; the source code, portable build, and installer all include LICENSE.
- [x] CI now includes pip-audit; no known vulnerabilities were found in current runtime dependencies.
- [x] Ruff formatted existing Python files; 67 Python files pass `ruff format --check`, and CI includes a formatting gate.

## Locations of Major Results

- Usage and architecture: [README.md](README.md)
- Complete evidence and checklist: [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md)
- Windows portable: [release/TWStockAnalysis-portable-0.2.0-dev.zip](release/TWStockAnalysis-portable-0.2.0-dev.zip)
- Windows installer: [release/TWStockAnalysis-Setup-0.2.0-dev.exe](release/TWStockAnalysis-Setup-0.2.0-dev.exe)
- Open-source license: [LICENSE](LICENSE)
- Checksums: [release/SHA256SUMS.txt](release/SHA256SUMS.txt)

## 2026-07-20: Investment Learning Lab expansion

- [x] Expanded Investment Learning Lab from 12 single beginner challenges to seven tracks, 44 concepts, and 220 local bilingual questions covering foundations; candlesticks and price charts; financials and valuation; ETFs; industries; news literacy; and strategy and risk.
- [x] Added track cards, levels 1–5, overall and track progress, missed-question review, rotated answer positions, illustrative chart concepts, and a source link for every question; existing 12-question completion records migrate forward.
- [x] Re-authored questions from verifiable SEC Investor.gov, SEC, FINRA, and Taiwan Stock Exchange education material. The production app neither fetches course questions nor transmits learning data.
- [x] Added equivalent Chinese and English source and maintenance records: [docs/INVESTMENT_LEARNING_SOURCES.md](docs/INVESTMENT_LEARNING_SOURCES.md) / [docs/INVESTMENT_LEARNING_SOURCES.en.md](docs/INVESTMENT_LEARNING_SOURCES.en.md).
- [x] Reset existing answer records and added a Clear answer records control plus starred key questions. Clearing completion and missed-question records does not remove key questions.

## 2026-07-20: Traceable growth and financial-safety formulas

- [x] Fixed the growth model's revenue-scale feature, which had been clipped to a constant. Adopted the validation-selected ridge + shrinkage + median-residual calibration v2 formula; the final broad-market holdout contains 1,696 TWSE/TPEx issuers and 6,619 samples, with MAE 0.1703—about a 4.8% improvement over the zero-growth baseline.
- [x] Kept the original gate rather than relaxing it: growth MAE remains roughly 0.04 percentage points short of the 5% target, and the historical archive is not proven point-in-time. Formal A–F therefore remains blank. The UI and PDF show a research/education disclaimer and expandable formulas, features, parameters, and grade rules.
- [x] Removed arbitrary 0–100 weighting and experimental A–F from ordinary-company financial safety. It now uses the original public-company Altman Z financial-structure reference only when complete, period-aligned annual statements are available; financial firms and inapplicable assets remain explicitly blocked.
- [x] Audited the current TWSE/TPEx official `ci` statement APIs across 1,927 paired ordinary-company statements. Their core balance-sheet fields are complete, but an exact EBIT field is available for zero issuers, so the project does not claim a market-wide, calibrated bankruptcy prediction from that API.
- [x] Added equivalent Chinese/English model cards, a market-wide coverage-audit script, formula/disclaimer UI and PDF content; 120 pytest cases, Ruff, frontend syntax checks, and `pip check` pass.

## 2026-07-20: Usable reference tiers from available data

- [x] Kept formal deployment gates intact, but exposed the existing growth formula's A–F output as a clearly labelled research/education reference tier. It is based on predicted rolling 12-month revenue growth plus empirical positive-growth likelihood, carries a non-investment disclaimer, and never becomes a formal rating merely because it is displayed.
- [x] Replaced the unavailable exact-EBIT-only ordinary-company path with `financial_structure_reference_v3`. It uses same-period official quarterly assets, liabilities, retained earnings, operating income, and revenue; it annualizes only the year-to-date flow inputs by `4 / reported quarter` and shows transparent A/C/E reference tiers.
- [x] Added the bilingual v3 model card, formula-tier disclosure, CSV/PDF fields, and an end-to-end 2330 smoke test. The live smoke result produced growth reference D and financial-structure reference A with 100% required-field coverage.

## 2026-07-20: English PDF report parity

- [x] Replaced the previous abbreviated English PDF path with equivalent detail coverage: profile, price, recent monthly revenue records, quarterly EPS records, valuation inputs, fundamental health and quality, financial metrics and official-statement provenance, risk signals, dividend history, news summaries, glossary, and disclaimer.
- [x] Corrected the English valuation section to read `fair_price_range` rather than incorrectly looking for fair-price keys at the top level of the analysis object.
- [x] Generated both reports from live 2330 analysis data in a temporary directory: Chinese and English are each 15 pages. Every English page has extractable text and all required detailed-section headings are present.
- [x] Added an English detailed-report regression test so rich analysis data must render at least 15 PDF pages in future changes.

## 2026-07-20: English PDF dynamic-analysis localization

- [x] Fixed PEG interpretations, risk signals, and narrative analysis being emitted in Chinese by the English PDF. The English report now rebuilds these sentences from structured analysis results instead of reusing the Chinese-UI narrative.
- [x] Localized all current system-generated risk categories, short/medium/long-term labels, PEG conclusions, and revenue, valuation, volatility, EPS, Piotroski, Altman, Graham, liquidity, profitability, and fundamental-health messages. Company names, news, and other source-provided text remain untouched.
- [x] Added a regression test that supplies Chinese analyser output and verifies that the resulting English dynamic analysis and risk signals contain no CJK characters. PDF-render tests, Ruff, and compilation checks pass.

## 2026-07-20: Documentation synchronization and development-workspace cleanup

- [x] Reviewed every Markdown document. README, development handoff, audit addendum, UI system, progress records, and Chinese/English model cards now match the bilingual UI/PDF, the 220-question Investment Learning Lab, reference tiers, and the 123-test state. Privacy, licensing, third-party notices, learning-source records, and archived historical-request documents remain factually correct, so their facts were not rewritten.
- [x] Marked the old growth v1, financial-safety v1, and financial-structure v2 model cards as historical and linked them to the active growth v2 and financial-structure v3 documents, preventing future work from applying an obsolete formula.
- [x] After confirming no App/Python work was running, cleared `cache/`, `build/`, `logs/`, `__pycache__/`, `app_runtime/__pycache__/`, `.pytest_cache/`, and `.ruff_cache/` (about 67 MiB). `.venv/`, `dist/`, `release/`, and `output/` were excluded from this cleanup target.

## 2026-07-20: GitHub + Render public-demo deployment preparation

- [x] Added `render.yaml`, `.python-version`, and equivalent Chinese/English deployment guides. Render can start one Python 3.12 Web Service from GitHub `main`, check `/healthz`, and auto-deploy only after CI passes.
- [x] Added a separate `TWSTOCK_APP_MODE=web`: it reads the platform `PORT`, binds to `0.0.0.0`, opens no browser, and does not use the desktop single-instance lock. The desktop release still binds only to `127.0.0.1`.
- [x] Public mode removes the `/shutdown` route and shutdown control, uses a temporary data root with smaller retention/capacity limits, and applies default per-source limits of six analyses per hour and 60 searches per minute. The service still runs only one heavy job at a time.
- [x] Added regression tests for public mode, health, shutdown surface, and rate limiting. A real local `TWSTOCK_APP_MODE=web` smoke test verified `/healthz` 200, no shutdown token/control in the homepage, and `POST /shutdown` 404. Final `ruff check .`, `ruff format --check .`, 127 pytest tests, and 10 JavaScript `node --check` commands all passed.
- [x] Git for Windows was installed from an officially signed installer. The GitHub remote `https://github.com/BrianSun0605/tw_stock_analysis.git` was created, and initial commit `2a3da08` was pushed to `main`; cache, output, virtual environments, and packaging artifacts remain excluded by `.gitignore`.
- [ ] The actual Render Blueprint still requires the repository owner to sign in to Render and authorize the GitHub repository. See `docs/DEPLOYMENT_RENDER.en.md`.
