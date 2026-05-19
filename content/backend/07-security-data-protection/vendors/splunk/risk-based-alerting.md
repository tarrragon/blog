---
title: "Splunk Risk-Based Alerting：從 alert per rule 到 score-aggregated notable"
date: 2026-05-18
description: "Splunk Enterprise Security 的 RBA 方法論：risk score / modifier / notable 三層 model、ES 配置 step-by-step、tuning playbook（false positive / score inflation / threshold drift / decay）、capacity 成本、跟 SOAR + case management 整合"
weight: 10
tags: ["backend", "security", "splunk", "detection", "rba", "deep-article"]
---

> 本文是 [Splunk](/backend/07-security-data-protection/vendors/splunk/) overview 的 implementation-layer deep article。Overview 已說明 Splunk Enterprise Security 在 SIEM / Detection 譜系的定位、本文聚焦 *Risk-Based Alerting (RBA)* 的實作層 — 從「per-rule alert」轉到「score 累積 + threshold 觸發 notable」的方法論轉變、跟 tuning / scaling / 整合的具體做法。

## 為什麼 RBA：alert fatigue 是 detection engineering 的天花板

Detection engineering 的成熟度上限不是「能寫多少 correlation rule」、是「SOC analyst 能處理多少 alert / day 而不會麻木」。多數 SOC 在 200-500 alert/day 區間就到處理上限、再加 rule 只會推升 false positive、analyst 開始 silent ignore 中低嚴重度 alert。

RBA 的核心轉折是 *把 alert 邏輯從「rule 觸發」拆成「score 累積」*：每個 detection rule 不直接產 alert、而是給 *user / asset / process* 加 risk score；多個低嚴重訊號累積到 threshold 才產 notable（高優先 case）。SOC 看的不是「rule X 觸發了」、是「user Y 今天累積 70 分、上週 12 分」。

RBA 不是 *寫 detection rule 的替代*、是 *aggregation 跟 prioritization 的新層*。原本 100 條 rule 各自產 alert 變成 100 條 rule 共同貢獻 score、score → notable 是新的 alert 邊界。

## RBA 三層 model：modifier、score、notable

Risk 流程的三個 first-class object：

| Object            | 責任                                                               | 例                                                   |
| ----------------- | ------------------------------------------------------------------ | ---------------------------------------------------- |
| **Risk modifier** | 一條 detection rule 產出、提供「給誰加多少分、為什麼、什麼類別」   | user `alice@corp` +25 分、reason `unusual_login_geo` |
| **Risk index**    | 累積所有 modifier、依時間衰減；query 出「user / asset 當前 score」 | `index=risk earliest=-7d`                            |
| **Risk notable**  | 當 score 累積超過 threshold 觸發、進 SOC case management           | user 累積 50 分 → 開 incident                        |

關鍵設計選擇都在 modifier 層：

- **加分維度**：per user / per asset / per process tree / per IP — 維度越細粒度、score 越能對應「個體」、但 query 成本越高
- **加分 weight**：簡單做法 severity 直接對應（low=5 / med=15 / high=30 / critical=60）；細做要考慮 *signal precision*（rule 的歷史 FP rate）
- **MITRE ATT&CK 對應**：每個 modifier 標 tactic / technique、跟 ATT&CK 對應、用來判斷 *kill chain 階段* 是否完整（reconnaissance → exfiltration 全套出現 vs 單一 tactic 重複）

## ES 配置 step-by-step

### Risk modifier 從 correlation search 產出

```spl
| search index=auth user=* unusual_geo=true
| stats count by user, src_ip, _time
| eval risk_score=25
| eval risk_object_type="user"
| eval risk_object=user
| eval risk_message="Unusual login geography"
| eval threat_object=src_ip
| eval threat_object_type="ip_address"
| eval mitre_technique="T1078"
| collect index=risk
```

關鍵欄位：

- `risk_object` + `risk_object_type`：誰被加分、預設 user / system / other
- `risk_score`：加多少分、考量 signal precision
- `threat_object`：對應的 attacker artifact（IP / hash / domain）、用來跨 modifier 關聯
- `mitre_technique`：對應 ATT&CK ID、用於 kill chain analysis

*Tuning 提醒*：第一次部署別直接 `collect index=risk`、先 `| table` 看 output、估算每天會產多少 modifier；超出 indexer 容量規劃前先做 sampling（`| where random()/2147483647<0.1` 取 10%）。

