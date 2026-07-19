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

## Private Company Research: When Financial Data Doesn't Exist

Taiwan's traditional industries are relationship-driven. Many critical supply chain participants are unlisted family businesses or farmer cooperatives without public financials. The skill's verification workflow must adapt — the goal shifts from "find the number" to "verify the business logic through structural evidence."

### Step 1: Corporate Registry Lookup

Before assuming a company has no verifiable data, check:

| Source | What it reveals | URL pattern |
| --- | --- | --- |
| 台灣公司網 (twincn.com) | Capital, representative, directors, establishment date, address | twincn.com/item.aspx?no={統編} |
| 104 人力銀行 | Employee count, capital, industry classification | 104.com.tw/company/{id} |
| TEJ 台灣經濟新報 | Corporate group analysis, even for private companies (case studies, group structure) | tejwin.com |
| 經濟部商工登記 | Official registration, paid-in capital, board changes | findbiz.nat.gov.tw |

Capital amount and employee count from registry data give a rough revenue estimate (food industry typically generates 3-6x capital in annual revenue; service industry 1-3x).

### Step 2: Holding Structure and Affiliations

Taiwan family businesses commonly use a layered structure: 控股公司（holding）→ 營運公司（operating）. The holding company owns 100% of the operating entity; the family's actual ownership is in the holding company's shareholder register.

Check sequence:
1. Find the operating company's shareholder — is it a 法人 (corporate entity)?
2. If yes, look up that entity — that's the holding company
3. Check the holding company's directors and shareholders — that's the actual ownership family
4. Search whether any of these individuals or the holding company appear in other public company filings (as directors, major shareholders, or related parties)

If the holding company or family members appear in a listed company's annual report as related parties, the private company's activities may be partially visible through the listed company's related-party transaction disclosures.

### Step 3: Upstream/Downstream Verification

When financial statements don't exist, verify the company's business logic through its supply chain relationships:

| Direction | What to look for | Verification method |
| --- | --- | --- |
| Upstream (suppliers) | Who supplies raw materials to this company? | Search company name + supplier brands; check if global suppliers (Fonterra, Bega) list them as distributor |
| Downstream (customers) | Who buys from them? What channels do they serve? | Industry reports mentioning their products; their own marketing materials listing client types |
| Infrastructure | Physical assets (factories, warehouses, vehicle fleets, branch offices) | Company website, 104 job listings (office locations), Google Maps satellite imagery of registered address |
| Scale proxies | Employee count, number of offices, fleet size | 104/LinkedIn employee count; industry case studies (TEJ); company "About" page |

The presence of infrastructure (30 offices nationwide, 100+ delivery trucks) is harder to fabricate than revenue claims. Physical assets serve as a floor estimate for business scale.

### Step 4: Dual-Role Detection

In Taiwan's concentrated industries, the same company often occupies competing positions in the value chain simultaneously — domestic producer AND importer, brand owner AND private-label manufacturer, retailer AND wholesaler. Detect this by:

1. Check if the company appears in BOTH domestic production registries AND import/export records
2. Search for the company name in agricultural ministry reports (domestic role) AND in customs/trade statistics (import role)
3. Look for industry reporting that explicitly names them in both capacities

Dual-role companies have structural conflicts of interest that explain their behavior better than financials alone. When a domestic dairy farmer also imports competing frozen concentrate, the conflict tells you more about market dynamics than any balance sheet would.

### Step 5: Explicit Limitation Marking

When a company is important to the industry story but financially unverifiable, the article must:

1. **State the company's role** — what it does in the supply chain
2. **State what IS verifiable** — registry data, infrastructure, upstream/downstream relationships, industry reports citing them
3. **State what is NOT verifiable** — revenue, profit margins, import volumes, cost structure
4. **Never estimate financials** — "revenue approximately X" without a source is a hallucinated statistic even if it's directionally correct

Template: "[Company] is an unlisted company (capital X, ~Y employees per 104). No public financial data exists to verify revenue or profitability. Its role in the supply chain is confirmed by [upstream supplier evidence] and [downstream customer evidence]."

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

**Version**: 1.1.0 — Added private company research methodology: corporate registry lookup (台灣公司網, 104, TEJ, 商工登記), holding structure detection, upstream/downstream verification when financials don't exist, dual-role conflict detection, explicit limitation marking protocol. Derived from dairy import economics research session where key supply chain participants (開元食品, 台灣牧場) had no public financials.
