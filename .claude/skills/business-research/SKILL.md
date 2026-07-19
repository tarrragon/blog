---
name: business-research
description: >
  This skill should be used when research is needed before writing business analysis — gathering
  financial data, verifying claims, finding industry benchmarks, or fact-checking social media
  business discussions. Triggers on: "find the financial data", "verify this claim", "search for
  company financials", "check if this is true", "gather industry data", "fact-check", "find the
  source", "what does the financial report say", "pull the numbers", "is this accurate",
  "research before writing", "collect data for analysis". Provides a systematic data collection
  and verification workflow to prevent hallucination and ensure analysis is grounded in public data.
---

# Business Research

Systematic data collection and verification workflow for business analysis. Every claim in a business analysis article must trace back to a verifiable source — public financial reports, government statistics, credible news reporting, or company disclosures. This skill prevents the most common failure mode in AI-generated business analysis: **plausible-sounding claims that have no factual basis**.

## Core Principle: No Unsourced Claims

A business analysis article makes two types of statements:

1. **Factual claims** (revenue numbers, market share, dates, ratios) — these must come from verifiable sources.
2. **Analytical judgments** (this strategy is risky, this margin is unsustainable) — these must be derived from factual claims through explicit reasoning.

The failure mode is when analytical judgments masquerade as factual claims ("the industry standard is 35%") without a traceable source. This skill ensures factual claims are sourced and analytical judgments are flagged as such.

## Data Collection Workflow

### Step 1: Identify What Data Is Needed

Before searching, list the specific data points the analysis requires:

| Data type | Example | Why needed |
| --- | --- | --- |
| Financial metrics | Revenue, gross margin, net margin, EPS | Quantify company performance |
| Industry benchmarks | Average margin, typical cost ratio | Provide comparison baseline |
| Historical data | Revenue trend over 8+ quarters | Distinguish structural from one-time |
| Event timeline | When did the acquisition happen, when did the policy change | Establish causation sequence |
| Competitive data | Peer companies' metrics | Enable cross-company comparison |

Prioritize: financial metrics and event timelines are highest value (most verifiable); industry benchmarks are medium (often experience-based); qualitative claims are lowest (hardest to verify).

### Step 2: Source Hierarchy

Use sources in order of reliability. Higher-tier sources override lower-tier when they conflict.

| Tier | Source type | Reliability | Example |
| --- | --- | --- | --- |
| 1 | Audited financial statements | Highest | Annual reports on MOPS, SEC filings |
| 2 | Company official disclosures | High | Earnings calls, investor presentations, press releases |
| 3 | Government statistics | High | Agricultural ministry data, central bank reports, census |
| 4 | Credible journalism | Medium-High | Investigative reporting with named sources (報導者, 天下, 商周) |
| 5 | Industry association reports | Medium | Trade association surveys, industry white papers |
| 6 | Analyst reports | Medium | Brokerage research, but note potential conflicts of interest |
| 7 | Social media / forums | Low | Useful for qualitative signals but never for factual claims |

**Taiwan-specific sources:**
- **MOPS (公開資訊觀測站)**: Listed/OTC company financial statements, material announcements, insider transactions
- **財報分析工具**: Goodinfo, 財報狗, StockFeel — aggregated financial data with calculated ratios
- **農業部統計**: Livestock counts, crop production, import/export data
- **主計總處**: Industry-level economic statistics
- **公平交易委員會**: Merger approvals, market concentration data

### Step 3: Search Strategy

**For company-specific data:**
1. Search company name + stock code + "財報" + year
2. Search company name + "法說會" (earnings call) for management commentary
3. Cross-reference numbers from at least two independent sources

**For industry data:**
1. Search industry + "產業分析" + year for overview reports
2. Search industry + specific metric (e.g., "毛利率" "市佔率") for benchmarks
3. Check government ministry websites for official statistics

**For event verification:**
1. Search event + date for original reporting
2. Look for follow-up reporting that confirms or corrects initial reports
3. Check for official announcements (company filings, government notices)

### Step 4: Verification Checklist

Before using any data point in analysis, verify:

| Check | How | Red flag |
| --- | --- | --- |
| Source exists | Can the original document/report be located? | "Industry sources say" without attribution |
| Number is current | Is there a more recent figure available? | Using 2020 data when 2025 exists |
| Context is preserved | Is the number being used in its original context? | Gross margin cited as net margin |
| Calculation is reproducible | Can the derived number be recalculated from inputs? | "Growth rate of X%" without base and comparison period |
| Conflicts are noted | Do different sources give different numbers? | Cherry-picking the most favorable source |

### Step 5: Hedging Uncertain Claims

When data is incomplete or sources disagree, use explicit hedging:

| Certainty level | Hedging language | When to use |
| --- | --- | --- |
| Verified | State directly: "2025 年營收 30.4 億（揚秦年度財報）" | Tier 1-2 source, cross-verified |
| Estimated | "估計" / "推估": "設備投資估計 100 萬（量級估算）" | Reasonable inference from partial data |
| Experience-based | "經驗法則" / "業界常見": "食材成本 35% 是餐飲業常見的經驗基準" | No single authoritative source |
| Speculative | Avoid in analysis; route to "further research needed" | No supporting data at all |

**Critical rule**: Never present experience-based benchmarks as verified facts. "The industry standard is 35%" requires either a source or the label "experience-based benchmark."

## Common Verification Failures

| Failure mode | How it happens | Prevention |
| --- | --- | --- |
| **Hallucinated statistics** | AI generates plausible-sounding numbers | Every number must trace to a search result or calculation |
| **Outdated data presented as current** | Using old reports without checking for updates | Always search with current year; label data with its period |
| **Survivorship bias in benchmarks** | "Average franchise profit is X" based on surviving stores only | Note the bias explicitly when using such data |
| **PR claims as facts** | Company press release numbers taken at face value | Cross-check PR claims against financial statements |
| **Single-source dependency** | Entire analysis built on one article | Cross-reference key claims from at least two independent sources |
| **Confusing revenue with profit** | "This company makes X billion" without specifying metric | Always specify: revenue, gross profit, operating profit, or net income |

## Supply Chain and Competitor Cross-Verification

A company's own financial report is a self-portrait — it shows what the company wants investors to see, within accounting rules. Supply chain verification and competitor lateral checks reveal what the self-portrait omits or distorts. This applies to ALL companies, listed or not.

### Principle: No Single-Company Analysis

Every factual claim about a company should be checkable from at least one external vantage point:

| Vantage point | What it reveals | Example |
| --- | --- | --- |
| Upstream supplier | Whether the company's cost claims are plausible | Fonterra's farmgate milk price confirms the floor cost for any Taiwan importer |
| Downstream customer | Whether the company's revenue claims match observable market presence | A chain with 7,000 stores each using 5L/day implies minimum monthly volume |
| Competitor with public data | Whether margins, growth rates, or cost ratios are structurally consistent across the industry | If competitor's margin is 8% and target claims 25% in the same commodity business, investigate |
| Industry regulator/association | Whether volume claims match aggregate statistics | Total import volume from customs data caps how much any single importer can be handling |

A company reporting 40% gross margin in a commodity industry where peers report 15-21% is either doing something structurally different (verify what) or misrepresenting (flag it). The competitor's report IS the verification tool.

### Competitor Lateral Checks

When analyzing Company A, search for Company B (competitor in the same segment) and compare:

1. **Margin plausibility**: If 大成's feed business has 5-10% gross margin, any competitor claiming 30% in the same feed segment needs explanation
2. **Growth rate consistency**: If the whole industry grew 5% but one company claims 30%, either they took share (verify from whom) or the claim is suspect
3. **Cost structure ratios**: Rent/revenue, labor/revenue, materials/revenue should be in similar bands for same-format businesses (e.g., all convenience stores have ~30% operating expense ratios)
4. **Annual report language cross-check**: When 統一's annual report changes language from "supply shortage" to "demand weakness," check if 光泉 and 味全's reports echo the same shift — consensus among competitors confirms it's structural, not company-specific

### Upstream/Downstream Verification

Verify a company's business logic through its position in the supply chain:

