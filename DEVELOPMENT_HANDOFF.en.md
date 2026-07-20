# Taiwan Stock Research: Development Handoff

Updated: 2026-07-20  
Handoff baseline version: `0.2.0-dev`  
Handoff baseline commit: `4b1c8bece5c90f9f7fa959a0260510de03b68e02` (`feat: complete audited desktop release`)  
Current branch: `main`

> This document is the entry point for a development handoff. It records what is genuinely complete, what is deliberately disabled, test evidence, build procedures, and next-step priorities. Item-by-item evidence and the historical fix record remain governed by [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md).

## 0. 2026-07-20 current update

- The latest full automated check is **127 pytest tests passed**, together with `ruff check .`, `ruff format --check .`, compilation, and 10 JavaScript `node --check` commands. Earlier browser/package evidence remains a historical record of that validation.
- The UI, CSV, PDFs, and Investment Learning Lab support Traditional Chinese/English switching. System-generated English PDF narrative—including PEG, risk signals, and the analysis summary—is rebuilt from structured results in English; company names, news, and other source text are not mechanically translated.
- Investment Learning Lab now has seven tracks, 44 concepts, and 220 local bilingual questions, with levels, tracks, missed-question review, answer-position rotation, starred key questions, and a clear-answer-records control. Sources, admission rules, and limits are in `docs/INVESTMENT_LEARNING_SOURCES.en.md`.
- The growth model uses `growth_revenue_v2`, with MAE 0.1703 on 1,696 issuers and 6,619 final holdout samples (about 4.8% better than the zero-growth baseline). Formal gates and the point-in-time limitation remain, so it shows only a research/education growth reference tier.
- Ordinary-company financial safety uses `financial_structure_reference_v3`: the latest official quarterly same-period assets, liabilities, retained earnings, operating income, and revenue produce a Z-ref A/C/E financial-structure reference. The formal rating remains blank and must not be called a bankruptcy probability or Taiwan credit rating.
- The English PDF now has detailed parity with the Chinese report and a detailed-report regression test requiring at least 15 pages. All system UI text and dynamic analysis narrative must follow the selected language.
- A GitHub + Render public-demo path is now included. `render.yaml` defines a Python 3.12 Singapore Free Web Service with `/healthz` and deployment after CI succeeds. `TWSTOCK_APP_MODE=web` is only for the public host: it reads `PORT`, binds to `0.0.0.0`, opens no browser, and skips the desktop single-instance lock. See `docs/DEPLOYMENT_RENDER.en.md`; GitHub remote setup and Render-account authorization still require the repository owner.

## 1. Understand This Project in 30 Seconds

This is a free, MIT-licensed Taiwan-security research tool that runs locally on Windows or as a public Render demo and is copyrighted by Fat Cat Game Studio. Users search Taiwan-listed securities through a browser interface. The program organizes official data, Yahoo fallback data, valuation, financial-risk signals, news indexes, and model estimates, and users can download PDFs.

The current product positioning is “a local research tool in public beta,” not a trading system or a prediction product with completed academic or financial validation.

Most important product rules:

1. “Growth” and “financial safety” are two independent ratings and must not be averaged into an overall score.
2. The growth model estimates revenue growth over the next rolling 12 months, not stock price.
3. Confirmed data and estimated data must be displayed in separate sections.
4. Formal A–F remains blank until validation gates are passed; growth and financial structure may show only clearly labelled research/education reference tiers.
5. Official data comes first; Yahoo is fallback only, and every field must show source, date, fallback, and stale status.
6. Do not force ordinary-company formulas onto different security types; when not applicable, stop and explain.
7. The desktop release App listens only on `127.0.0.1` and allows one user, one job, and one program instance at a time. Render `web` mode also runs only one heavy job, and uses temporary storage plus source-based limits to protect the free demo host.
8. A PDF is generated only after the user presses the button, not automatically for every analysis.

## 2. Current Git and Delivery Status

