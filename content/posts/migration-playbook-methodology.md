---
title: "Migration Playbook 寫作方法論：5 種 type 對應 5 種結構、不是 universal phased"
date: 2026-05-19
description: "Migration playbook 跟 deep article 是不同 content category — 結構由 source/target 的最大差異維度決定、5 種 type（schema 差 / drop-in / operational / multi-tool / paradigm shift）對應 5 種不同結構模板；寫作前必須跑 diff dimension audit、選對結構再開寫；本文整理判讀流程、5 種 type anatomy、cadence dogfood findings 跟 deep article methodology 的邊界"
tags: ["writing-methodology", "migration-playbook", "cross-vendor", "technical-writing"]
---

Migration playbook 跟 [single feature deep article](/posts/vendor-deep-article-methodology/) 是 *不同 content category*。Deep article 處理「某 vendor 某 feature 怎麼實作 / 除錯」、是 *implementation flow*；migration playbook 處理「從 source vendor 怎麼移到 target vendor」、是 *process flow*。兩者目標、結構、寫作節奏都不同。本文整理 migration playbook 的方法論：5 種 type 結構模板、選 type 的 diff dimension audit、寫作流程、cadence 紀律。

本文背景：第三輪 deep article batch 寫了 5 篇跨 vendor migration playbook（Splunk → Elastic / Redis → DragonflyDB / PostgreSQL → Aurora / Datadog → Grafana Stack / Kafka ↔ NATS）、產出後發現 *5 篇結構完全不同*；嘗試套 deep article 6-section 跟自然形成的 6-phase 都 *只對 1 種 type 適用*。Migration playbook 需要自己的 methodology。

## 為什麼跟 deep article methodology 不同

寫了 10 篇 deep article + 5 篇 migration playbook 後對照：

| 維度                | Deep article                                           | Migration playbook                                            |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| 主題形狀            | Single feature（pgBouncer / Vault dynamic credential） | Cross-vendor process（Splunk → Elastic）                      |
| 結構                | 6-section（problem → concept → config → failure → capacity → integration）| 5 種不同 type、各對應不同結構             |
| 重點章節            | Step-by-step 配置 + 故障演練                            | 視 type 不同：phased flow / parallel streams / hybrid           |
| 行數                | 200-400 行                                              | 200-400 行（per article、type 內變異不大）                     |
| 寫作週期 / 篇       | 1-2 小時                                                | 2-3 小時（diff dimension audit + 結構選擇 + 寫作）             |
| 跨篇 cadence 風險   | 中（章節 1 entry 容易 collapse）                       | 高（migration 主題本質相似、natural attractor「為什麼遷」明顯）|
| 讀者                | 已選 vendor、要實作或除錯                              | 評估 / 執行 vendor 切換                                       |

關鍵差異：deep article 是 *single direction implementation*、migration playbook 是 *bidirectional comparison + process*。

## 5 種 migration type + 對應結構

從 5 篇 migration playbook batch 跑出來的分類：

### Type A：Phased translation（schema 差為主）

實證：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/)

特徵：source 跟 target 是 *同類產品* 但 *API / schema / data model 不相容*；application / SOC 端需要 *大量 translation work*。

結構：

```text
1. 為什麼遷（cost / multi-vendor / cloud-native driver）
2. 結構 differentiator（明示是 phased、不是 6-section）
3. Phase 0 audit（盤點 source 端內容、量化 baseline）
4. Phase 1 schema 對位（source ↔ target 規格表）
5. Phase 2 translation（vendor tool + AI-assisted + manual 三 tier）
6. Phase 3 parallel run（dual-system + dedup 4-8 週）
7. Phase 4 cutover（routing 切換、可逆邊界）
8. Phase 5 cleanup（不可逆階段、不可過早）
9. Production 故障演練
10. Capacity / cost 對照
11. 整合 / 下一步
```

11-12 章節、200-300 行、整體週期 4-9 個月。

### Type B：6-section + audit prefix（drop-in compatible）

實證：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)

特徵：source 跟 target *protocol 完全相容*、application code 不改；migration 是 *operational cutover* 不是 *content translation*。

結構：

