# Investment Learning Lab: Content and Source Verification

Updated: 2026-07-20

## Scope and design principles

Investment Learning Lab is an offline, bilingual investor-education feature with seven learning tracks, 44 concepts, and 220 questions. It covers investment foundations; candlesticks and price charts; financial statements and valuation; ETFs and asset allocation; industry research; news and media literacy; and strategy, behavior, and risk management.

- Questions are newly authored from verifiable definitions, risk disclosures, and verification methods in the cited materials. They do not reproduce source text.
- Questions do not give buy/sell instructions, predict prices, guarantee returns, or present a technical indicator as a stand-alone trading signal.
- Course data ships with the app. The app does not request external websites or send learning progress while a learner studies.
- Each question exposes a source link in the interface for the learner's own review.
- The original 12 quick-learning concepts remain in their corresponding new topics. This course-record version update clears prior completion and missed-question records on first load. Learners can later clear answer records from the course home while keeping their starred key questions.

## Curriculum structure

| Learning track | Core scope | Main verification principle |
| --- | --- | --- |
| Investment foundations | Goals, horizon, risk, compounding, diversification, and allocation | Personal horizon and risk tolerance come before product selection. |
| Charts and price behavior | Line charts, candlestick OHLC, wicks, volume, trend, and volatility | Charts describe observed data; they do not independently predict future price. |
| Financials, metrics, and valuation | Revenue, EPS, P/E, margins, statements, yield, and valuation | Read metrics with their period, assumptions, and limits. |
| ETFs and asset allocation | NAV, premium/discount, expense ratio, tracking error, liquidity, and concentration | Review fund market price, NAV, holdings, and costs together. |
| Industry research | Semiconductors, financials, cyclicals, technology/software, and biotech/healthcare | Check an industry-specific observation list rather than one number. |
| News and information literacy | Original disclosures, headline context, social signals, conflicts, timing, and fraud flags | Find the original document, date, and interests before forming a view. |
| Strategy, behavior, and risk | Plan, position size, costs, trade discipline, confirmation bias, and overtrading | Use predefined rules and counterevidence to reduce emotion-driven decisions. |

## Verified primary sources

| ID | Institution and document | Verifiable material used | Why it is reliable |
| --- | --- | --- | --- |
| `investor_intro` | [Investor.gov: Introduction to Investing](https://www.investor.gov/introduction-investing) | Foundations of investing, risk, horizon, and allocation | Investor-education site of the U.S. Securities and Exchange Commission (SEC). |
| `investor_diversification` | [Investor.gov: Diversify Your Investments](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/diversify-your-investments) | Diversification and concentration risk | SEC investor-education material. |
| `investor_compound` | [Investor.gov: What is compound interest?](https://www.investor.gov/additional-resources/information/youth/teachers-classroom-resources/what-compound-interest) | Definition and limits of compounding | SEC investor-education material. |
| `investor_candlestick` | [Investor.gov: Candlestick Chart Glossary](https://www.investor.gov/introduction-investing/investing-basics/glossary/candlestick-chart) | Candlestick structure and terms | SEC investor-education material. |
| `twse_technical` | [Taiwan Stock Exchange: Technical-analysis learning material](https://shl.twse.com.tw/rsrc/download/question.pdf) | Structural definitions for candles, trend, and volume | TWSE investor-education material. The course does not treat technical patterns as guaranteed signals. |
| `sec_statements` | [SEC: Beginner's Guide to Financial Statements](https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements) | Reading financial statements, revenue, earnings, and cash flow | Official SEC explanatory guide. |
| `twse_etf_overview` | [Taiwan Stock Exchange: ETF overview and risks](https://accessibility.twse.com.tw/zh/products/securities/etf/overview/introduction.html) | ETFs, NAV, fees, liquidity, and holdings risk | Official TWSE educational material. |
| `twse_etf_premium` | [Taiwan Stock Exchange: ETF premium and discount](https://www.twse.com.tw/zh/ETFortune/invest/8a8216d69e6379f4019e87050e710106) | Relationship between market price and NAV | TWSE ETF education material. |
| `investor_social` | [Investor.gov: Social Media and Stock-Tip Scams](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/social-media-stock-scams) | Social posts, original sources, fraud, and verification | SEC investor-protection education material. |
| `finra_basics` | [FINRA: Investing Basics](https://www.finra.org/investors/investing/investing-basics) | Risk, costs, planning, and general investing principles | FINRA investor-education material. |
| `finra_social` | [FINRA: Social-Media-Influenced Investing](https://www.finra.org/rules-guidance/key-topics/fintech/report/social-media-influenced-investing) | Social influence, behavioral bias, and information risk | FINRA regulatory and research material. |

## Inclusion and maintenance rules

1. Use only definitions and risk reminders that can be directly checked in regulator, exchange, or investor-education material as primary support.
2. Cross-check formulas and scenario questions against a second conceptual source or the context of an original document. When evidence is insufficient, teach that the information is insufficient rather than guessing.
3. Any content about performance, price direction, or technical patterns must state its period, assumptions, limitation, or the boundary that it is not a trading signal.
4. A new question must include Chinese and English content, a question ID, track, level, at least one source ID, and a common misconception. It is not admitted to the production question bank if any item is missing.
5. Before release, run frontend checks for question count, bilingual fields, source links, legacy-progress migration, and answer-position rotation.

## Disclaimer and limitations

This feature is for education and research only; it is not investment, tax, or legal advice. Sources are verified, but financial products, regulations, and company-specific information can change. Learners should verify current official disclosures and make decisions according to their own goals, horizon, and risk tolerance.