| Item | Current status |
|---|---|
| Branch | `main` |
| Committed baseline | `4b1c8be` |
| Remote repository | Not configured yet |
| Git tag / GitHub Release | Not created yet |
| Open-source license | MIT, Copyright (c) 2026 Fat Cat Game Studio |
| Windows code signing | Not signed; public downloads may show a SmartScreen warning |
| This handoff document | Will be an uncommitted change after creation; the successor must verify it and commit it separately |

Artifacts such as `release/`, `dist/`, and `build/` are managed by `.gitignore`; do not commit large packaged artifacts directly to Git. A remote repository should be created in the future, followed by a formal Release containing the ZIP, Setup EXE, and SHA-256.

## 3. Completed Status with Evidence

### 3.1 Features and Data

- Built-in official-security snapshot, schema 4, with 2,773 records:
  - Ordinary shares: 2,326
  - ETFs: 381
  - ETNs: 21
  - Preferred shares: 29
  - REITs: 6
  - TDRs: 10
- Covers listed, OTC, and Emerging Stock Market securities; warrants and bonds are currently excluded.
- Search by code, Chinese name, or alias; mixed alphanumeric security codes can be entered directly.
- Analysis flow, cancellation, restoring tasks after refresh, on-demand PDF, CSV export, provenance labels, and stale-data prompts are implemented.
- Writable data in release mode is stored in `%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\`, not in the read-only program bundle.
- Single-instance operation, loopback binding, normal shutdown, and installer install/uninstall flows have been tested in practice.

### 3.2 Most Recent Complete Automated Checks

- `pytest`: 123 passed (latest full check on 2026-07-20).
- Ruff lint: passed.
- Ruff format: 66 Python files passed.
- `pip check`: passed.
- `pip-audit 2.10.1`: no known vulnerabilities found in runtime dependencies.
- JavaScript: six files passed `node --check`.
- Real browser flow: keyboard search for 2330, arrow keys and Enter, five-stage analysis, result focus, provenance labels, and all 13 PDF steps passed; the actual PDF has 15 pages.
- No full-page horizontal overflow at widths 300 px, 627 px, and 1187 px.
- Browser console had no errors or warnings; basic DOM accessibility checks passed.
- 2026-07-19 fix verification: PDFs use TrueType CIDFontType2 to avoid Traditional Chinese garbling in some readers; real 2330 data obtained 24 months of official revenue (2024-07 to 2026-06); 0050 correctly retains ETF identity, tracking index, and AUM and no longer presents missing company revenue/EPS.

### 3.3 Latest Packaging Artifacts

| Artifact | Size | SHA-256 |
|---|---:|---|
| `release/TWStockAnalysis-portable-0.2.0-dev.zip` | 80,753,404 bytes | `d94d878be678d4bc9773647576ddd8eddc29d7dd8d8cd506a5edb38561d97715` |
| `release/TWStockAnalysis-Setup-0.2.0-dev.exe` | 62,066,691 bytes | `4521c2c3bdd26fff7f77642b40b5fea714c861949aeca1a99db40a7ef09664b1` |

These are local packaging results and are not tracked in Git. Files and hashes will necessarily change after a rebuild; use the new `release/SHA256SUMS.txt` as the authority.

### 3.4 How Much More Complete Is It than the Initial Version?

The comparison baseline is the initial Git commit `ff558d7` (`chore: establish project baseline`) and the current commit `4b1c8be`. “How the UI feels,” engineering readiness, and validated forecasting capability must be considered separately, otherwise the result is easy to misjudge.

| Perspective | Initial version | Current version | Conclusion |
|---|---:|---:|---|
| UI and visible-feature feel | About 8/10 | About 8.5/10 | The original already had many visible features, so the visual difference is modest |
| Software engineering and public-beta readiness | About 2/10 | About 7.5/10 | Data, tests, security, storage, and packaging improved substantially |
| Formally validated investment models | 0/2 | 0/2 | Core predictive capability is still unfinished and must not be claimed to be more accurate |

Directly verifiable figures:

| Item | Initial version | Current version | Difference |
|---|---:|---:|---|
| Searchable securities | 371 | 2,773 | Increased by 2,402, about 7.47× |
| Automated tests in repository | 0 | 123 passed | From no regression protection to tests for the main flows |
| Formal rating models passed | 0 | 0 | Still unfinished |
| Experimental ratings | Mixed A–D overall score | Separate growth and safety systems | Reduces misleading output, but does not mean forecasts are validated |
| Main data sources | Yahoo, HiStock, and hard-coded list | Official first, Yahoo fallback, per-field provenance | Better credibility and traceability |
| Windows delivery | No formal flow | Portable ZIP, Setup EXE, SHA-256 | Can now be installed by testers |
| CI | None | Windows CI and complete gate | Each push/PR can automatically catch regressions |
| Open source and third-party licensing | Incomplete | MIT, font license, third-party notices | Meets basic public-source delivery requirements |

From the initial baseline to the current version, 111 files were involved, with about 58,263 added and 4,438 deleted lines. Much of the added material is the official-security snapshot, tests, and documentation; line count indicates scope of change, not quality by itself.

The following internal scale was created to prioritize the handoff; it is not financial-industry certification:

| Dimension | Weight | Initial version | Current version |
|---|---:|---:|---:|
| UI and visible features | 15 | 12 | 13 |
| Data coverage and source credibility | 20 | 5 | 17 |
| Model reasonableness and anti-misleading safeguards | 20 | 3 | 8 |
| Testing and stability | 20 | 1 | 17 |
| Security and local-data management | 15 | 3 | 12 |
| Installation, licensing, and release | 10 | 0 | 7 |
| **Total** | **100** | **24** | **74** |

The most honest interpretation is that the project has advanced from “a feature-rich demonstration program lacking evidence” to “a local App suitable for public testing,” but it is not yet “a formal investment tool proven to forecast future growth and financial distress.” The next stage should not keep piling on UI features; it should first complete the data and validation evidence required for formal models.

## 4. Architecture and Data Flow

~~~mermaid
flowchart LR
    U["User / local browser"] --> W["webui.py / Flask + Waitress"]
    W --> A["services/analysis.py"]
    A --> R["stock/ official data and security master"]
    A --> Y["services/market_snapshot.py / Yahoo fallback"]
    A --> M["models/ growth and safety experimental models"]
    A --> V["valuation/ valuation and research indicators"]
    A --> N["news/ news index"]
    A --> S["storage/ SQLite cache and cleanup"]
    A --> UI["templates + static/js + static/css"]
    UI --> U
    W --> P["report/ on-demand PDF"]
    P --> U
~~~

### 4.1 Main File Map

| Path | Responsibility | Handoff caution |
|---|---|---|
| `webui.py` | Flask routes, task state, SSE, downloads, shutdown, and Waitress startup | Do not casually simplify `_close_waitress_server()` or the EXE may remain after shutdown |
| `services/analysis.py` | Shared CLI/Web analysis flow | New analysis steps must also preserve cancellation, progress, and deadline handling |
| `main.py` | CLI entry | Use `python main.py 2330` to quickly check analysis data |
| `config.py` | Dev/release paths, cache, output, log, and fonts | Do not let release mode write back into the bundle |
| `stock/normalizer.py` | Security master, search, and normalization | Define applicable models before adding an asset type; do not add search then force a formula |
| `stock/official_stock_snapshot.json` | Versioned official security master | Failed updates must not overwrite the last valid version |
| `stock/official_financials.py` | Official financial data | Preserve per-field provenance and data date |
| `stock/mops_history.py` | Market Observation Post System historical data | Core location for future point-in-time work |
| `services/market_snapshot.py` | Shared market snapshot and Yahoo fallback | Yahoo is not the main trusted source; fallback must be shown |
| `models/growth_model.py` | 12-month revenue-growth experimental model | Not a price model; do not remove the formal-rating gate |
| `models/safety_model.py` | Financial-safety experimental screen | Not a bankruptcy probability; financial-sector companies must not receive ordinary-company formulas |
| `research/model_cards/` | Model objectives, limitations, and applicability | Update alongside model revisions |
| `research/backtest/` | Backtests and model-validation artifacts | Preserve benchmarks, splits, and failed results, not only the best figures |
| `valuation/analyzer.py` | Valuation and existing research indicators | Do not combine valuation, growth, and safety into one conclusion |
| `templates/index.html` | Page structure and accessibility semantics | Rerun keyboard and narrow-screen acceptance after modification |
| `static/css/app.css` | UI-system implementation | Mobile overflow was fixed here; test 300 px |
| `static/js/api.js` | API calls | Dynamic APIs must not be cached by the Service Worker |
| `static/js/app.js` | Interactions and task flow | Preserve single-worker behavior, cancellation, and focus management |
| `static/js/dom.js` | Safe DOM construction | Do not revert external text to `innerHTML` concatenation |
| `static/js/render.js` | Results UI and provenance labels | Trusted data and estimates must be separated |
| `static/js/export.js` | CSV export | Preserve spreadsheet-formula injection neutralization |
| `static/service-worker.js` | Offline cache for static resources | Do not cache dynamic responses such as analysis, task, and download |
| `report/` | PDF generator | Generate only on demand; unsupported assets must not receive PDFs |
| `storage/` | SQLite cache, task files, and automatic cleanup | Update documentation and tests whenever TTL or capacity changes |
| `packaging/` | PyInstaller and Inno Setup configuration | Installer remains unsigned |
| `scripts/build_windows.ps1` | Windows checks and packaging | The script does not currently run `ruff format --check` or `pip-audit`; run the complete gate manually before packaging |
| `tests/` | Automated regression tests | Add or update focused tests before fixing a bug |
| `docs/UI_DESIGN_SYSTEM.md` | Font, color, spacing, state, and component rules | UI changes must follow this system |
| `docs/PRIVACY.md` | Local-data and external-connection explanation | Update before adding an external source or telemetry |
| `docs/DEPLOYMENT_RENDER.en.md` | GitHub + Render public-demo deployment | First push, Blueprint, quotas, and operating limits |
| `THIRD_PARTY_NOTICES.md` | Packages, fonts, icons, and data sources | Update when dependencies or assets change |
| `PROJECT_AUDIT_REPORT.md` | Complete audit evidence, real issues, and checklist | This is the debug-history/evidence master; do not replace it with a new summary |

## 5. Web API, Task Lifecycle, and Resource Limits

Current endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Main page |
| GET | `/search` | Security search |
| POST | `/analyze` | Create an analysis job |
| GET | `/task/<task_id>` | Get job status |
| GET | `/stream/<task_id>` | SSE progress events |
| POST | `/task/<task_id>/report` | Create a PDF job |
| POST | `/task/<task_id>/cancel` | Cancel a job |
| GET | `/download/<filename>` | Download an output file |
| POST | `/shutdown` | Desktop only: safely close the local App; not registered in public mode |
| GET | `/ping` | Lightweight connectivity check |
| GET | `/healthz` | Render health check |
| GET | `/manifest.json` | PWA manifest |

Hard limits in `webui.py`:

- Concurrent jobs: 1.
- Analysis deadline: 180 seconds.
- PDF deadline: 180 seconds.
- Maximum single result: 64 MiB.
- Event limit: 200 events or 4 MiB.
- Total job TTL: 1 hour.
- Terminal-state TTL: 10 minutes.

These limits are guardrails and resource protection for general users. Do not loosen them merely to make a large output succeed. Any real adjustment must consider memory, disk, cancellation, error messages, and malicious input together.

## 6. Data Sources and Credibility Contract

### 6.1 Priority

1. Official sources such as TWSE, TPEx, and the Market Observation Post System.
2. The saved last valid official version; it may be used offline, but the UI must mark it `stale`.
3. Yahoo Finance/yfinance fallback; the UI must label it Yahoo or `fallback`.

News retains only index fields—title, summary, source, and link—not full text.

### 6.2 Each Data Field Must Retain

- Value.
- Data source.
- Data date or retrieval time.
- Whether it is fallback.
- Whether it is stale.
- Reason for missing or not applicable.

Do not write only one “data source” line in a footer, because one page can mix official, Yahoo, and model data. Provenance must travel with the field or section.

### 6.3 Asset-Class Applicability Boundaries

| Class | Search | Ordinary-company growth model | Ordinary-company safety model | PDF |
|---|---:|---:|---:|---:|
| Ordinary shares / TDR | Yes | Experimental, subject to gate | Experimental, subject to gate | Yes |
| Financial holdings, banks, insurers | Yes | Depends on data | No; specialized regulatory model pending | Can show applicability limits |
| ETF | Yes | No; constituent-weighted model pending | No; ETF structural experimental screen only | Supported content only |
| ETN | Yes | No | No | No |
| REIT | Yes | No | No | No |
| Preferred share | Yes | No | No | No |
| Warrants / bonds | No | No | No | No |

## 7. Model Status: the Most Easily Misunderstood Part

### 7.1 Growth Model

- Objective: future rolling 12-month revenue growth.
- It is not a stock-price forecast, investment return, or buy/sell recommendation.
- The active model is `growth_revenue_v2`: 24 months of official revenue with ridge + shrinkage + median-residual calibration. Its final broad-market holdout has 1,696 issuers and 6,619 samples, MAE 0.1703, or about a 4.8% improvement over the zero-growth baseline.
- It shows estimated growth percentage, an 80% interval, likelihood of positive growth, an expandable full formula, and a separately labelled A–F growth reference tier. The tier is available for research/education even though the formal A–F rating remains blank because the pre-specified 5% MAE-improvement gate and point-in-time archive requirement are incomplete.
- Existing historical data is the “latest revised version,” not true point-in-time data archived at every announcement date, and may create look-ahead bias.
- The secondary EPS target has not completed historical validation and must not generate seemingly precise EPS forecasts.

### 7.2 Financial Safety Model

- The active model is `financial_structure_reference_v3`: it uses the latest official TWSE/TPEx ordinary-company quarterly statement when its seven required fields are present. It annualizes year-to-date operating income and revenue by `4 / reported quarter`, displays a transparent A/C/E financial-structure reference tier, and never calls the result original Altman Z or a Taiwan bankruptcy probability.
- There are no complete Taiwan-company labels for “future financial distress/delisting/default,” so it is not a bankruptcy probability, credit rating, or formal Taiwan rating.
- Formal A–F remains blank. The separately labelled A/C/E *reference* tier shows every ratio, coefficient, contribution, annualization factor, and limit. Missing data must not be filled with an arbitrary 0–100 score.
- Financial and insurance companies have different balance-sheet structures and must not receive ordinary-company formulas.

### 7.3 Correct Next-Stage Research Sequence

1. Build an announcement-date archived, reproducible point-in-time dataset.
2. Freeze objectives, benchmarks, time splits, and acceptance gates before training models.
3. Use rolling/walk-forward temporal validation for growth models to avoid future-data leakage from random splitting.
4. For the safety model, first define auditable distress labels and observation windows, then address class imbalance, calibration, and out-of-sample validation.
5. Report MAE, directional accuracy, interval coverage, calibration, and results by industry and market-cap groups, not only one overall score.
6. Enable formal A–F only after the defined gates pass; preserve failed results in `research/` as well.

## 8. Local Storage, Cache, and Cleanup Rules

Release data root:

~~~text
%LOCALAPPDATA%\FatCatGameStudio\TWStockAnalysis\
├─ cache\
├─ logs\
└─ output\
~~~

| Type | Current rule | Reason |
|---|---|---|
| PDF/output | Retain 3 days; remove oldest files first above 250 MiB | Supports short-term re-download without unlimited accumulation |
| Job charts | Retain 24 hours | No need to occupy space long after a job ends |
| Cache | Hard ceiling 256 MiB; above 200 MiB, reduce to 160 MiB | High/low watermarks avoid deleting a little and immediately cleaning again |
| Log | Retain 14 days; total limit 20 MiB | Enough to diagnose recent issues without long-term leakage or growth |
| Cleanup frequency | At most once every 6 hours | No need to scan the full disk for every request |

This is better than deleting everything in batches every few days: frequently used official data can continue to be used, while infrequently used files are retired one by one by age and capacity. Rules are in `config.py` and `storage/cleanup.py`.

Uninstallation currently preserves user data in `%LOCALAPPDATA%` to avoid accidentally deleting PDFs, cache, and logs. Program contents are removed, but testing may leave an empty installation-data folder; this is a low-priority issue.

## 9. UI, UX, and Accessibility Rules

- The visual system is governed by `docs/UI_DESIGN_SYSTEM.md`, including Noto Sans TC, colors, spacing, states, and components.
- Do not use color alone for success, warning, provenance, or risk; include text or an icon as well.
- Touch targets are at least 44 px.
- Search combobox, arrow keys, Enter, focus movement, and result focus after analysis are implemented.
- Trusted data, estimates, news, and limitations need clear sections; do not blend every card together.
- Retest at least 300 px on narrow screens; full-page mobile horizontal overflow was a real bug.
- Basic DOM checks in the browser are complete, but Axe automated scans and physical NVDA/Windows Narrator acceptance are not. Do not mark either as complete.

## 10. Security Boundaries and Safeguards That Must Not Be Broken

- Desktop Waitress binds only to `127.0.0.1`. A public host must use only the reviewed `TWSTOCK_APP_MODE=web` path, running at `0.0.0.0:$PORT`; do not expose desktop mode by changing its host.
- Desktop `/shutdown` requires a random token plus loopback, Host, and same-origin checks. Public mode registers neither this route nor its token.
- Public mode trusts Render's one reverse proxy to obtain the source address and applies in-memory limits to search/analysis starts. This is not shared multi-node rate limiting or account isolation; add those before scaling the service.
- CSP forbids inline scripts and inline styles.
- External text uses safe DOM APIs; do not insert news, names, or error text directly into `innerHTML`.
- CSV export must neutralize spreadsheet formulas beginning with `=`, `+`, `-`, or `@`.
- The Service Worker caches only fixed static resources and must not cache task, analysis, download, or other dynamic APIs.
- File names, task IDs, and download paths must continue to prevent path traversal.
- Do not log `.env`, tokens, full personal data, or unnecessary external-response content.
- Before adding an external source, verify its official status, stability, license, and public-distribution terms, then update `docs/PRIVACY.md` and `THIRD_PARTY_NOTICES.md`.

## 11. Development Environment and Common Commands

Requirements: Windows and Python 3.12. Full packaging additionally requires Node.js 20+, PyInstaller, and Inno Setup.

### 11.1 Install and Start

~~~powershell
python -m pip install -r requirements-dev.txt
python webui.py
~~~

Specify a port:

~~~powershell
python webui.py 5050
~~~

Quick CLI test:

~~~powershell
python main.py 2330
~~~

Update the official security snapshot:

~~~powershell
python scripts\update_stock_snapshot.py
~~~

After updating the snapshot, verify at least: schema, record count, each asset class, duplicate codes, blank names, source URL, failed-update preservation of the last valid version, and a representative search.

### 11.2 Complete Gate Before Every Commit

~~~powershell
python -m pip check
python -m pip_audit -r requirements.txt --progress-spinner off
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -p no:cacheprovider
node --check static\js\api.js
node --check static\js\app.js
node --check static\js\dom.js
node --check static\js\export.js
node --check static\js\render.js
node --check static\service-worker.js
git diff --check
~~~

CI is in `.github/workflows/ci.yml`, uses Windows latest and Python 3.12, and runs the dependency, security, formatting, test, and JavaScript-syntax gates above.

### 11.3 Windows Packaging

Portable:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
~~~

Portable + Setup EXE:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Installer
~~~

Note: `scripts/build_windows.ps1` currently runs `pip check`, Ruff lint, pytest, and JS syntax, but does not run `pip-audit` or `ruff format --check`. Run the complete gate manually before creating a public build.

After packaging, perform actual acceptance rather than looking only at the build exit code:

1. Extract the portable build into a new directory and start it.
2. Confirm loopback-only listening and that the bundled 2,773-record master is available.
3. Search an ordinary share, ETF, ETN, and at least one alphanumeric code.
4. Complete a 2330 analysis, cancel one job, generate and download a PDF.
5. Start it again to confirm single-instance behavior.
6. After normal shutdown, confirm the background EXE disappears.
7. Install the Setup, launch, launch again, close, and uninstall it.
8. Recalculate hashes and confirm `SHA256SUMS.txt` matches the actual files.

## 12. Known Environment Issues and Lessons Learned

1. Calling only `server.close()` when closing the App leaves a Waitress keep-alive channel and can leave the EXE running. `_close_waitress_server()` in `webui.py` closes the channel before the server; do not remove it without regression testing.
2. The 300 px mobile layout once had a full-page horizontal scrollbar caused by a `body` minimum width and source-list fields. Retest after changing global layout, grids, or source fields.
3. When installing/uninstalling in a restricted sandbox, shortcut creation and HKCU writes can return code 4. Installation, launch, and uninstallation were tested successfully under ordinary Windows permissions. Distinguish permission restrictions from product bugs when assessing installer problems.
4. `yfinance` normally writes SQLite cookie/timezone cache to the user profile; it is now forced into the project or LocalAppData cache. Do not remove that setting.
5. A single public Render demo service now exists, but it is not an enterprise multi-user platform: it has no accounts, persistent tasks, or shared rate-limit database, and free-host storage can lose caches/PDFs. A future scaled service still needs redesigned authentication, authorization, CSRF, shared job queues, data isolation, monitoring, and persistent storage.

## 13. Next Development Priorities

The recommended main line is “credible data → reproducible validation → formal models,” then specialized methods for different assets and formal publication. Do not prioritize a major UI rewrite now: the real missing element is evidence that ratings are credible, not more cards.

Scope boundary:

- Included: point-in-time official data, validation of growth and safety models, specialized ETF/financial methods, accessibility, digital signing, and formal open-source release.
- Temporarily excluded: stock-price target forecasts, combining growth and safety into a single total score, an enterprise-grade multi-user public web server, and major UI decoration or architecture rewriting before model evidence is complete.

### P0: Confirm the Baseline Has Not Drifted After Handoff

- Run the full gate first and confirm it is still 127 tests passed, or record any difference.
- Start the source version and run one complete 2330 flow and PDF.
- Check `git status`; do not accidentally commit `build/`, `dist/`, `release/`, cache, logs, or PDFs.
- Compare with the checklist in `PROJECT_AUDIT_REPORT.md`; do not rely only on this handoff summary.

### P1: Build Genuinely Verifiable Formal Models

- Build point-in-time financial-statement and monthly-revenue datasets.
- Preserve source, announcement time, version, and revision relationship so a model cannot see information not public at its forecast time.
- Fix time splits, benchmarks, and acceptance gates.
- Build financial-distress labels and out-of-sample tests.
- Preserve successful and failed experiments; update `research/backtest/` and `research/model_cards/`.
- Keep formal A–F blank until gates pass.

Completion condition: the dataset is reproducible from a clean environment with no future-data leakage, and growth and safety models each receive a clear “pass” or “fail” conclusion. This is the highest priority and the work most likely to materially improve product value.

### P2: Complete Specialized Methods for Different Assets

- First priority, ETFs: constituents, weights, tracking index, concentration, liquidity, premium/discount, and weighted growth.
- Second priority, financial/insurance: capital adequacy, asset quality, reserves, regulation, and industry-specific risk.
- Third priority, REITs, ETNs, and preferred shares: define the user question and data contract first, then decide whether ratings and PDFs are appropriate.

Completion condition: every asset type has its own applicable fields, stop conditions, tests, and model card; it must not fall back to ordinary-share formulas.

### P3: Complete Public-Beta Quality Work

- Run Axe and preserve its report.
- Complete the primary flow with Windows Narrator or NVDA and record physical assistive-technology results.
- Purchase or configure a Windows code-signing certificate, sign the executable and installer, then retest SmartScreen/signature information.
- Fix the low-priority empty-folder issue after uninstallation.

Completion condition: the primary flow has no Axe critical/serious issues, a physical screen reader can complete core tasks, and public installers show a verifiable publisher.

### P4: Formal Open-Source Publication

- Configure a Git remote.
- Decide version number and release notes.
- Create a tag and GitHub Release.
- Upload portable build, installer, SHA-256, license, and known limitations.
- The public page must clearly state: local tool, not investment advice, models remain experimental, data sources, and Yahoo fallback limitations.

Completion condition: new users can verify source and hash from the public page, complete installation and the primary flow, and do not mistake experimental ratings for guarantees or formal investment advice.

### Recommended Version Roadmap

| Suggested milestone | Development theme | Acceptance outcome |
|---|---|---|
| `0.2.x` | Stabilize the current public-beta baseline | Fix regressions and add Axe/screen-reader evidence; no major features |
| `0.3.0` | Point-in-time data foundation | Reproducible official historical dataset, version record, and data-quality report |
| `0.4.0` | Formal model validation | Growth/safety each pass their gates, or honestly remain experimental |
| `0.5.0` | Asset-specialized analysis | ETFs first, financials second; other assets according to data feasibility |
| `1.0.0` | Formal public release | Accessibility acceptance, code signing, remote repository, and formal Release |

## 14. Regression Rules When Changing Things

| Changed area | Minimum reruns |
|---|---|
| Data source/parser | Relevant unit tests, failed fallback, source/date display, stale behavior |
| Model/rating | Temporal-split backtest, gates, model card, formal/experimental labels, asset applicability boundary |
| `webui.py` | Task lifecycle, cancellation, deadline, SSE, single worker, shutdown, loopback |
| UI/CSS | 300/627/1187 px, keyboard, focus, console, source sections, 44 px targets |
| PDF | On-demand generation, pages and Chinese font, download, 3-day TTL, unsupported-asset restriction |
| Storage/config | Dev/release paths, capacity and TTL, non-destructive cleanup, read-only bundle |
| Packaging | Portable in new directory, installer, single instance, normal shutdown, uninstall, hash |
| Dependencies | `pip check`, `pip-audit`, full pytest, license notices |

## 15. Order of Document Authority

If documents conflict, verify in this order:

1. Current actual code, tests, and real packaged artifacts.
2. Item-by-item evidence and latest status in `PROJECT_AUDIT_REPORT.md`.
3. High-level progress in `PROGRESS.md`.
4. User instructions in `README.md`.
5. The organized summary in this handoff document.

Do not skip real testing because a document says “complete,” and do not ignore later recorded fixes and regression evidence because an early audit said “problem.”

## 16. Suggested First Hour for the Successor

1. Read this file, `README.md`, and `PROGRESS.md`, then the conclusions and unfinished items in `PROJECT_AUDIT_REPORT.md`.
2. Run `git status` and `git log -1` to confirm the baseline commit.
3. Create a Python 3.12 environment and install `requirements-dev.txt`.
4. Run the complete gate and record any result that differs from this document.
5. Run `python webui.py`, then use 2330 to test search, analysis, cancellation, PDF, and normal shutdown.
6. Choose one P1 item; add tests or research evidence first, then make the smallest change.
7. For every handoff, update `PROJECT_AUDIT_REPORT.md`, `PROGRESS.md`, necessary model cards, and this handoff document together.

## 17. Final Reminder

The most valuable part of this version is not that it “appears able to rate everything.” It is that untrustworthy, inapplicable, and unvalidated content has been explicitly blocked. Future development should prioritize data and model evidence; do not pretend completion by removing gates, merging the two ratings, or adding attractive-looking numbers.
