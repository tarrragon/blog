# US and International Equities Verification

> **Role**: Operational reference for the `business-research` skill — extends the data-access-layering model and verification playbooks beyond Taiwan to US equities (primary) and other major markets (Japan, Europe).
>
> **When to read**: When the research target is a US-listed company (or a global peer used for lateral comparison), or when comparing companies across markets with different accounting and payout conventions.

## US Layer Structure: Layer 3 Is the Cheap Layer

Taiwan's pattern (aggregator pages easy, regulator filings heavy) inverts in the US. SEC EDGAR is free, structured, and machine-readable — for US companies, go to layer 3 early instead of treating it as a last resort.

| Layer | Tool | Notes |
| --- | --- | --- |
| 1. Search snippets | Web search | Same limits as everywhere — single points, no series |
| 2. Aggregator pages | stockanalysis.com（乾淨的 10 年報表表格）、macrotrends.net（10 年以上 ROE/毛利率/P/E 序列頁） | Browser scrape works; good for quick longitudinal series |
| 3. SEC EDGAR | Full-text search UI（efts.sec.gov / sec.gov/edgar/search）；XBRL company facts API：`data.sec.gov/api/xbrl/companyfacts/CIK{10位數}.json`（免費 JSON、需帶 User-Agent header） | The authoritative original — structured fundamentals for the full filing history |

## Filing Types Mapped to Analytical Purpose

| Filing | Content | Serves |
| --- | --- | --- |
| 10-K（年報） | Segment data, capex and D&A footnotes, risk factors, full audited statements | Segment margin decomposition; the maintenance-vs-growth capex split that aggregators never carry |
| 10-Q（季報） | Quarterly statements | Trend confirmation, TTM reconstruction |
| 8-K + earnings release | Material events; **GAAP vs non-GAAP reconciliation table** | The US equivalent of normalized-EPS work — the reconciliation is mandatory disclosure, use it instead of rebuilding it |
| DEF 14A（股東會說明書） | Executive compensation structure, insider pledging disclosure | Management-alignment check; closest US analog to Taiwan's 董監質押 signal |
| Form 4 | Insider buys/sells within 2 business days | Insider signal — the behavioral counterpart to shareholding trends |
| 13F | Institutional holdings (quarterly) | Ownership shifts; note 45-day lag |

## US-Specific Verification Modes

| Failure mode | How it happens | Prevention |
| --- | --- | --- |
| Non-GAAP quoted as GAAP | "Adjusted EPS" from press releases cited as earnings; adjustments can exclude SBC, restructuring, impairments | Always check the reconciliation table; state which basis a number uses |
| Buybacks ignored in payout analysis | US capital return is dividend + repurchase; dividend yield alone understates payout and distorts the retained-earnings test | Use total shareholder yield; track share count — a shrinking denominator inflates EPS growth without operating improvement |
| Fiscal year offsets | Many US/global companies use non-calendar FY (Tyson ends Sept, Fonterra ends July) | Label every figure with FY end month; align periods before peer comparison |
| TTM vs FY mixing | Trailing-twelve-month values compared against fiscal-year values | State the period basis explicitly |
| Split-adjusted series | Historical prices/EPS retroactively adjusted for splits differ from as-reported | Same rule as Taiwan stock dividends: never mix bases within one series |

## Other Major Markets (Brief)

| Market | Primary sources | Notes |
| --- | --- | --- |
| Japan | 決算短信（tanshin，早於完整財報的季度摘要）、EDINET（申報檔）、company IR pages | Tanshin is the fast layer; segment detail in the 有価証券報告書。Payout culture historically low but rising |
| Europe | Company IR annual/interim reports; exchange filing portals（如 Nasdaq Stockholm for Nordic） | No EDGAR equivalent with uniform structure — IR pages are the practical layer 3 |
| Cross-market comparison | — | Three mandatory labels on every cross-market figure: accounting standard (IFRS / US GAAP / local), FY end month, currency with conversion date. A margin comparison across standards is approximate by construction — say so |

## Equivalents Map: Taiwan Concept → US Source

| Taiwan practice | US counterpart |
| --- | --- |
| MOPS 公開資訊觀測站 | SEC EDGAR |
| 法說會簡報 | Earnings call transcript + investor deck (8-K exhibit) |
| Goodinfo 歷年經營績效 | macrotrends / stockanalysis 10-yr pages, or XBRL API directly |
| 正常化 EPS（手工剔除一次性） | GAAP vs non-GAAP reconciliation（已是強制揭露、直接引用並自行覆核） |
| 董監質押 | Proxy statement insider-pledging disclosure + Form 4 activity |
| 股利連續年數 | Dividend history + buyback history combined（只看股利會誤判配置紀律） |