| Direction | What to look for | Verification method |
| --- | --- | --- |
| Upstream (suppliers) | Does the supplier's public data confirm the claimed relationship? | Global suppliers (Fonterra, Bega) sometimes list distributors; customs data shows import volumes by destination |
| Downstream (customers) | Do customers' reports or product labels confirm sourcing? | 7-11's "咖啡專用乳" ingredient label confirms who supplies them; franchisee cost breakdowns confirm mother-company markup |
| Competitor (lateral) | Do peers' financials bracket the plausible range? | Same-industry peers' margins set the ceiling and floor for claims |
| Aggregate (industry) | Do individual claims add up to industry totals? | If 4 importers each claim 40% market share, someone's lying |

Physical infrastructure is particularly hard to fabricate: 30 offices nationwide, 100+ delivery trucks, factory automation lines. These serve as floor estimates for business scale even without revenue data.

### Dual-Role Detection

In Taiwan's concentrated industries, the same company often occupies competing positions simultaneously — domestic producer AND importer, brand owner AND private-label manufacturer, retailer AND wholesaler. When a company has dual roles:

1. Its self-reported financials blend two businesses with conflicting incentives
2. Profitability claims for either role are suspect (internal transfer pricing can shift profit between roles)
3. The company's BEHAVIOR (which role is it investing in? which is it shrinking?) reveals its true strategic bet better than reported margins

Detection: check if the company appears in BOTH domestic production registries AND import/export records; search agricultural ministry reports (domestic role) AND customs statistics (import role); look for industry reporting that names them in both capacities.

### When the Target Company Has No Public Financials

Many critical supply chain participants in Taiwan are unlisted family businesses or farmer cooperatives. The verification goal shifts from "find the number" to "verify the business logic through structural evidence."

**Corporate registry lookup:**

| Source | What it reveals |
| --- | --- |
| 台灣公司網 (twincn.com) | Capital, representative, directors, establishment date |
| 104 人力銀行 | Employee count, capital, industry classification |
| TEJ 台灣經濟新報 | Corporate group analysis, case studies (covers private companies) |
| 經濟部商工登記 (findbiz.nat.gov.tw) | Official registration, paid-in capital, board changes |

**Holding structure detection:** Taiwan family businesses commonly layer 控股公司 → 營運公司. Find the operating company's corporate shareholder → look up that holding company → check its directors and shareholders for the actual ownership family. If family members appear in a listed company's annual report as related parties, the private company's activities may be partially visible through related-party transaction disclosures.

**Explicit limitation marking in articles:** When a company is important to the story but financially unverifiable:
1. State its supply chain role
2. State what IS verifiable (registry data, infrastructure, upstream/downstream evidence)
3. State what is NOT verifiable (revenue, margins, import volumes)
4. Never estimate financials without a source — "revenue approximately X" is a hallucinated statistic even if directionally correct

## Integration with business-analysis Skill

This skill provides the data foundation for [`business-analysis`](../business-analysis/SKILL.md). The workflow:

1. **business-analysis** Step 1 identifies what analysis is needed
2. **business-research** gathers and verifies the data
3. **business-analysis** Steps 2-7 perform the analysis on verified data

When writing business analysis articles, invoke this skill first to collect data, then invoke business-analysis for the analytical framework.

## Output: Source Log

Every research session should produce a source log — a list of all data points used and their sources. Format:

```text
| Data point | Value | Source | Tier | Verified by |
| Revenue 2025 | 30.4 億 | 揚秦年度財報 | 1 | MOPS filing |
| Store count | 955 | 法說會 2025/12 | 2 | Cross-checked with news |
| Food cost benchmark | 35% | Industry experience | 5 | Labeled as experience-based |
```

This log becomes the article's source attribution and enables future verification when data ages.

---

**Version**: 1.2.0 — Restructured private company section into broader "Supply Chain and Competitor Cross-Verification" principle: single-company financial reports are self-portraits that require external validation. Added competitor lateral checks (margin plausibility, growth consistency, cost ratio bands, annual report language cross-check), upstream/downstream verification as universal method (not just for private companies), dual-role detection for companies with conflicting positions. Private company registry lookup retained as sub-section. Derived from dairy import economics research where competitor cross-check (統一 vs 光泉 annual report language shift) and upstream verification (Fonterra farmgate price as cost floor) proved more informative than any single company's self-reported data.
