---
title: "Splunk → Elastic Security Detection Rule Migration：6 段 phased playbook 跟 5 大踩雷"
date: 2026-05-18
description: "從 Splunk Enterprise Security 遷到 Elastic Security 的 detection rule translation playbook：SPL ↔ KQL/ES|QL schema 對位、AI-assisted translation pipeline、parallel run 比對、cutover routing、5 個 production 踩雷（macro 沒對應 / time zone 差異 / summary index 不對位 / alert dedup key 衝突 / 過早 decommission）、capacity / cost 對照"
weight: 11
tags: ["backend", "security", "splunk", "elastic-security", "migration", "detection-rule", "cross-vendor"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/)（source）跟 [Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)（target）兩個 vendor overview。Migration playbook 跟 [vendor deep article methodology](/posts/vendor-deep-article-methodology/) 的 6-section flow 不同 — 是 *phased process*（audit → translation → parallel run → cutover → cleanup）、強調 *時間軸* 跟 *回退邊界*。

## 為什麼遷：cost / multi-vendor / cloud-native 三條 driver

Splunk → Elastic 遷移在 2022+ 變主流選項、driver 通常三條疊加：

| Driver           | 觸發場景                                                                                                                                                                                                               |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Cost**         | Splunk per-GB ingest pricing 在 5+ TB/day 規模累積到無法接受、Elastic fixed-tier pricing 可省 50-70%                                                                                                                   |
| **Multi-vendor** | 想避免 SIEM lock-in、跟 [Sentinel](/backend/07-security-data-protection/vendors/google-security-operations/) / [Datadog Security](/backend/07-security-data-protection/vendors/datadog-security/) 同時跑形成 portfolio |
| **Cloud-native** | 已用 Elasticsearch / Kibana 做 application observability、想統一 stack 走 Elastic Cloud / ECK                                                                                                                          |

反向 driver（Elastic → Splunk）也存在但少數 — 主要是 *合規 / 政府客戶要 Splunk Cloud GovCloud*、或 *Splunk Premium ES 的 RBA + UEBA 成熟度仍領先*。本文聚焦 Splunk → Elastic、反向流程結構相同但 *schema 對位方向相反*。

## 結構：phased migration 不是 6-section deep article

跟 single-feature deep article（[Splunk RBA](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)、Vault dynamic credential）不同、migration playbook 的核心是 *time-sequenced phase* + *回退邊界*。6 段 phase：

| Phase                     | 內容                                                           | 預估時長                                  | 回退邊界                                  |                   |
| ------------------------- | -------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------- | ----------------- |
| **Phase 0：rule audit**   | 盤點 Splunk 端 rule、量化 precision / FP rate / alert volume   | 1-2 週                                    | 不影響 production                         |                   |
| **Phase 1：schema 對位**  | SPL ↔ KQL / ES                                                 | QL、CIM ↔ ECS、index ↔ data view 對應規格 | 1-2 週                                    | 不影響 production |
| **Phase 2：translation**  | rule 一條條轉、AI-assisted + 人工 verify                       | 4-12 週                                   | 翻譯失敗的 rule 退回 manual / 標 deferred |                   |
| **Phase 3：parallel run** | 兩 SIEM 同時跑、alert 兩邊產出、累積 confidence                | 4-8 週                                    | 切回單 Splunk、Elastic 端關 alert         |                   |
| **Phase 4：cutover**      | alert routing 切到 Elastic、Splunk 仍 ingest 但不送 alert      | 1 週                                      | routing 切回 Splunk、半小時內可逆         |                   |
| **Phase 5：cleanup**      | Splunk ingest 停、歷史資料 archive 到 S3、license decommission | 2-4 週                                    | **不可逆** — 過早走會失去歷史查詢能力     |                   |

整個遷移週期 4-9 個月、跟 single deep article 1-2 小時完全不同 scale。

## Phase 0：rule audit 建 baseline

遷移前必須先知道 *current state*：

```spl
-- Splunk rule 盤點
| rest /servicesNS/-/-/saved/searches
  splunk_server=local search="alert"
| where disabled=0
| eval rule_age=now()-strptime(updated, "%Y-%m-%dT%H:%M:%S")
| stats count, avg(rule_age) by app, owner
```

每條 rule 量化四個指標：

| 指標                   | 怎麼算                                                 | 用途                                            |
| ---------------------- | ------------------------------------------------------ | ----------------------------------------------- |
| Alert volume / day     | `index=_audit action=alert_fired rule_name=X` 過 30 天 | 高 volume 先翻、cutover 期間影響大              |
| Precision (TP / total) | SOC review 過去 30 天 alert、標 TP / FP / unknown      | 低 precision 先翻（藉機 fix、不是直接複製問題） |
| Detection coverage     | 對應 MITRE ATT&CK technique                            | 確認 Elastic 端有對應 coverage、不能漏 tactic   |
| Owner / 維護狀態       | rule 的 owner team + 最後 update 時間                  | Owner 失聯的 rule 翻譯成本爆、考慮直接退役      |

