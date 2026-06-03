---
title: "從 MongoDB / Cassandra 遷入 Cosmos DB：protocol-compat API drop-in vs native API paradigm shift、相容性邊界與 dual-write cutover"
date: 2026-06-02
description: "MongoDB / Cassandra 遷入 Azure Cosmos DB 的 migration playbook：用 Cosmos 的 MongoDB API / Cassandra API 做 wire-protocol drop-in（Type B）vs 換 native SQL API 的 paradigm shift（Type E）兩條路徑的取捨、6 維 diff audit、相容性邊界、dual-write 與 cutover — 從 Microsoft 365 / Forbes 遷移對照切入"
weight: 73
tags: ["backend", "database", "cosmosdb", "migration", "mongodb", "cassandra", "deep-article"]
---

本文是 [Cosmos DB](/backend/01-database/vendors/cosmosdb/) overview 的 migration playbook、寫作參照 [Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)。從 MongoDB 或 Cassandra 遷入 Cosmos DB 的核心決策是 *選哪條路徑* — 用 Cosmos 的 protocol-compat API（MongoDB API / Cassandra API）做 wire-protocol drop-in、driver 與 query 大致不動；還是換 native SQL API、把 application 重寫成 Cosmos native paradigm。這兩條路的 diff 維度、風險、不可逆性都不同、是一個 multi-element 的 migration 規劃。本文先把 driver 與 no-go 講清楚、再做 6 維 diff audit 分出兩條路徑、再進各自的 phase plan、evidence 與 cutover。

API *選擇判斷* 本身（MongoDB API vs SQL API 的四層 framing、dogfood signal、multi-model、跨雲 hedging）由 [mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/) 主寫、本文不重複展開那層對比；本文主寫 *遷移流程* — 選定路徑後怎麼安全把資料與流量搬過去。