```text
1. 為什麼遷
2. 結構 differentiator（明示 drop-in、跟 phased 對照）
3. 相容性 audit（在 cutover 前列出風險點）
4. Step-by-step cutover（BGSAVE → load → dual-write → traffic shift）
5. Production 故障演練
6. Capacity / cost 對照
7. 整合 / 下一步
```

接近 deep article 6-section + 多一段 *相容性 audit*；7-8 章節、200 行、整體週期 1-4 週。

### Type C：Operational redesign hybrid

實證：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)

特徵：source 跟 target *protocol 相容、application 不改*、但 *operational model 完全不同*（HA / backup / monitoring / capacity 全換）。

結構：

```text
1. 為什麼遷
2. 結構 differentiator（明示混合）
3. Operational redesign 對位（HA / backup / config / extension 表）
4. Phase 0 audit（extension / config 相容性）
5. Phase 1 operational infrastructure 準備
6. Phase 2 data migration（DMS / logical replication 兩條路）
7. Phase 3 cutover 跟 verification
8. Production 故障演練
9. Capacity / cost 對照
10. 整合 / 下一步
```

11-12 章節、240-280 行、整體週期 6-12 週。

### Type D：Parallel streams（multi-tool 拆分）

實證：[Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/)

特徵：source 是 *一站式 SaaS*、target 是 *N 個專責 component*；每個 component 獨立 migration、stream 間 *少 dependency*。

結構：

```text
1. Cost reality check（拆 source 帳單到具體 component 計費項）
2. N 個責任、N 個 component（source 一站式 vs target multi-tool 對位）
3. Migration 結構：parallel streams（每 stream 各自 phased、整體 staggered）
4. Agent migration（unified agent → 多 specialized agent）
5. Production 故障演練
6. Capacity / cost 對照
7. 整合 / 下一步
```

10-11 章節、220-250 行、整體週期 2-4 個月。

### Type E：Partial + 混合架構（paradigm shift）

實證：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)

特徵：source 跟 target *不是同類產品*（不同抽象層 / paradigm）；「migration」字面不成立、是 *按 use case 拆分 + 共存*。

結構：

```text
1. 「字面 migration 不成立」（paradigm contrast 開頭）
2. 什麼情境真的能換、什麼不能（適配度表）
3. 為什麼會考慮這個 paradigm shift
4. Migration 結構：application 重設計 + 部分 stream cutover + 長期混合
5. Application 重設計範例（pattern 翻譯）
6. Production 故障演練
7. Capacity / cost 對照
8. 整合 / 下一步（含「混合架構是 long-term default」）
```

10-11 章節、220-250 行、不收斂（永遠混合）。

## 寫前的 diff dimension audit

寫 migration playbook 前先跑：

```text
Step 1: 列 5 維度
  - Schema / API
  - Operational model
  - Abstraction / paradigm
  - Number of components (1 vs N)
  - Application change

Step 2: 對每維度評 High / Medium / Low

Step 3: 找最大差異維度

Step 4: 對映 type
  - Schema = High           → Type A
  - 全 Low                  → Type B
  - Operational = High      → Type C
  - Components = High       → Type D
  - Paradigm = High         → Type E
```

Audit 結果決定結構、不是反向。跳過 audit 直接套既有模板會在 phase 變空白 / process 強行線性的場景失真。詳細失效機制見 [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)。

## Cadence dogfood findings：被動寫作會 collapse

5 篇 migration playbook 寫作期間發現 *natural cadence attractor*：

| 篇 | Variant 規劃 | 章節 1 entry framing                          |
| --- | ----------- | -------------------------------------------- |
| 1 Splunk → Elastic     | 被動 | 「為什麼遷：cost / multi-vendor / cloud-native」|
| 2 Redis → DragonflyDB  | 被動 | 「為什麼遷：cost / single-thread / multi-tenancy」|
| 3 Postgres → Aurora    | 被動 | 「為什麼遷：operational cost / HA / DR」     |
| 4 Datadog → Grafana    | 主動 | 「$50K/month bill 拆解」                     |
| 5 Kafka ↔ NATS         | 主動 | 「『Kafka → NATS migration』字面上不成立」    |

3/5 collapse — natural attractor「為什麼遷：X / Y / Z driver」在前 3 篇 *被動寫作* 下浮現。寫第 4 篇前發現問題、後 2 篇 *主動換 entry variant*。