**Audit 階段的關鍵決策：哪些 rule 不翻譯** — production 通常 30-50% rule 是 legacy / dead code / 已 deprecated；遷移是 *清理機會*、不是「全部複製過去」。

## Phase 1：Schema 對位

Splunk 跟 Elastic 的 data model 沒有 1:1 mapping、必須先建對位 spec：

| Splunk concept      | Elastic 對應                                  | 對位難度                                             |                          |
| ------------------- | --------------------------------------------- | ---------------------------------------------------- | ------------------------ |
| SPL search language | KQL（簡單）/ ES                               | QL（複雜 query、PG 14+ piped）                       | 中、語法差距大但概念對齊 |
| Index               | Data view（read）/ data stream（write）       | 低、概念相同                                         |                          |
| CIM data model      | Elastic Common Schema (ECS)                   | 中、欄位命名差、有對照表（CIM→ECS open source）      |                          |
| Macros              | Runtime fields / transforms / ingest pipeline | 高、Splunk macro 是 SPL fragment、Elastic 沒對等概念 |                          |
| Lookups             | Enrich processors / lookup index              | 中、邏輯對等但 lifecycle 管法不同                    |                          |
| Correlation search  | Detection rule（KQL / EQL / Threshold / ML）  | 中、Splunk 一條 search、Elastic 拆 rule type         |                          |
| Summary index       | Transform / rollup                            | 高、Splunk `tstats` summary index 概念複雜           |                          |
| Notable event       | Alert + signal（Security app）                | 低、Elastic 7.x+ 已成熟                              |                          |
| Saved search        | Saved query                                   | 低                                                   |                          |
| Dashboard           | Kibana dashboard                              | 中、Splunk XML/SimpleXML 跟 Kibana JSON 不可直接轉   |                          |

**Field mapping 是最大坑**：Splunk 自由 schema（`extract` runtime）vs Elastic 強 type ECS。Splunk 端 `src_ip` 可能是 string；Elastic 端必須 `source.ip` 是 `ip` type — 任何 ingest pipeline 都要先把 raw event 轉成 ECS 結構。

## Phase 2：Translation pipeline

實務 translation 用 *3-tier hybrid*：

### Tier 1: vendor tool（cover 30-50%）

Elastic 官方提供 `splunk-to-elastic` migration assistant（SaaS / on-prem）— 對 *簡單 SPL search* 自動轉 KQL；cover ratio 視 SPL 複雜度而定。

### Tier 2: LLM-assisted（cover 30-40%）

對 *中等複雜* SPL（含 stats / eval / where）、用 Claude / GPT 翻譯：

```text
prompt template:
"Convert this Splunk SPL to Elastic ES|QL. Preserve detection logic. List any
unmappable functions.

SPL:
index=auth action=login user=* | bucket _time span=5m
| stats count by user, src_ip, _time | where count > 10"
```

LLM output 必須 *人工 verify*：

- 對相同樣本資料跑 SPL vs ES|QL、output 對齊
- FP rate 不能 *惡化*
- Threshold / window 對等（5m window 跟 5m window 對應）

### Tier 3: manual（cover 10-30%）

剩下的是：

- 含 macro 跨 SPL fragment 的 rule（macro 必須先展開或 inline）
- 含 summary index 跟 tstats 的高效能 rule
- 用 `transaction` / `streamstats` 的 stateful query

這類 rule 翻譯成 KQL 邏輯後、通常 *效能差 5-20x*（Splunk summary index 是 precomputed、KQL 是 runtime）；要評估 *改用 Elastic transform* 或 *接受效能下降*。

## Phase 3：Parallel run

雙 SIEM 同時跑是 *最重要的 confidence-building 階段*：

```text
                 ┌─→ Splunk ──→ alert ──┐
data source ─┤                          ├─→ alert dedup ──→ SOAR / SOC
                 └─→ Elastic ──→ alert ─┘
```

Dedup 策略：

- **Key**：`rule_name + event_id + timestamp_5min_bucket`
- **Window**：5-10 分鐘（兩端有不同處理 latency）
- **Routing**：dedup 後送 SOAR、SOC 看「來自哪個 SIEM」標籤

跑 4-8 週累積：

| 指標                   | 期望                                          |
| ---------------------- | --------------------------------------------- |
| Alert coverage 一致性  | Elastic 抓到 Splunk 的 95%+ 對應 alert        |
| FP rate 不惡化         | Elastic FP / Splunk FP ≤ 1.2（允許 20% 浮動） |
| Detection latency 對等 | Elastic 端 alert 時間在 Splunk 端 ± 5 分鐘內  |
| Volume / day           | Alert 總數兩端對齊（10% 內）                  |

