# Third-Party Packages, Fonts, and Data Sources

This file records third-party material distributed with the source code or Windows App. The full license text remains governed by files included with each package and its upstream project.

## Fonts

### Noto Sans TC

- Purpose: PDFs, charts, and Traditional Chinese display.
- Upstream: notofonts/noto-cjk, Noto Sans CJK Traditional Chinese.
- License: SIL Open Font License 1.1.
- License copy in this project: `assets/licenses/NotoSansCJK-OFL.txt`.
- Font files: `fonts/NotoSansTC-Regular.otf`, `fonts/NotoSansTC-Bold.otf`, and the PDF-specific `fonts/NotoSansTC-Variable.ttf`.
- Version: 2.004.
- SHA-256 (Regular): `5BAB0CB3C1CF89DDE07C4A95A4054B195AFBCFE784D69D75C340780712237537`.
- SHA-256 (Bold): `55420B259EB119BF5F2A0AADBA10CF9D736C12D64AB93E78546D69EF5F43558B`.
- SHA-256 (PDF TrueType): `864727D210D54F2537BBE23B3A839436C3992AF72DE9322AF5270897246BD44F`.

The font may be distributed with software but must not be sold by itself. If the font is modified, OFL and reserved-name terms must still be followed.

## Python Runtime Packages

| Package | Pinned version | Primary license |
|---|---:|---|
| yfinance | 1.5.1 | Apache |
| NumPy | 2.4.6 | BSD-3-Clause and bundled-component licenses |
| pandas | 3.0.3 | BSD-3-Clause |
| Matplotlib | 3.10.9 | Matplotlib License and bundled-component licenses |
| fpdf2 | 2.8.7 | LGPL-3.0-only |
| Requests | 2.33.1 | Apache-2.0 |
| Beautiful Soup | 4.15.0 | MIT |
| lxml | 6.1.1 | BSD-3-Clause |
| Flask | 3.1.3 | BSD-3-Clause |
| Waitress | 3.0.2 | ZPL-2.1 |

The release installer should retain package licenses/metadata collected by PyInstaller. Update this table whenever dependencies are upgraded.

## Data Sources

- TWSE OpenAPI, TPEx OpenAPI, and the Market Observation Post System: official public-data sources. The App stores the required snapshots and cache and labels source and date for each field.
- FinMind API: structured fallback data only when a public-cloud host cannot temporarily obtain complete monthly revenue or quarterly EPS from TWSE/TPEx/MOPS. Returned values are always marked `fallback` and remind users to check official disclosures; the project never presents them as direct official responses.
- Yahoo Finance / yfinance: fallback only for market data, some financial data, and ETF information. Upstream describes Yahoo data as oriented toward personal research. This project does not redistribute a complete Yahoo dataset; terms must be reconfirmed before commercialization.
- Google News / Bing RSS: only titles, summaries, sources, and links from public indexes are organized; full text is neither stored nor republished.

Public readability of official data does not guarantee correctness or uninterrupted availability. The App validates fields, retains the last valid data, and marks `stale` / `fallback`.

## Icons

`picture/icon/app-icon.svg` is a geometric icon created for this project and contains no third-party photographs or trademark assets.

## Open-Source License for This Project

This project uses the MIT License, Copyright (c) 2026 Fat Cat Game Studio. See `LICENSE` in the project root for the full terms.
