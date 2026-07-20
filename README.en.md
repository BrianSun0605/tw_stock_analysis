# Taiwan Stock Research

This is a Taiwan-stock research tool that can run on your own computer or be deployed as a public demo website. It organizes official public data, clearly labelled Yahoo/FinMind fallback data, valuation scenarios, financial-risk signals, and news indexes, and lets users download PDFs themselves.

It is not a trading system and does not guarantee that a stock will rise. Growth, financial safety, and whether a share price is cheap are three different things; the interface does not average them into a deceptively precise single score.

## What It Can Do Now

- Search the project-bundled snapshot of 2,773 official securities, covering listed, OTC, and Emerging Stock Market securities, including stocks, TDRs, ETFs, ETNs, preferred shares, and REITs; warrants and bonds are excluded.
- Read TWSE, TPEx, and Market Observation Post System data first. Monthly revenue uses the latest OpenAPI period together with the official MOPS historical archive to complete trends. If a cloud host is temporarily rejected by an official endpoint, structured FinMind monthly-revenue/quarterly-EPS data is used only as a labelled fallback; the interface marks source, date, `fallback`, and stale status.
- Show confirmed data separately from model estimates.
- Display valuation ranges, financial health, Piotroski/Altman applicability, dividends, peers, calendars, and news indexes.
- Provide an offline, bilingual Investment Learning Lab: seven learning tracks, 44 concepts, and 220 local questions covering foundations; candlesticks and price charts; financials and valuation; ETFs; industry research; news literacy; and strategy/risk. Learners can use track, level, missed-question, and starred-key-question views.
- Keep quick plain-language lessons beside indicators. Learning progress, missed questions, and starred key questions are stored only locally; users can clear answer records without removing starred questions.
- Support Traditional Chinese/English UI switching. In English mode, system UI, the interactive question bank, CSV fields, and PDF analysis narratives render in English. Company names, news, and other source-provided text remain in their original source language.
- Show web results when analysis finishes; generate a PDF only when the user presses the button.
- The Windows release listens only on local `127.0.0.1` and permits only one running instance at a time.

## What the Two Ratings Currently Mean

### Growth Rating

The goal is to estimate a company's revenue growth over the next rolling 12 months, not to predict its share price. The model shows a growth reference tier, growth percentage, an 80% estimated interval, and the likelihood of positive growth.

`growth_revenue_v2` uses 24 months of official revenue with ridge regression, shrinkage, and median-residual calibration. Its broad-market holdout contains 1,696 issuers and 6,619 samples, with MAE 0.1703—about a 4.8% improvement over the zero-growth baseline. Formal A–F remains blank because the model has not reached the pre-specified 5% MAE-improvement gate and the archive is not proven announcement-date point-in-time data. The growth reference tier is for research and education only; it is not a formal rating, price target, or return forecast. The secondary EPS target has not completed historical validation, so it produces no forecast numbers.

### Financial Safety Rating

Ordinary companies use `financial_structure_reference_v3`: it calculates a transparent Z-ref financial-structure reference from same-period official assets, liabilities, retained earnings, operating income, and revenue, annualizing only year-to-date income-statement flows by `4 / reported quarter`. It shows A/C/E reference tiers and formula details; it is not a bankruptcy probability, credit rating, or investment recommendation.

Taiwan historical financial-distress labels, announcement-date-reproducible statements, and chronological out-of-sample validation are unfinished. Formal A–F therefore remains blank, and the financial-structure reference tier must not be treated as a formal Taiwan financial-safety grade.

- Financial holding companies, banks, and insurers: the ordinary-company formula is not applied; the interface shows “specialized model pending.”
- ETFs: company revenue/EPS models are not applied. Instead, an experimental screen for ETF structural safety uses NAV, premium/discount, expense ratio, AUM, trading volume, distributions, and tracking index.
- ETNs, REITs, and preferred shares: included in the official search master, but specialized analysis models are not complete. Ordinary-share formulas are not applied, and no rating or PDF is produced.
- Growth and safety always remain separate; `combined_rating` is permanently blank.

Locations of models and limitations:

- `models/growth_model.py`
- `models/safety_model.py`
- `research/model_cards/`
- `research/backtest/`

## Installing and Running the Source Code

Requirement: Python 3.12. The project is currently verified with Python 3.12.

```powershell
python -m pip install -r requirements.txt
python webui.py
```

The default address is `http://127.0.0.1:5000`. You can also specify another port:

```powershell
python webui.py 5050
```

Command-line mode:

```powershell
python main.py 2330
```

## Web Workflow

1. Search for a stock code or name and start analysis.
2. When the five analysis stages finish, the web page shows the result immediately.
3. Press “Generate PDF” only when you need a PDF; download becomes available when it is complete.
4. Analysis can be cancelled. After refreshing the page, non-expired task status can be restored.
5. Only one analysis or PDF job runs at a time, and a single job is limited to 180 seconds.

## Public Deployment with GitHub + Render

The repository includes `render.yaml` and a safe `web` runtime mode for a single Web Service that users can open directly. It does not need GitHub Pages or an AI API. Public mode uses Render's `PORT`, removes desktop shutdown controls, writes files to temporary storage, and limits per-source analysis/search activity.