不對齊的 rule 退回 Phase 2 重新 translation；累積到 95%+ 對齊才能進 Phase 4。

## Phase 4：Cutover — routing 切換

```text
Before cutover:
  Splunk → SOAR (active routing)
  Elastic → SOAR (parallel, marked test)

After cutover:
  Splunk → ingest 持續 / alert disabled
  Elastic → SOAR (active routing)
```

Cutover 期間：

1. PagerDuty / Opsgenie 端 *先建 Elastic integration*、不立刻 disable Splunk
2. 切換 dedup key 的 routing priority — 同一 alert 優先取 Elastic 那條
3. **保留 Splunk ingest** — 不立刻停、提供 fallback 半小時
4. SOC 24h 監視、無異常進入 Phase 5

回退邊界：cutover 失敗（Elastic 端 alert 大量遺漏 / 延遲）→ routing 切回 Splunk、Elastic 端 alert 再標 test、回 Phase 3。回退時間 30 分鐘內。

## Phase 5：Cleanup — 不可逆階段

Splunk ingest 停、license decommission、歷史資料 archive：

```bash
# 1. 歷史 archive 到 S3（Splunk DDAS / Smart Store / 第三方）
splunk export ... | aws s3 cp - s3://splunk-archive/

# 2. 確認 archive 可查（cold storage retrieve test）
# 3. Splunk indexer disable / Splunk Cloud subscription downgrade
```

**不可逆邊界**：Splunk license 退掉、historical query 必須走 S3 + 重 ingest 才能跑、SLA 從即時變天級。決策關鍵：

- 法規 retention（GDPR / SOX / HIPAA）多久
- Incident response 需要 historical query 的頻率
- 翻譯後的歷史資料 indexable in Elastic？多數情況 ECS 跟 CIM 結構差太大、historical 不直接可查

實務 default：Splunk Cloud 保留最低 tier 1 年、Elastic 接新資料；1 年後再評估 archive 策略。

## Production 故障演練

### Case 1：Macro 跨 SPL 沒對應 KQL function

**徵兆**：translation tool 把 macro `\`my_internal_lookup(...)\`` 標 unmappable、人工翻譯後發現 macro 含 3 個巢狀 macro、共 80 行 SPL 邏輯；KQL 端拆成 5 個 runtime field + 2 個 ingest processor 才對等。

**修法**：

1. **Audit 階段** 用 `splunk btool savedsearches list | grep <macro>` 找所有 macro 使用點、估翻譯成本
2. **Inline 策略**：macro 在 5 處以下、直接 inline 到 detection rule、不重建 KQL macro
3. **Ingest processor 策略**：macro 是 *資料轉換* 邏輯、放 Elastic ingest pipeline、不放 detection rule
4. **退役策略**：macro 已 deprecated、不翻譯、把使用的 rule 一起退役

### Case 2：Time zone parsing 差異

**徵兆**：parallel run 階段、Splunk 跟 Elastic 對同一個 raw event 解出的 `_time` 差 8 小時；dedup key 沒對齊、雙 alert 都觸發。

**根因**：Splunk `_time` 是 epoch、time zone 由 `props.conf` 端決定；Elastic ingest pipeline 用 `date` processor、time zone 預設 UTC。raw event 有 `Asia/Taipei` timestamp、Splunk 解 UTC、Elastic 解 local。

**修法**：

1. **Ingest pipeline 統一**：所有 raw event 在 ingest 時轉 UTC、不依賴 source-side time zone
2. **dedup 容忍 window**：dedup window 拉到 30 分鐘、cover time zone 漂移
3. **schema 對位 spec 明示時區處理**：Phase 1 spec 要列「所有時間戳統一 UTC」

### Case 3：Summary index 翻譯效能爆

**徵兆**：Splunk 端 `tstats count from datamodel=Authentication where _time>=-7d` 跑 2 秒、翻譯成 KQL 後 Elastic 跑 45 秒；SOC dashboard 端 timeout。

**根因**：Splunk summary index 是 *precomputed*（小時 / 天聚合預先算好）、`tstats` 直接讀 summary；KQL 直接跑 search 是 *raw event scan*、效能差數量級。

**修法**：

1. **Elastic Transform**：Elastic 端建 *continuous transform*、把 raw event 預先 aggregate 到 transform index、KQL 查 transform index、效能對等
2. **Rollup index**（Elastic legacy）：給 metric-style data 用、deprecated 但仍可
3. **接受 latency**：dashboard query 可接受 30s、不必精準對等 Splunk

