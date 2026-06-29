---
title: "Migration Playbook 寫作方法論：6 種 type 對應 6 種結構、不是 universal phased"
date: 2026-05-19
description: "跨 vendor migration playbook 的結構選型：diff dimension audit 判斷差異維度、再選對應結構模板。與 deep article 的 content category 邊界。"
tags: ["writing-methodology", "migration-playbook", "cross-vendor", "technical-writing"]
---

Migration playbook 跟 [single feature deep article](/posts/vendor-deep-article-methodology/) 是 *不同 content category*。Deep article 處理「某 vendor 某 feature 怎麼實作 / 除錯」、是 *implementation flow*；migration playbook 處理「從 source vendor 怎麼移到 target vendor」、是 *process flow*。兩者目標、結構、寫作節奏都不同。本文整理 migration playbook 的方法論：6 種 type 結構模板（含後加的 Type F topology re-layout）、選 type 的 6 維 diff dimension audit、寫作流程、cadence 紀律。

本文背景：第三輪 deep article batch 寫了 5 篇跨 vendor migration playbook（Splunk → Elastic / Redis → DragonflyDB / PostgreSQL → Aurora / Datadog → Grafana Stack / Kafka ↔ NATS）、產出後發現 *5 篇結構完全不同*；嘗試套 deep article 6-section 跟自然形成的 6-phase 都 *只對 1 種 type 適用*。Migration playbook 需要自己的 methodology。

## 為什麼跟 deep article methodology 不同

寫了 10 篇 deep article + 5 篇 migration playbook 後對照：

| 維度              | Deep article                                                               | Migration playbook                                               |
| ----------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 主題形狀          | Single feature（pgBouncer / Vault dynamic credential）                     | Cross-vendor process（Splunk → Elastic）                         |
| 結構              | 6-section（problem → concept → config → failure → capacity → integration） | 6 種不同 type、各對應不同結構                                    |
| 重點章節          | Step-by-step 配置 + 故障演練                                               | 視 type 不同：phased flow / parallel streams / hybrid            |
| 行數              | 200-400 行                                                                 | 200-400 行（per article、type 內變異不大）                       |
| 寫作週期 / 篇     | 1-2 小時                                                                   | 2-3 小時（diff dimension audit + 結構選擇 + 寫作）               |
| 跨篇 cadence 風險 | 中（章節 1 entry 容易 collapse）                                           | 高（migration 主題本質相似、主題語意 attractor「為什麼遷」明顯） |
| 讀者              | 已選 vendor、要實作或除錯                                                  | 評估 / 執行 vendor 切換                                          |

關鍵差異：deep article 是 *single direction implementation*、migration playbook 是 *bidirectional comparison + process*。

## 6 種 migration type + 對應結構

從第一輪 5 篇 migration playbook batch 跑出 Type A-E、第二輪 Redis cluster re-sharding dogfood 浮現 Type F（topology re-layout）：

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

### Type F：Topology re-layout（data topology 為主）

實證：[Redis cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)

特徵：source / target 多數是 *同 cluster 不同 state*、不是跨 vendor；資料分佈 *sharding / partition / replication / region / co-location 拓樸* 變動、但 schema / operational / paradigm 不變。

結構：

```text
1. 為什麼 re-layout（4-N 種 driver）
2. 結構 differentiator（re-layout 不是 migration）
3. Pre-layout analysis（current topology audit / hot key / slot 分佈）
4. Re-layout 機制（slot migration / partition split / shard rebalance）
5. Execution flow（per-step、含 rollback boundary）
6. Production 故障演練
7. Capacity / cost
8. 整合 / 下一步
```

7-9 章節、200-260 行、整體週期 1 天-2 週（依 cluster 大小）。