For the first GitHub upload, creating the free Render Blueprint, naming, testing, quotas, and free-plan limits, follow [docs/DEPLOYMENT_RENDER.en.md](docs/DEPLOYMENT_RENDER.en.md).

## Data Sources and Limitations

| Data | Preferred source | Fallback or limitation |
|---|---|---|
| Security list | TWSE OpenAPI, TPEx OpenAPI, and the official TWSE ETN product list | A versioned official snapshot is used; a failed update does not overwrite the last valid version |
| Monthly revenue and financial statements | TWSE/TPEx OpenAPI and Market Observation Post System | If official endpoints are temporarily unavailable, FinMind structured monthly revenue and quarterly EPS can be used as a fallback. Each value retains its `fallback` status, source, and reminder to check official disclosures. |
| Market prices, some financial data, and ETF data | Yahoo Finance / yfinance | Yahoo is a fallback; its upstream data is oriented toward personal research, so terms must be reconfirmed before commercialization |
| News | Google/Bing RSS indexes | Only titles, summaries, sources, and links are organized; full text is not stored |

Update the securities snapshot:

```powershell
python scripts\update_stock_snapshot.py
```

Main source-code locations:

- `stock/official_stock_snapshot.json`
- `stock/official_financials.py`
- `stock/mops_history.py`
- `services/market_snapshot.py`

## PDFs, Cache, and Local Data

The release App stores writable data in:

```text
%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\
├─ cache\
├─ logs\
└─ output\
```

- PDFs: retained for 3 days; when output exceeds 250 MiB, the oldest files are removed first.
- One-time job charts: retained for 24 hours.
- Cache: when it exceeds 200 MiB, it is reduced to 160 MiB. The last valid official data can be used offline, but is marked stale.
- Logs: retained for 14 days with a total limit of 20 MiB.
- Cleanup runs at most once every 6 hours.

This is more appropriate than clearing everything every fixed number of days: frequently used data can remain, while infrequently used and expired files are removed one by one according to age and capacity. The rules are in `config.py` and `storage/cleanup.py`.

### Manual cleanup in a development workspace

After closing the App and confirming that no analysis or PDF task is running, it is safe to clear `cache/`, `build/`, `logs/`, `__pycache__/`, `.pytest_cache/`, and `.ruff_cache/`. They contain rebuildable caches, task charts, build intermediates, test/lint caches, or logs and do not affect the next run. Keep `.venv/`, `dist/`, `release/`, and `output/`; `output/` can contain PDFs a user wants to retain.

## Development Checks and Windows Packaging

Development and packaging require Python 3.12 and Node.js 20 or later. Generating the Setup EXE additionally requires Inno Setup.

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pip_audit -r requirements.txt --progress-spinner off
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -p no:cacheprovider
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Installer
```

Packaging outputs:

- Portable version: `release/TWStockAnalysis-portable-<version>.zip`
- Installer version: `release/TWStockAnalysis-Setup-<version>.exe`
- Checksums: `release/SHA256SUMS.txt`
- Installer configuration: `packaging/installer.iss`. With `-Installer`, Inno Setup is located through PATH or common installation locations.
- The current development EXE is not Windows code-signed, so public downloads may show a SmartScreen warning.

## Important File Locations

```text
webui.py                    Local web service and job lifecycle
services/analysis.py        Shared CLI/Web analysis flow
models/                     Growth and safety models
stock/                      Official data, prices, dividends, peers, and calendar
valuation/analyzer.py       Valuation and existing research indicators
templates/index.html        Page structure
static/css/app.css          UI visual-system implementation
static/js/                  API, rendering, cancellation, and CSV export
static/js/learning*.js      Bilingual Investment Learning Lab, question bank, and local learning records
static/js/i18n.js           UI/report language strings
report/                     PDF generator
storage/                    SQLite and automatic cleanup
tests/                      Automated tests
docs/UI_DESIGN_SYSTEM.md    Font, color, spacing, state, and component rules
docs/PRIVACY.md             Local-data and external-connection explanation
THIRD_PARTY_NOTICES.md      Packages, fonts, icons, and data sources
LICENSE                     MIT open-source license and copyright holder
PROJECT_AUDIT_REPORT.md     Issue evidence, fix status, and remaining checklist
```

## Security and Public Distribution Status

- The desktop service binds only to `127.0.0.1`; only an explicit `TWSTOCK_APP_MODE=web` deployment binds to the platform-provided public port.
- The shutdown endpoint requires a random token plus loopback, Host, and same-origin checks.
- Public `web` mode does not register the shutdown endpoint or render its button, applies source-based limits to search and analysis starts, and uses temporary storage for free-host tasks, caches, and PDFs.
- CSP forbids inline scripts/styles; dynamic APIs do not enter the Service Worker cache.
- External text uses safe DOM APIs; CSV neutralizes spreadsheet-formula prefixes.
- A copy of the Noto Sans TC OFL license is in `assets/licenses/`; see `THIRD_PARTY_NOTICES.md` for third-party information.
- The project uses the MIT License, copyright holder “Fat Cat Game Studio”; see `LICENSE` for the full terms.

For complete verification results and reasons for unfinished work, see [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md).