### Case 4：Cutover 期間 PagerDuty dedup key 衝突

**徵兆**：cutover 後 24h、SOC 收到雙倍 alert；PagerDuty 兩條 incident 各標 `splunk` 跟 `elastic` source、實際是同一事件。

**根因**：PagerDuty 的 dedup key 用 `rule_name + alert_id`、Splunk alert_id 跟 Elastic signal_id 命名空間不同、PagerDuty 視為兩個獨立 incident。

**修法**：

1. **預先設計 dedup key**：用 `rule_name + event_hash`、不用 SIEM 內部 ID
2. **PagerDuty routing rule**：cutover 期間 disable Splunk source routing、不要靠 dedup
3. **Phase 3 parallel run 期間就測試 dedup**：不要拖到 cutover 才發現

### Case 5：過早 decommission Splunk、歷史 incident 無法回溯

**徵兆**：cutover 後 6 個月、發生 incident、需要回查 12 個月前的 auth log；Splunk 已 decom、Elastic 端歷史資料缺、S3 archive 無索引、4 小時找不到 evidence。

**根因**：Cleanup phase 過早走、沒先做 *historical query rehearsal*；S3 archive 沒可用的索引層。

**修法**：

1. **預防**：Phase 5 前跑 *5 個 historical query drill*、驗證 incident response 時能用
2. **架構**：S3 archive 配 Elastic frozen tier（searchable snapshot）、6 個月 retrieve latency 接受
3. **法規對齊**：Cleanup 時間表必須跟 compliance retention requirement 對齊、不只是 cost-driven

## Capacity / cost 對照

| 維度                      | Splunk Enterprise / Cloud               | Elastic Security                              | 取捨                                    |
| ------------------------- | --------------------------------------- | --------------------------------------------- | --------------------------------------- |
| Pricing model             | per-GB ingest（昂貴 in scale）          | fixed tier / data tier / per-resource         | Elastic 5+ TB/day 規模便宜 50-70%       |
| Ingest performance        | 強、Splunk forwarder 成熟               | 強、Elastic Agent / Filebeat                  | 略接近、Splunk 對 unstructured raw 略優 |
| Search performance        | 強、SPL + summary index                 | 中、KQL runtime + transform                   | Splunk 對複雜 query 仍領先              |
| Detection content         | ES content + SOC content                | Elastic Security 内建 detection rule + 開源   | 兩端都有、Elastic 對 cloud-native 較強  |
| UEBA / ML                 | ES Premium UEBA、成熟                   | Elastic ML + 7.x+ rule type                   | Splunk 領先、Elastic 追趕中             |
| Cloud-native              | Splunk Cloud（managed but proprietary） | Elastic Cloud / ECK on K8s                    | Elastic 更 K8s-friendly                 |
| Lock-in                   | 高（SPL / 自家 forwarder / ES app）     | 中（open-source core + commercial extension） | Elastic 較易遷出（理論上）              |
| Total cost (5y, 10TB/day) | $5-15M USD                              | $1.5-5M USD                                   | 5-3 倍差                                |

## 整合 / 下一步

### 跟 SOAR 整合

[PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / Tines / Splunk SOAR：

- cutover 期間 SOAR playbook 仍用 Splunk-shaped event、Phase 5 後改 Elastic-shaped
- Playbook 內 SPL query 必須改寫 KQL / ES|QL、可 hybrid（短期保留 SOAR 端原 SPL 邏輯）

### 跟 case management 整合

Jira / ServiceNow / Elastic Cases：

- Splunk notable → Jira ticket 用 link field 帶 `splunk_url`
- Elastic alert → Jira 用 `elastic_url`
- 兩個 URL field 期間同時存在、Phase 5 後 archive

### 反向遷移（Elastic → Splunk）

結構 mirror 對稱、phase 仍 6 段、但 schema 對位方向相反：

- KQL → SPL 翻譯（vendor tool 對等度低、ES|QL → SPL 更困難）
- ECS → CIM 對位
- 多數企業 *不會* 反向遷、reverse migration 多半是合規驅動（特定客戶要 Splunk）

### 下一步議題

- **Multi-vendor SIEM portfolio**：不選一家、Splunk + Elastic + Sentinel 同時跑、routing 邏輯按 cost / use case 切
- **AI-native detection**：兩家都在發展、translation 流程可能再次重來
- **Compliance migration constraints**：金融 / 政府客戶 SIEM migration 需通過 audit、phase 時間表會被拉長

## 相關連結

- Source vendor：[Splunk](/backend/07-security-data-protection/vendors/splunk/)
- Target vendor：[Elastic Security](/backend/07-security-data-protection/vendors/elastic-security/)
- 上游 chapter：[7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)
- 平行 deep article：[Splunk RBA](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