詳細 audit dimension 跟 sub-dimension（sharding / partition / replication / region / co-location 5 sub-dimension）見 [#128 Data topology 是 process content 的第 6 audit 維度](/report/data-topology-as-audit-dimension/)。

## 寫前的 diff dimension audit

寫 migration playbook 前先跑：

```text
Step 1: 列 6 維度
  - Schema / API
  - Operational model
  - Abstraction / paradigm
  - Number of components (1 vs N)
  - Application change
  - Data topology（sharding / partition / replication / region / co-location 拓樸）

Step 2: 對每維度評 High / Medium / Low

Step 3: 找主導差異維度（不是「最大」、是「讀者最關心」）

Step 4: 對映常見 type
  - Schema = High（其他 Low）       → Type A
  - 全 Low / 全 Medium               → Type B
  - Operational = High（其他 Low）   → Type C
  - Components = High               → Type D
  - Paradigm = High                 → Type E
  - Topology = High（其他 Low）      → Type F

Step 5: 處理多重歸類（多軸 High）
  - 主結構選讀者最關心的維度（多數情境 Schema > Paradigm > Operational > Topology > Components）
  - 其他高維度抽出獨立段補充、不強迫單一 type 標籤
  - 詳細規則見 #127「多重歸類跟 tie-breaking」段

Step 6: 確認不在已知漏類內
  - 同 vendor major version upgrade / 政策合規驅動 / acquisition consolidation 不適用 5 type
  - 容量重劃 / re-sharding 場景已被 Type F 涵蓋（topology 軸 High）
  - 漏類處理見「何時不該套這個方法論」段
```

Audit 結果決定主結構、不是反向。跳過 audit 直接套既有模板會在 phase 變空白 / process 強行線性的場景失真。詳細失效機制 + 漏類列表見 [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)；data topology 維度跟 Type F 詳細 anatomy 見 [#128](/report/data-topology-as-audit-dimension/)。

## Cadence dogfood findings：被動寫作會 collapse

5 篇 migration playbook 寫作期間發現 *主題語意 attractor*（atomic 定義見 [#122 cadence 同質化](/report/cadence-homogenization-in-batch-writing/) Update 段、是 [#123 constraint collapse](/report/compliance-optimum-converges-cadence/) 的內容驅動子類型）：

| 篇                    | Variant 規劃 | 章節 1 entry framing                               |
| --------------------- | ------------ | -------------------------------------------------- |
| 1 Splunk → Elastic    | 被動         | 「為什麼遷：cost / multi-vendor / cloud-native」   |
| 2 Redis → DragonflyDB | 被動         | 「為什麼遷：cost / single-thread / multi-tenancy」 |
| 3 Postgres → Aurora   | 被動         | 「為什麼遷：operational cost / HA / DR」           |
| 4 Datadog → Grafana   | 主動         | 「$50K/month bill 拆解」                           |
| 5 Kafka ↔ NATS        | 主動         | 「『Kafka → NATS migration』字面上不成立」         |

3/5 collapse — 主題語意 attractor「為什麼遷：X / Y / Z driver」在前 3 篇 *被動寫作* 下浮現。寫第 4 篇前發現問題、後 2 篇 *主動換 entry variant*。

對照前批 deep article batch（N=4 / N=5 各全錯開、collapse 0%）、migration playbook 的 *主題語意 attractor* 比 deep article 更強。寫 migration playbook 必須：

1. **Stage 0 預先列 5 種 entry framing variant**（cost / paradigm / operational / case-led / driver list）
2. **每篇對應一種 variant、不重複**（或重複時刻意換 framing 的 *角度*）
3. **第 5 篇前抽 batch audit**（不是進度 80% 抽樣、是 *確認 entry framing 跟 stage 0 規劃對齊*）

對應 [case-first-module-workflow skill](/posts/case-first-agent-team-review-workflow/) 的 cadence-sampling principle — 主題語意 attractor 是 cadence collapse 的新失效源、被動 stage-internal checkpoint 不夠、必須 *stage 0 變體規劃*。

## 寫作流程（vs deep article methodology）

| Step | Deep article               | Migration playbook                           |
| ---- | -------------------------- | -------------------------------------------- |
| 1    | 選題 + 經驗驗證            | 選題 + **diff dimension audit**              |
| 2    | 草稿 outline + 真實 config | 對映 type A-E、用對應結構模板                |
| 3    | 補敘事                     | 補敘事 + **結構 differentiator 段**          |
| 4    | 故障演練段是核心           | 故障演練段是核心（不變）                     |
| 5    | Cross-link 回 overview     | Cross-link 回 *source + target* 兩個 vendor  |
| 6    | 單一 reviewer 即可         | 單一 reviewer + **跨篇 entry framing audit** |
| 7    | 取捨「廣度 vs 深度」       | 取捨「phased vs hybrid」（依 type）          |

## 何時不該套這個方法論（5 type + audit 不適用）

5 type 框架 + diff dimension audit 主要對應 *跨 vendor process*。以下情境 *不適用 5 type 框架*、需要其他方法論：

- **Pure vendor doc 翻譯**：寫在 vendor docs / posts、不寫 migration playbook
- **同 vendor major version upgrade**（PostgreSQL 14 → 17 / Kafka 3 → 4）：source / target 同 vendor、5 type 預設跨 vendor；同 version upgrade 重點在 *upgrade-specific feature* + *release note + 相容性 audit*、結構接近 deep article methodology 的 6-section + 額外 upgrade audit 段、不是 phased migration
- **臨時 PoC / spike**：不需要完整 phased / hybrid playbook、簡短決策文件即可
- **容量重新規劃 / re-sharding**（單實例 → sharded、單 region → multi-region）：~~source / target 同 vendor、無 schema 差、是 *data topology 重劃*、5 維度沒 topology 軸~~ 第二輪 dogfood 後 audit 已擴 6 維、補上 *data topology* 維度、re-sharding 對映 **Type F topology re-layout**、不在「不該套」內；詳見 [#128 Data topology 是 process content 的第 6 audit 維度](/report/data-topology-as-audit-dimension/)
- **Acquisition / merger consolidation**（兩 org 合併 / cluster federate）：source / target 同產品、主要工作在 identity / RBAC / 歷史資料合併、不是結構轉換

注意 *politics-driven / compliance-driven migration* **不在排除範圍** — 法規驅動只是 *driver*、資料層仍走 type A-E 之一；playbook 主結構走對應 type、額外加 *合規 evidence collection* 段、不是另起爐灶。

## Backlog（下一輪可寫的 migration playbook）

候選 + 預判 type：

| Source → Target                      | 預判 type     | 預估行數 |                             |
| ------------------------------------ | ------------- | -------- | --------------------------- |
| MongoDB self-managed → MongoDB Atlas | Type C        | ~250     | **完成 2026-05-19、349 行** |
| Self-managed Kafka → MSK / Confluent | Type C        | ~240     |                             |
| MySQL → PostgreSQL                   | Type A        | ~300     | **完成 2026-05-19、263 行** |
| ELK self-managed → Elastic Cloud     | Type C        | ~220     |                             |
| Jenkins → GitHub Actions / GitLab CI | Type A        | ~280     |                             |
| New Relic → Datadog                  | Type A        | ~220     |                             |
| Redis → Memcached                    | Type E        | ~200     |                             |
| etcd → Consul                        | Type E        | ~220     |                             |
| Vault → AWS Secrets Manager          | Type C/E 混合 | ~250     |                             |
| Terraform → OpenTofu                 | Type B        | ~180     |                             |

第二輪選 3-5 篇、跑 stage 0 variant 規劃 + 寫作。

### 第二輪 batch 完成 (2026-05-19)

實際寫了 5 篇、包含 2 篇 backlog 標的（MongoDB → Atlas、MySQL → PostgreSQL）+ 3 篇驗證 self-aware limitation：

- [PostgreSQL major version upgrade (14 → 17)](/backend/01-database/vendors/postgresql/major-version-upgrade/) — 漏類驗證（同 vendor）、結構走 deep article + upgrade audit、不是 5 type
- [Redis cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/) — 漏類驗證（topology 重劃）、新結構 anatomy 浮現
- [PostgreSQL → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/) — 三維 High multi-axis 驗證、Type E 主結構 + Type A/C 高維度獨立段
- [MySQL → PostgreSQL](/backend/01-database/vendors/mysql/migrate-to-postgresql/) — Type A 標準形態 (263 行)
- [MongoDB → Atlas](/backend/01-database/vendors/mongodb/migrate-to-atlas/) — Type C 標準形態 (349 行)

5 篇 1,389 行、entry framing 全 5 種錯開、collapse 0/5（vs 第一輪 3/5）。

### 第三輪 batch 完成 (2026-05-19、Type F dogfood + 3 軸候選驗證)

第三輪驗證 #128 self-aware limitation 4 條 tripwire、5 篇 1,292 行、entry framing 全 5 種錯開、collapse 0/5：

- [PostgreSQL partition redesign](/backend/01-database/vendors/postgresql/partition-redesign/) (246 行) — Type F dogfood #2、anatomy 通用性驗證
- [MongoDB shard + multi-DC expansion](/backend/01-database/vendors/mongodb/shard-expansion-multi-dc/) (288 行) — Type F dogfood #3 + parallel run 例外實證
- [Vault → AWS Secrets Manager](/backend/07-security-data-protection/vendors/hashicorp-vault/migrate-to-aws-secrets-manager/) (271 行) — Identity axis 候選驗證（45% 工作量）
- [DynamoDB consistency model optimization](/backend/01-database/vendors/dynamodb/consistency-model-optimization/) (249 行) — Consistency axis 候選驗證（85% 工作量）
- [PostgreSQL multi-region GDPR rollout](/backend/01-database/vendors/postgresql/multi-region-gdpr-rollout/) (238 行) — Residency axis 候選驗證（40% 工作量）

第三輪累積 evidence：

- **Type F sub-type 浮現**：F-cluster（單 cluster 內、不需 parallel run）vs F-multi-region（跨 region、需 parallel run）；anatomy 在 sub-type 之間有差異
- **3 軸候選確認可獨立**：identity / consistency / residency 各帶 30-85% 獨立工作量；累積到 3-5 case / 軸後考慮升 audit 7-9 維
- **Residency 是 cross-cutting constraint**：不只是 driver、反向約束 topology + operational + application；可能需要 *constraint layer* 概念跟 axis 並列

## 跟其他 methodology / skill 的關係

- [Deep article methodology](/posts/vendor-deep-article-methodology/)：sibling、處理 single feature implementation
- [Case-first Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/)：兩者都是寫作流程、case-first 適合 *broad coverage* vendor overview batch、本方法論適合 *cross-vendor process*
- [Compositional Writing skill](/skills/compositional-writing/)：寫作的 atomic 原則、本方法論的章節層級設計

## Self-aware limitation

本 methodology 從 5 篇 migration playbook dogfood 抽出 5 type；對應 [#127](/report/content-structure-by-max-diff-dimension/) 的 self-aware limitation 段、本 methodology 也是 *current best understanding*、不是完備理論。已知 limitation：

- **5 type 非窮盡**：major version upgrade / 容量重劃 / merger consolidation 等情境不在 5 type 內、見「何時不該套」段
- **多重歸類常見**：實際 source/target 配對很少完美對映單一 type；audit Step 5 處理多軸 High 情境
- **「主導維度」需 judgment**：Schema > Paradigm > Operational > Topology > Components 的優先序是當前 heuristic、不是 universal 規則；且優先序本身是 audience-dependent（DBA 視角下 Topology 可能 > Operational、application developer 視角下 Schema > Paradigm）
- **Cadence dogfood 自身 3/5 collapse**：本批 5 篇前 3 篇被動寫作時自身浮現「為什麼遷 X/Y/Z driver」collapse、後 2 篇主動 variant 才錯開；證實 stage 0 variant 規劃是本 methodology 的 *硬需求*、不是 nice-to-have

第二輪 / 第三輪 batch 後可能需要：(1) 擴充 type 集合、(2) 主導維度優先序動態化、(3) audit 維度補新軸（如 data topology / identity model）。本 methodology 接受 evolution、不假裝穩定。

### Update（2026-05-19）：第二輪 batch 驗證結果

第二輪 5 篇驗證了 self-aware limitation 的 4 項預測 + 浮現 3 項新議題：

驗證成立：

- **5 type 漏類確認**：major version upgrade（同 vendor）+ re-sharding（topology 重劃）結構跟 5 type 完全不同、各有自己的 anatomy、不該強行歸類
- **多重歸類 + tie-breaking 規則成立**：PostgreSQL → CockroachDB 三維皆 High、按 Step 5「主導維度走 Type E + 高維度獨立段」執行、結構成立
- **Type A / Type C 標準形態仍適用**：MySQL → PostgreSQL（Type A）+ MongoDB → Atlas（Type C）走標準模板、跟第一輪同 type 對應
- **Stage 0 variant 規劃硬需求**：第二輪 5 篇全主動 variant、collapse 0/5（vs 第一輪 3 篇被動 collapse 3/5）— 確認 stage 0 不是 nice-to-have

浮現新議題：

- **新 audit 維度（data topology）**：re-sharding 揭露 5 維度沒「topology」軸；第三輪 batch 跑前評估是否要擴 6 維
- **「為什麼這篇不套」是漏類文章標準模板**：major-version-upgrade + cluster-resharding 都用這個 frame 開頭、明示跟 5 type 邊界；未來漏類文章可採用
- **「高維度獨立段」對照表升級**：multi-axis 文章自然會多出這個元素（cockroachdb 篇對照表 row 11）、應該升級為 multi-axis migration 的 standard structural element

## 相關連結

本 methodology 在三層 hierarchy 的位置：

| 層次          | 對應                                                                                                                                                   | 角色                                   |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------- |
| 具體 SOP 層   | 本 methodology + [Vendor deep article methodology](/posts/vendor-deep-article-methodology/)                                                            | 寫作流程 / 步驟 / 結構模板             |
| 抽象原則層    | [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)                                                        | 結構選擇規則、跨 content category 通用 |
| 症狀 / 機制層 | [#122 Cadence 同質化](/report/cadence-homogenization-in-batch-writing/) + [#124 Emergence 違規](/report/emergence-violations-need-in-stream-sampling/) | 寫作中的具體 failure mode              |

讀的順序：症狀層先讀體會風險、抽象層讀通用原則、SOP 層找具體執行步驟。寫作時反向：先做 SOP 步驟、若觸發症狀回溯到原則卡找根因。

- 5 篇 dogfood demo：[Splunk → Elastic](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) / [PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) / [Datadog → Grafana Stack](/backend/04-observability/vendors/datadog/migrate-to-grafana-stack/) / [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