### Risk notable：threshold aggregation

```spl
| tstats summariesonly=t count, sum(All_Risk.calculated_risk_score) as total_risk
  from datamodel=Risk.All_Risk
  where earliest=-24h
  by All_Risk.risk_object, All_Risk.risk_object_type
| where total_risk > 80
| `risk_score_format`
```

`total_risk > 80` 是觸發 notable 的 threshold。Tuning 重點：

- **Time window**：-24h 是預設、但要看 *attack pattern average duration* 調整；APT 用 7-14 day window、commodity attack 用 4-12h
- **Threshold value**：80 是 *當量* 不是普世值、依 modifier weight 分佈調整；ES 7.0+ 預設建議 100、實務多在 60-150 區間
- **Aggregation 維度**：by user 是 default、但 lateral movement scenario 要 by asset、credential abuse 要 by service account

*Tuning 提醒*：第一週跑 *shadow mode* — 觸發 notable 但不 page、SOC 後續 review、調整 threshold 跟 weight；shadow 跑 1-2 週後再啟 production page。

### Notable enrichment：人類能看的 case

```spl
| eval description="User ".risk_object." accumulated ".total_risk." risk over 24h"
| eval mitre_techniques=mvjoin(mitre_technique, ", ")
| eval contributing_rules=mvjoin(search_name, ", ")
| sendalert notable
```

Notable 進入 ES Incident Review、SOC analyst 看到的不只 score、還有 *組成這 80 分的 N 條 rule + ATT&CK 覆蓋的 tactic*；這是 RBA 比 per-rule alert 強的核心 — analyst 直接看完整 narrative、不用拼湊。

## Tuning playbook：四類常見 drift

### Playbook A：False positive 累積

**徵兆**：某 user 連續 N 天觸發 notable、SOC 每次 review 後 close 為 FP；但 modifier 仍持續加分。

**根因**：modifier 加分邏輯沒考慮 baseline — 例：DBA 每天用 `psql` 連 prod 是正常、`unusual_command` rule 把它當異常加 15 分、累積到 threshold。

**修法**：

1. Modifier 端加 `whitelist_lookup`：DBA / SRE / approved service account 跳過 specific modifier
2. 進階：modifier 加 `signal_precision` weight、historical FP rate > 30% 的 rule weight 降到 5 分以下
3. 不能輕易加 `NOT user IN (...)` exclusion、long whitelist 是反模式 — 用 *role-based exclusion*（query AD group）

### Playbook B：Score inflation

**徵兆**：threshold 設 80、SOC 收到的 notable 每 day 從 5 個漲到 25 個、但「實際攻擊」沒對應增加。

**根因**：新加的 detection rule 沒對齊既有 weight 分佈、新 rule 都給 +30 / +40、global average 抬升、threshold 變相降低。

**修法**：

1. 每加新 rule 時跑「+1 rule 對 daily notable 數的影響」shadow simulation
2. 重新 calibrate threshold — 不是固定值、是 *p95 daily total_risk 的 1.5 倍*
3. 季度 review：跑 `index=risk | stats sum(risk_score) by source` 看 modifier 來源分佈、score 集中在少數 rule 是 inflation 訊號

*Tuning 提醒*：score inflation 跟 alert fatigue 是同樣症狀的不同根因；前者改 threshold + rule weight calibration、後者改 modifier 維度跟 whitelist。

### Playbook C：Threshold drift

**徵兆**：threshold 設定半年沒動、但 attack landscape / business 行為都變了；要嘛 notable 太多（threshold 低於 baseline）、要嘛 missed detection（threshold 高於實際攻擊累積）。

**根因**：threshold 是 *static value、但 baseline 是 dynamic*；business 流程變動（雲端遷移 / 新部門 / WFH 比例變化）影響 modifier 觸發頻率。

**修法**：

1. Quarterly tuning cadence：每季跑 `tstats sum(All_Risk.calculated_risk_score) by user | stats p50, p95, p99` 看分佈
2. Adaptive threshold：用 `p95 × 1.3` 動態計算、寫 macro 自動 update
3. 不要把 threshold drift 當「rule 不準」、是 *基準漂移*、不是 rule 錯

### Playbook D：Decay 設計

**徵兆**：user 7 天前的低分異常持續累積在 score 內、threshold 觸發 notable 但實際是 *7 天分散事件*、不是 *當前攻擊 episode*。

