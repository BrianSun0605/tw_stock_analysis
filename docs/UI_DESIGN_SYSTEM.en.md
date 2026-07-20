# UI Design System

This system keeps future screen changes consistent instead of relying on ad-hoc visual adjustments every time.

## 1. Information Order

1. At first glance, show the security, price date, source, fallback status, and missing data.
2. “Confirmed data” and “model estimates” must be separated; an estimate must not be written as an observed fact.
3. Growth and financial safety must always be displayed separately and must not be averaged into one overall rating.
4. ETFs, ordinary companies, and financial companies use different copy; when something does not apply, show the reason directly.
5. Important limitations must appear near the number, not only in a footer disclaimer.
6. Beginner KPIs must be grouped by the question they answer instead of merely stacking identical cards: for ordinary shares, “Price and Valuation / Company Quality and Growth / Income”; for ETFs, “Market Price and NAV / Fund Structure / Trading and Income.”
7. Learning interactions use 30–60-second single-question tasks, immediate plain-language feedback, and common misconceptions. Learning progress is stored locally only; do not use leaderboards or correct-answer rates to imply investment ability.
8. Investment Learning Lab uses tracks, levels, missed-question review, and starred key questions to provide a learning path. Clearing answer records must retain a user's starred key questions and must not send learning records to a server.
9. After a language change, all system UI, model explanations, CSV fields, interactive questions, and system-generated PDF narrative must use the selected language. Company names, news, disclosures, and other source-provided text remain in their source language and must not be presented as verified translations.

## 2. Colors

Color sources follow the CSS variables in `static/css/app.css`:

| Purpose | Token | Hex |
|---|---|---|
| Primary text / dark background | `--navy-900` | `#123047` |
| Primary action | `--blue-700` | `#1d5f8a` |
| Success / lower risk | `--green-700` | `#167044` |
| Caution / uncertainty | `--amber-700` | `#9a5c08` |
| Error / higher risk | `--red-700` | `#b4232c` |
| Secondary text | `--slate-500` | `#596672` |

- Color cannot be the only signal; it must be accompanied by text, an icon, or a status name.
- Small text on a white background must use at least `--slate-500`; do not reduce contrast further.
- A–F may be supported with color, but both screen and exported content must retain the letter.

## 3. Fonts and Type Sizes

- Web: system sans-serif, preferring Segoe UI, Microsoft JhengHei, and Noto Sans TC.
- PDFs/charts: the Noto Sans TC font (SIL OFL 1.1) distributed with the App.
- Recommended body text: 13–16 px; explanatory text at least 11 px; long paragraphs at least 12 px.
- Use tabular numerals to avoid shifting when values update.
- Do not replace primary Chinese headings with all-cap English; English eyebrows are only a supporting hierarchy.

## 4. Spacing and Layout

- Base spacing: 4, 8, 12, 16, 24, and 32 px.
- Card padding: 22–28 px on desktop, 18 px on mobile.
- Corner radius: 12 px for primary cards, 6–9 px for small components.
- Desktop maximum width: 1440 px; 1120, 820, and 560 px are the main breakpoints.
- Tables may scroll horizontally on narrow screens; their container must be keyboard-focusable and include an explanation.

## 5. Component States

Every component that loads data must express:

- `loading`: being fetched.
- `ready`: data available.
- `missing`: insufficient data; do not display zero instead.
- `stale`: using last valid older data.
- `fallback`: official data unavailable; a labeled fallback is used.
- `not applicable`: model does not apply.
- `error`: source or format error, with a plain-language response.

Buttons require `default`, `hover`, `focus-visible`, and `disabled`; background work additionally has `cancelling`.

## 6. Accessibility

- Every operation can be completed using only a keyboard.
- `focus-visible` must be clear; after results open, move focus to the results area.
- Search suggestions use `combobox` / `listbox` / `option` semantics and `aria-activedescendant`.
- Progress and errors use `aria-live`, while avoiding rereading the entire page on every update.
- Chart alt descriptions name the security and chart type; decorative images use empty alt text.
- Click targets are at least 40×40 px; primary mobile buttons use full-row width.

## 7. Copy

- Do not call a “reference price” a real-time price unless the source actually provides a real-time timestamp.
- Do not present ETFs as having insufficient company revenue/EPS data. Show company metrics as not applicable and replace them with ETF measures such as NAV, premium/discount, expense ratio, AUM, trading volume, distributions, and tracking index.
- Learning questions and quick explanations must state that they are educational, and must not describe any single indicator as a basis for buying, selling, or guaranteed return.
- Do not call a “valuation scenario range” a target price or guaranteed fair value.
- Models that have not passed their gates must say “experimental estimate / validation not passed.”
- A safety screen is not a bankruptcy probability and does not mean a stock price cannot fall.
- News sentiment must always say “keyword classification, not an investment signal.”

## 8. Acceptance

For every UI change, check at least:

1. 1440×900, 820×1180, and 390×844.
2. Keyboard search, cancellation, reading, PDF generation, and download.
3. No full-page horizontal overflow; tables scroll only inside their own containers.
4. No axe critical/serious issues.
5. JavaScript syntax, Flask tests, and real-data smoke tests pass.