對照前批 deep article batch（N=4 / N=5 各全錯開、collapse 0%）、migration playbook 的 *主題語意 attractor* 比 deep article 更強。寫 migration playbook 必須：

1. **Stage 0 預先列 5 種 entry framing variant**（cost / paradigm / operational / case-led / driver list）
2. **每篇對應一種 variant、不重複**（或重複時刻意換 framing 的 *角度*）
3. **第 5 篇前抽 batch audit**（不是進度 80% 抽樣、是 *確認 entry framing 跟 stage 0 規劃對齊*）

對應 [case-first-module-workflow skill](/posts/case-first-agent-team-review-workflow/) 的 cadence-sampling principle — 主題語意 attractor 是 cadence collapse 的新失效源、被動 stage-internal checkpoint 不夠、必須 *stage 0 變體規劃*。

## 寫作流程（vs deep article methodology）

| Step | Deep article             | Migration playbook                                        |
| ---- | ------------------------ | --------------------------------------------------------- |
| 1    | 選題 + 經驗驗證          | 選題 + **diff dimension audit**                            |
| 2    | 草稿 outline + 真實 config | 對映 type A-E、用對應結構模板                              |
| 3    | 補敘事                   | 補敘事 + **結構 differentiator 段**                       |
| 4    | 故障演練段是核心          | 故障演練段是核心（不變）                                  |
| 5    | Cross-link 回 overview   | Cross-link 回 *source + target* 兩個 vendor               |
| 6    | 單一 reviewer 即可        | 單一 reviewer + **跨篇 entry framing audit**              |
| 7    | 取捨「廣度 vs 深度」      | 取捨「phased vs hybrid」（依 type）                       |

## 何時不該套這個方法論

- **Pure vendor doc 翻譯**：寫在 vendor docs / posts、不寫 migration playbook
- **Major version upgrade**（PostgreSQL 14 → 17）：同 vendor 內升級、用 deep article methodology（focus on upgrade-specific feature / 廠商 release note）
- **臨時 PoC / spike**：不需要完整 phased / hybrid playbook、簡短決策文件即可
- **Compliance-driven 強制 migration**：法規導向、playbook 重點在 *合規 evidence collection*、跟 5 種 type 不同框架

## Backlog（下一輪可寫的 migration playbook）

候選 + 預判 type：

| Source → Target                          | 預判 type | 預估行數 |
| ---------------------------------------- | --------- | -------- |
| MongoDB self-managed → MongoDB Atlas     | Type C    | ~250     |
| Self-managed Kafka → MSK / Confluent     | Type C    | ~240     |
| MySQL → PostgreSQL                       | Type A    | ~300     |
| ELK self-managed → Elastic Cloud         | Type C    | ~220     |
| Jenkins → GitHub Actions / GitLab CI     | Type A/D 混合 | ~280  |
| New Relic → Datadog                      | Type B/D 混合 | ~220  |
| Redis → Memcached                        | Type E    | ~200     |
| etcd → Consul                            | Type E    | ~220     |
| Vault → AWS Secrets Manager              | Type C/E 混合 | ~250  |
| Terraform → OpenTofu                     | Type B    | ~180     |

第二輪選 3-5 篇、跑 stage 0 variant 規劃 + 寫作。

## 跟其他 methodology / skill 的關係

- [Deep article methodology](/posts/vendor-deep-article-methodology/)：sibling、處理 single feature implementation
- [Case-first Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/)：兩者都是寫作流程、case-first 適合 *broad coverage* vendor overview batch、本方法論適合 *cross-vendor process*
- [Compositional Writing skill](/skills/compositional-writing/)：寫作的 atomic 原則、本方法論的章節層級設計

## 相關連結

- 5 篇 dogfood demo：[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) / [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) / [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- 對應 report 卡：[#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/) / [#122 Cadence 同質化是模板的隱形維度](/report/cadence-homogenization-in-batch-writing/) / [#124 Emergence-class 違規規則化不了](/report/emergence-violations-need-in-stream-sampling/)
- 對位 methodology：[Vendor deep article methodology](/posts/vendor-deep-article-methodology/)