**根因**：default RBA 在 `-24h` window 內 sum、沒考慮 *時間衰減*；7 天前的低分跟今天的低分權重一樣。

**修法**：加 decay function、modifier weight 隨時間衰減：

```spl
| eval age_hours=(now() - _time)/3600
| eval decayed_score = calculated_risk_score * exp(-age_hours / 48)
| stats sum(decayed_score) as total_risk by risk_object
```

`exp(-age/48)` 是 48 小時半衰期、24h 前的事件權重剩 60%、48h 剩 37%、7 天前剩 < 3%。half-life 依 attack pattern 調整：commodity attack 12-24h、APT 5-14 day。

## Capacity 規劃

RBA 的 capacity 三個面向：

| 維度                 | 估算方式                                                                                | 警戒值                                           |
| -------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Risk index event/day | `總 detection rule × 平均 trigger 次數/day`                                             | 中型 SOC ~100K-500K / day                        |
| Risk datamodel size  | `event/day × 365 day × 1KB avg`                                                         | 100K/day × 365 × 1KB ≈ 36GB / year               |
| Search head load     | RBA tstats 比 raw search 便宜 ~10x、但 by-user aggregation 在 1M+ user 仍重             | 跑 hourly notable trigger search、不是 streaming |
| Indexer ingest       | RBA 不大增 ingest（已 ingest 的 log 處理出 modifier）、但 datamodel acceleration 要 CPU | 每 indexer 預留 10-15% CPU 給 datamodel accel    |

實務 sizing：500K modifier/day、用戶 5K、tstats hourly trigger search、需要 *3 indexer + 1 search head*（含 RBA 之外的工作）。

> 注意 [SC4S / Splunk Cloud](/backend/07-security-data-protection/vendors/splunk/) ingest pricing — RBA 不增 ingest GB / day、但 datamodel acceleration 算 CPU 工作量、Splunk Cloud 是另外計費的 vCPU；on-prem 自管 indexer 沒這個 cost。

## 整合 / 下一步

### 跟 SOAR / case management

Notable 觸發後接 SOAR：

- **enrichment**：自動 query AD / asset DB / threat intel、把 user role / asset criticality / known IoC 補進 case
- **decision tree**：根據 risk score 區間決定 SOC tier（< 100 tier 1 / 100-200 tier 2 / 200+ tier 3 + page）
- **playbook automation**：disable user / isolate endpoint / rotate credential 走 SOAR pipeline、不要 SOC analyst 手動 click

### 跟 [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Sentinel](/backend/07-security-data-protection/vendors/google-security-operations/) 對照

各家對 RBA 的實作命名不同：Splunk 叫 RBA、Elastic 叫 Risk Engine、Microsoft Sentinel 叫 Fusion + UEBA aggregation、Sumo Logic 叫 Insight Trainer；底層概念相同（score aggregation + threshold notable）、細節差在 *modifier 寫法跟 ML 自動化程度*。跨平台遷移時 modifier 邏輯多半要重寫、threshold + decay tuning 經驗可以平移。

### 跟 UEBA

RBA 跟 UEBA（user / entity behavior analytics）是 *互補不是替代* — UEBA 用 ML 算 baseline 偏差、輸出 anomaly score 餵進 RBA 當一個 modifier 來源。實作順序通常是 *先靜態 rule + RBA、再加 UEBA 補充*；直接從 ML-first 開始通常 tuning 成本爆炸。

### 下一步議題

- **Threat object correlation**：跨 modifier 用 threat_object 串相同 attacker artifact、score 跨 user 跨 asset 聚合
- **Kill chain coverage analysis**：notable 拆成「ATT&CK tactic 覆蓋 N/14」、覆蓋越廣 priority 越高
- **Risk-based response automation**：score 區間自動觸發不同 SOAR playbook、人工只 review tier 3

## 相關連結

- 上游 vendor 頁：[Splunk](/backend/07-security-data-protection/vendors/splunk/)
- 對照案例：[Okta Cross-Tenant Impersonation 2023](/backend/07-security-data-protection/cases/okta-cross-tenant-impersonation-2023/)、[Microsoft Storm-0558](/backend/07-security-data-protection/cases/microsoft-storm-0558-signing-key-2023/)
- 上游 chapter：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行 vendor：[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/) / [Google Security Operations](/backend/07-security-data-protection/vendors/google-security-operations/)
- 平行 deep article：[Vault Dynamic Credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
