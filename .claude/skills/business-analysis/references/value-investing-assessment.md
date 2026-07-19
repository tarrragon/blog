# Value Investing Assessment

> **Role**: Operational reference for the `business-analysis` skill — extends Step 4 (valuation) from "is this business viable" to "is this stock mispriced relative to intrinsic value" (Buffett-style value investing).
>
> **When to read**: When the analysis goal is an investment decision on a listed company — identifying whether current price underestimates durable earning power, or whether apparent cheapness is a trap.

## Boundary: Business Analysis vs Investment Analysis

Business analysis answers "is this a good company" (margins, positioning, strategy). Investment analysis answers "is this a good price for this company" — a comparison that requires data business analysis alone never collects: historical valuation bands, market cap series, capital efficiency ratios. A complete company analysis with no price data cannot support a buy/avoid judgment. State this limitation explicitly rather than letting a business-quality conclusion masquerade as an investment recommendation.

## Three-Gate Screen

All three gates must pass. A failure at any gate vetoes the investment regardless of the other two.

### Gate 1: Moat Durability

The moat test is pricing power through downturns — not margin level in good years.

| Check | Method | Pass signal |
| --- | --- | --- |
| Margin stability across cycles | Pull 10-year gross margin series; find the worst 2 years | Margin floor stays above peer median even in bad years |
| Pricing power direction | Did prices rise with (or faster than) input costs during inflation? | Cost pass-through within 2-3 quarters |
| Customer switching cost | What must a customer change to switch supplier? | Concrete switching activities (production line recalibration, recertification), not just habit |
| Moat type identification | Scale / network / switching cost / brand / regulatory license / formula-patent | At least one structural moat, named specifically |

Single-year high margin is a cycle observation, not a moat observation. A company earning 21% gross margin at the top of a livestock price cycle may have a structural floor of 16% — the moat is the floor, not the peak.

### Gate 2: Management Quality (Capital Allocation)

Judge management by what they do with retained earnings, not by narrative.

| Check | Method | Red flag |
| --- | --- | --- |
| Retained earnings test | Over 10 years: for each $1 retained (not paid out), did market value grow more than $1? | Retained capital compounding below index returns |
| Dividend consistency | 10-year dividend record | Cuts without corresponding earnings collapse; erratic policy |
| M&A track record | Did past acquisitions reach their stated targets? | Serial acquisitions with no follow-up disclosure of returns |
| Capex return trail | Prior expansion projects: did they generate the projected revenue/margins? | Capex direction announced but returns never reported |
| Insider alignment | Director/major shareholder ownership trend | Insiders reducing while promoting growth narrative |

### Gate 3: Price Below Intrinsic Value

| Check | Method | Note |
| --- | --- | --- |
| Normalized earnings basis | Strip one-time items (cycle windfalls, disposal gains) before applying any multiple | Valuing peak-cycle EPS at average multiples double-counts the good year |
| Historical valuation band | Current P/E and P/B vs the company's own 10-year percentile | "13x" is meaningless without knowing whether the stock's band is 8-15x or 12-25x |
| Owner earnings | Net income + D&A - maintenance capex (exclude growth capex) | Requires splitting maintenance vs growth capex — ask what spending merely keeps current revenue |
| Margin of safety | Buy only when price is materially below conservative intrinsic estimate | The discount absorbs estimation error; without it, precision of the estimate becomes the bet |

## Capital Efficiency Screen

Margins measure product economics; ROE measures owner economics. A 13% gross margin business with high asset turnover can be a better owner outcome than a 30% margin business that consumes capital.

- **10-year ROE series**: consistent ROE above ~15% without rising leverage is the primary quantitative filter.
- **DuPont decomposition**: ROE = net margin × asset turnover × leverage. Identify which lever drives ROE — turnover-driven and margin-driven ROE are durable; leverage-driven ROE is fragile.
- **ROIC vs WACC**: value is created only when return on invested capital exceeds cost of capital. High-capex transformations must eventually show ROIC above hurdle, or the growth destroys value.

## Taiwan-Specific Governance Signals

| Signal | Where to find | Interpretation |
| --- | --- | --- |
| 董監質押比率 (director share pledges) | Public company filings (MOPS) | High or rising pledge ratios precede governance crises; pledged shares create forced-selling and control-defense incentives misaligned with minority shareholders |
| Related-party transaction magnitude | Annual report footnotes | Rising intercompany volume shifts profit between entities; margin of any single entity becomes unreliable |
| Ownership dispute activity | News + shareholding changes | Active control contests divert management attention and can trigger defensive asset sales at bad prices |
| Cross-shareholding / JV opacity | Group structure mapping | Unlisted JVs carrying critical operations (production, procurement) escape disclosure — risk hides where reporting doesn't reach |

## Value Window Identification

The recurring pattern for entry timing: reported earnings compressed by a one-time or cyclical shock while structural signals remain positive.

| Signal set | Reading |
| --- | --- |
| Earnings down + capex up + operating cash flow positive + new products launching | Transforming under pressure — market prices the compressed earnings, structure is improving unpriced |
| Earnings down + capex frozen + short-term debt rising | Being crushed — cheapness is justified |
| Earnings up sharply + windfall component identified | Cycle peak — normalize before valuing; often the worst entry despite best headlines |
| Complex holding structure obscuring operating earnings | Potential mispricing from opacity — but only actionable after YOU decompose the one-timers; unresolved opacity is your blind spot too |

## Value Trap Taxonomy

Cheap is a starting condition, not a conclusion. Three trap types that pass a naive price screen:

1. **Damaged-moat trap**: price collapsed because the moat (brand trust, license, technology relevance) was structurally impaired. Test: does the moat have a credible recovery path with a timeline, or does recovery depend on customers forgetting? Consumer trust damage routinely persists 5-10 years.
2. **Governance trap**: assets and earnings intact but controlled by parties whose interests oppose minority shareholders. No price is low enough when the person allocating your capital is working against you.
3. **Structural-decline trap**: low multiple on earnings that are themselves in secular decline (technology substitution, demand migration). The E in P/E keeps falling to meet the P.

## Output Addition

When this reference is used, extend the standard output with:

1. **Three-gate scorecard** (moat / management / price — pass, fail, or insufficient data per gate)
2. **Data sufficiency statement** — which of the required series (10-year ROE, valuation band, pledge ratio, owner earnings) were actually obtained; a gate assessed without its data is marked "insufficient data", never silently passed
3. **Value window classification** (transforming-under-pressure / crushed / cycle-peak / opacity) with the specific signals observed
4. **Trap check** — explicitly test all three trap types before concluding a low price is an opportunity