Case anchor：[9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（MongoDB → Cosmos DB MongoDB API、planet-scale、dogfood）、[9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自管 → Atlas、6 個月、同 DB 換託管的時程對照）、[9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（保留 MongoDB 補周邊、對照「不一定要遷」）。Microsoft 365 case 自承沒揭露 throughput / latency / cost 數字、本文不拿它當 benchmark、只取遷移路徑 frame。

## Driver：為什麼遷、什麼條件不遷

有效的遷移 driver 不是「Cosmos DB 比較好」、而是具體壓力：team 已綁 Azure 生態、需要 turnkey global distribution、自管 MongoDB / Cassandra cluster 的 ops 負擔要轉移、或需要 multi-model 把多個 NoSQL 集中治理。Microsoft 365 的 driver 是 planet-scale 全球分散 + Azure dogfood、不是 query 性能。

No-go condition（這些情況不該遷入 Cosmos DB）：

- 跨雲是核心需求 — Cosmos DB 只在 Azure；跨雲彈性高於 Azure 整合時、MongoDB 留 [Atlas](/backend/01-database/vendors/mongodb/)（Forbes 路徑、跨 AWS / GCP / Azure）、Cassandra 留自管或 ScyllaDB。
- 需要 native MongoDB / Cassandra 最新 feature — Cosmos DB 的 protocol-compat API server version 落後原生、且部分 feature 行為不同。
- 未來雲商策略未定 — hedging 價值高於當下整合、見 [vendor lock-in](/backend/knowledge-cards/vendor-lock-in/) 的退出成本。
- 現有 cluster 補周邊就夠用 — Coinbase 保留 MongoDB 加 proxy / cache / predictive scaling、沒遷出。遷移成本高、先確認「補周邊」解不了問題再遷。

## Diff audit：6 維度分出兩條路徑

source（MongoDB / Cassandra）與 target（Cosmos DB）的差異按 6 維度盤點、兩條路徑的維度高低不同、這也是 type 判定的依據。

| 維度          | protocol-compat API（MongoDB / Cassandra API）       | native SQL API                              |
| ------------- | ---------------------------------------------------- | ------------------------------------------- |
| Schema        | Low — document / table shape 大致保留                | Medium — 重新建模成 Cosmos native document  |
| Operational   | High — 自管 cluster → managed RU/s + region          | High — 同左                                 |
| Paradigm      | Low — 仍 document / wide-column 語意                 | High — 換 query 模型、index policy、RU 思維 |
| Components    | Medium — driver 保留、aggregation / CQL 部分要改     | High — driver、query layer、ORM 全換        |
| Application   | Medium — connection string、auth、consistency 對應   | High — 整個 data access layer 重寫          |
| Data topology | High — replica set / ring → partition + multi-region | High — 同左                                 |

主導差異決定 type：

- protocol-compat 路徑 — 最大差異是 operational 與 data topology、paradigm 維持 Low、是 wire-compat 的 drop-in 但有相容 gap。對應 **Type B drop-in（partial）**：driver 不換、但每個 query pattern 要驗證相容性、不是無腦切換。
- native API 路徑 — paradigm High + application High、是 **Type E paradigm shift**：不只搬資料、要重寫 application 的整個 data access layer。

判讀句：protocol-compat 是「換底層儲存與運維、保留 query 介面」、native API 是「連 query 範式一起換」。多數遷移先走 protocol-compat 把資料與 ops 搬過去、native API 是後續若要拿完整 Cosmos feature（Change Feed、stored procedure 原生支援、SQL API query）才考慮的二次遷移 — 一次到位 native API 的工程複雜度與風險顯著更高。

### Cassandra 路徑的專屬差異

Cassandra → Cosmos DB Cassandra API 跟 MongoDB 路徑有一個關鍵不同：Cassandra 的資料建模是 *query-driven*（partition key + clustering key 對應 access pattern）、這套建模思維跟 Cosmos DB 的 logical partition 概念部分對齊、但 Cosmos DB 的 per-partition RU 上限（目前約 10,000 RU/s、vendor 規格、實作時 cross-verify Azure doc 當前值）與 RU 計費會讓原本 Cassandra 上「寬 partition + 大量 clustering row」的設計變成 hot partition 風險。CQL 的 consistency level（QUORUM / LOCAL_ONE 等）要對應到 Cosmos DB 的 5 個 consistency level、語義不是一對一、見 [consistency-levels-engineering](../consistency-levels-engineering/)。Cassandra 的 secondary index / materialized view 在 Cassandra API 的支援度要逐項驗證（時間敏感、查文件）。

## Phase plan

兩條路徑共用大架構、protocol-compat 的相容 audit 較輕、native API 多一段 application 重寫。

### protocol-compat 路徑（Type B drop-in）

- Phase 0：相容性 audit — 把 production query / aggregation pipeline（MongoDB）或 CQL statement（Cassandra）拉出來、逐條對照 Cosmos DB 對應 API 的 [feature support](https://learn.microsoft.com/azure/cosmos-db/mongodb/feature-support-60) 清單、列出 unsupported 與行為不同的部分。
- Phase 1：partition key 設計 — MongoDB shard key / Cassandra partition key 翻譯成 Cosmos logical partition key、檢查 10,000 RU/s 上限與 hot partition 風險、見 [partition-key-design](../partition-key-design/)。
- Phase 2：bulk export-import — 初始資料用 Data Migration Tool / mongodump / sstable export 灌入。
- Phase 3：CDC sync — source 的持續變更（MongoDB oplog / Cassandra CDC）同步到 Cosmos DB、收斂初始 load 後的增量。
- Phase 4：shadow read — production query 在兩邊各跑一遍、對 result checksum、量 Cosmos 端 RU baseline、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)。
- Phase 5：read cutover — 讀切 Cosmos、寫仍 source（可回退）。
- Phase 6：write cutover — 寫切 Cosmos。
- Phase 7：cleanup — 退役 source cluster、保留 export 與最終 checksum。

### native API 路徑（Type E paradigm shift）多出的工作

native API 路徑在 Phase 0 與 Phase 1 之間插入 *application 重寫 stream*、與資料遷移 stream 並行：

- 重新建模 document（從 MongoDB document / Cassandra table 設計 Cosmos native shape、決定 embed vs reference）
- 重寫 data access layer（換掉 MongoDB driver / CQL、改用 Cosmos SQL API SDK、重寫所有 query）
- 重寫 aggregation（Cosmos SQL API 沒有 JOIN、aggregation 模型不同、部分邏輯移到 application 或用 stored procedure / Change Feed 物化）

這條 application stream 是 native API 路徑的主要風險與工期來源、必須跟資料遷移 stream 用獨立 owner 並行、shadow read 階段要對 *重寫後的 query* 與 *原 query* 的結果一致性、不只是資料一致性。

### 時程現實

Forbes 同 DB 換託管（自管 → Atlas、paradigm 不變）用 6 個月、中型團隊多 squad 並行。protocol-compat 遷入 Cosmos DB 的工程複雜度高於 Forbes 型（多了 RU / partition / region 範式與相容 gap）、native API 路徑再高一個量級（加 application 重寫）。拿 Forbes 6 個月當 native API 路徑 baseline 會從第一天 over-commit。

## Evidence

每個 phase 用資料證明可前進、不靠感覺：

- Phase 0：unsupported feature 清單已窮舉、每條有對應策略（改寫 / 移 application 層 / 接受降級）
- Phase 2-3：row / document count 對齊、CDC replication lag 收斂到穩定
- Phase 4：query result checksum 一致（protocol-compat 比原 query 結果；native API 比重寫 query 與原 query 結果）、RU baseline 量到、aggregation result 逐條對齊
- Phase 5-6：error rate、p99 latency、RU consumption 在 cutover 後在預期範圍
- 對應 [schema-migration-rollout-evidence](/backend/01-database/schema-migration-rollout-evidence/) 的 dual-write 驗證

## Cutover

- read cutover window：先切讀、寫留 source、Cosmos 端 read error rate 與 latency 達標再進 write cutover
- write cutover window：read-only freeze < 10 分鐘、切寫、最終 checksum 對齊
- Rollback condition：query error rate 超過閾值（如 > 1%）、RU consumption 顯著高於估算（protocol-compat 翻譯層 overhead 比預期高）、或 result mismatch — 任一成立回退到 source、對應 [rollback condition](/backend/knowledge-cards/rollback-condition/)
- decision owner：cutover 期間誰有權回退要事前定、資料庫切流失敗代價高、不靠臨場判斷
- 不可逆點：API kind 是 account 層、建 account 時選定、無法事後切換 — protocol-compat 與 native API 是 *兩個不同 account*；選 protocol-compat 後想升 native API 是 export → 新 account → import + 重寫 application 的二次全量遷移、不是 in-place 升級。這個不可逆性要在 Phase 0 就決定方向、不能 cutover 後反悔

## Cleanup

- 退役 source cluster 前確認最終 checksum、保留 export dump 90 天作為 rollback 後路
- 移除 dual-write writer、CDC connector、shadow read harness
- 保留 RU baseline 與 partition 分布觀測進 production dashboard、見 [ru-cost-model-sizing](../ru-cost-model-sizing/)
- incident write-back：把相容 gap 與翻譯層成本意外寫回 runbook、給未來同類遷移

## 失敗模式

### 假設 wire-compat = 100% 行為相同

protocol-compat API 是「在某些 query pattern 下相容」、不是普遍相容。MongoDB 的部分 aggregation stage（`$graphLookup` / `$facet` 等）、Cassandra 的部分 CQL feature 在對應 API 行為不同或不支援、dev 環境 sample data 看不出、production 才爆。修法是 Phase 0 把 *所有* production query 拉出來逐條驗證、Phase 4 shadow read 對 checksum、不能假設相容。

### shard key / partition key 直接照搬

MongoDB shard key 或 Cassandra partition key 直接當 Cosmos logical partition key、忽略 10,000 RU/s per partition 上限。原本 Cassandra 寬 partition 在 Cosmos 變 hot partition、throttle。修法是 Phase 1 按 Cosmos 的 partition 上限重新評估、必要時用 synthetic / composite key 強制分散、見 [partition-key-design](../partition-key-design/) 與 [Hot Partition](/backend/knowledge-cards/hot-partition/)。

### 把 native API 二次遷移當「升級」低估

選 protocol-compat 上線後、想拿 Change Feed / SQL query 等 native 能力、以為「升級到 SQL API」是改設定。實際是新 account + 全量資料遷 + application 重寫的第二次完整遷移。修法是 Phase 0 就決定終態方向 — 若終態確定要 native feature 且團隊能承擔重寫、直接走 native API 路徑、不要兩段遷。

### consistency level 對應錯

CQL 的 QUORUM / MongoDB 的 read concern majority 直接假設等價於 Cosmos 某個 level、語義不是一對一。修法是按 [consistency-levels-engineering](../consistency-levels-engineering/) 把 read-after-write 與順序需求逐場景對應、不照字面翻譯 consistency 名稱。

## 邊界與整合

- 主對比 SSoT：[mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/) — API *選擇判斷* 與三型遷移路徑分類在它主寫、本文主寫選定後的 *遷移流程*
- Sibling deep articles：[partition-key-design](../partition-key-design/)（shard / partition key 翻譯）、[ru-cost-model-sizing](../ru-cost-model-sizing/)（翻譯層 RU overhead 與 baseline）、[consistency-levels-engineering](../consistency-levels-engineering/)（read concern / CQL consistency 對應）、[change-feed-cdc](../change-feed-cdc/)（native API 才有原生 Change Feed、是 native 路徑的 feature driver 之一）
- 不遷的對照：[Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) 保留 MongoDB 補周邊 — 確認「補周邊」解不了再遷
- 跨雲對照：[Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) 留 Atlas 跨雲 — 跨雲需求是 Cosmos DB 的 no-go
- 共通遷移模型：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- Knowledge card：[vendor lock-in](/backend/knowledge-cards/vendor-lock-in/) / [Hot Partition](/backend/knowledge-cards/hot-partition/)
- 回 overview：[Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) 的「從 MongoDB / Cassandra 遷入」backlog

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾遷入 backlog 的深度展開
- [mongodb-api-vs-sql-api](../mongodb-api-vs-sql-api/) — API 選擇判斷與三型遷移路徑 SSoT
- [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API dogfood
- [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) — 同 DB 換託管時程對照
- [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — 保留 MongoDB 不遷的對照
- [partition-key-design](../partition-key-design/) / [ru-cost-model-sizing](../ru-cost-model-sizing/) / [consistency-levels-engineering](../consistency-levels-engineering/) — 遷移各 phase 的 sibling
- [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) — 跨 vendor 共通模型
- [Vendor Lock-in 卡片](/backend/knowledge-cards/vendor-lock-in/) — 跨雲 no-go 判讀
- 官方：[Migrate to Cosmos DB for MongoDB](https://learn.microsoft.com/azure/cosmos-db/mongodb/) / [Cosmos DB for Apache Cassandra](https://learn.microsoft.com/azure/cosmos-db/cassandra/)
