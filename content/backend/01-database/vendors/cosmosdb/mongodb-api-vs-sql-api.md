---
title: "Cosmos DB MongoDB API vs SQL API：遷移路徑、dogfood signal、multi-model、跨雲 hedging"
date: 2026-05-27
description: "從『MongoDB API 跟 SQL API 哪個快』推進到 vendor selection 的四層問題：三型遷移路徑、dogfood signal 怎麼讀、multi-model 差異化、跨雲 hedging — 從 Microsoft 365 dogfood 案例切入"
weight: 30
tags: ["backend", "database", "cosmosdb", "mongodb-api", "sql-api", "migration", "deep-article"]
---

Cosmos DB 提供 *5 個 API*（SQL / MongoDB / Cassandra / Gremlin / Table）、底層是同一個分散式 document store。團隊從 MongoDB 來、第一個問題通常是「MongoDB API 跟 native SQL API 我選哪個」 — 但這個問題框架太窄。讀者真正在比的是 *vendor selection*、不是兩個 API 的 syntax 差。本文把選型推到四層問題：(a) 你的遷移路徑屬於哪一型、(b) dogfood signal 怎麼讀、(c) multi-model 差異化是否真用上、(d) 跨雲 hedging 還是單雲 lock-in。先把四層 framing 講清楚、再進兩個 API 的機制差異、最後給 MongoDB → Cosmos DB MongoDB API 的 migration playbook。

本文不是 Cosmos DB overview（請看 [Cosmos DB vendor 頁](/backend/01-database/vendors/cosmosdb/)）— 而是 *選型決策 + 遷移實作* 的深度展開。Case anchor 是 [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — Microsoft 自家 dogfood、MongoDB → Cosmos DB MongoDB API 的 planet-scale 分析平台、提供四層 framing 的證據錨點。

## 問題情境：選型問題不是「兩個 API 哪個快」

典型觸發場景：團隊已用 MongoDB（自管 或 Atlas）、評估遷到 Azure；Cosmos DB 提供 MongoDB API（wire protocol 相容）跟 native SQL API 兩條路；文件講「MongoDB API 是 wire compat、SQL API 是 native」、但這個敘述沒回答真實決策問題。

讀者實際在問：

- 「MongoDB API 我們的 aggregation pipeline 跑得起來嗎」
- 「`$lookup` 在 Cosmos DB MongoDB API 支援嗎」
- 「change stream 跟 Change Feed 是同一回事嗎」
- 「為什麼有人說 MongoDB API 只是過渡、最終要遷 SQL API」
- 「Microsoft 自己選了 MongoDB API、是不是代表 MongoDB API 才是對的選擇」

這些問題背後的 *真實壓力* 是 vendor selection：團隊已選 Azure、要決定「留 Atlas 還是進 Cosmos DB、進了 Cosmos DB 用哪個 API」、選錯的成本是 *年級的工程遷移* — 不是 *config 改不改* 等級。Microsoft 365 案例（[9.C30](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)）從 MongoDB 遷到 Cosmos DB MongoDB API 是 dogfood、但 case 自承「沒有提具體 throughput、latency、cost 數字」— 引用時不能拿這個案例的「成功」當 benchmark、只能取它的 framing。

## 四層 framing：vendor selection 的真實決策軸

### Framing 1：document model 三型遷移路徑對照（本章合成 frame）

「MongoDB → Cosmos DB」是 *一種* 遷移、不是 *全部* 遷移。document model 的遷移路徑在 case 庫至少呈現三型、風險跟 ROI 完全不同：

| 遷移型             | 案例                                                                                                                                                   | 工程複雜度                        | ROI                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- | ------------------------------ |
| 保留 + 補周邊      | [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/)（mongobetween + freshness token + ML predictive scaling） | 低、漸進、保留 MongoDB 自管       | 中、解 connection storm 等瓶頸 |
| 同 DB 換託管       | [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/)（自管 → Atlas、6 個月）                             | 中、schema 跟 access pattern 保留 | 高、釋放 ops 人力              |
| 同 model 換 vendor | [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/)（MongoDB → Cosmos DB MongoDB API）                    | 高、底層架構換、driver 保留       | 高、planet-scale 擴展性        |

**三型 frame 是本章合成、case 原文沒有此分類**。引用時要明示：Forbes 6 個月遷移成功 *不代表* Microsoft 365 也是 6 個月、底層架構換的工程複雜度遠高於託管換。讀者開頭要先問「我屬於哪一型」、再進兩個 API 比較 — 「保留 + 補周邊」根本不需要進 Cosmos DB selection、「同 DB 換託管」的主要 trade-off 是 Atlas vs Cosmos DB 跨雲問題（Framing 4）、「同 model 換 vendor」才是本文聚焦的決策。

把三型混淆的後果是：拿 Forbes 6 個月時程當 baseline 估 Microsoft 365 型遷移、實際工程複雜度高 3-5 倍、project plan 從第一天就 over-commit。

### Framing 2：dogfood 是高權重 selection signal、但案例數字常不公開

Microsoft 365 案例揭露的核心 signal 是「Microsoft 自家旗艦產品 dogfood Cosmos DB」— 跟 Amazon Prime Day 用 DynamoDB、Google 自家用 Spanner 一樣、雲商旗艦 DB 都用在自家旗艦產品上、這個 signal 在 vendor selection 的權重高、因為「雲商自己賭身家」。讀者該把這當 *選型訊號*、不是當 *production benchmark*。

但 9.C30 case 自承的警示必須明示：

- 「沒有提具體 throughput、latency、cost 數字。Microsoft 內部數字通常不公開、跟 AWS / GCP 案例的數字密度差很多」
- 「『MongoDB 不夠用』是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*、不是普遍結論」

兩條警示直接影響寫作紀律：

- 不能拿「Microsoft 365 遷成功」當「我們也會成功」的證據 — 規模 / workload pattern / 團隊能力都不同
- 不能拿「Microsoft 從 MongoDB 遷出」當「MongoDB 不行」的結論 — Microsoft 自己也有大量 MongoDB / Cosmos DB / SQL Server 並用、不是全部遷出

dogfood signal 的 *正確用法* 是當 frame 借鑑（multi-model 差異化、planet-scale 抽象單位、API compatibility 層）、不是當數字 benchmark。

### Framing 3：multi-model 是 Cosmos DB 的差異化價值、不總是真用上

Cosmos DB 的差異化價值不是「比 Atlas 更會跑 MongoDB」、是 *單一服務支援 5 個 API*（SQL / MongoDB / Cassandra / Gremlin / Table）。跨雲對照揭露這個差異化的稀有度：

- AWS：DynamoDB（KV）+ DocumentDB（MongoDB-compatible）+ Neptune（graph）+ Keyspaces（Cassandra）— 各 use case 一個產品
- GCP：Firestore（document）+ Bigtable（KV）+ Spanner（SQL）— 各 use case 一個產品
- Azure Cosmos DB：5 個 API 在 *同一個服務* 內、partition + RU + region 治理共用

對 selection 的意義：若團隊預期同一系統會用 document + KV + graph 混合、Cosmos DB 的 multi-model 是 *運維單一服務* 的 unique value、不是只看「MongoDB 替代品」就能 ROI 評估。但 anti-pattern 也明確：*若團隊只用 MongoDB API、不會用其他 4 個 API*、multi-model 差異化價值對該團隊 *不成立*、不該變成 selection 理由。

判讀時要把 multi-model 當「條件性價值」、不是「普遍優勢」 — 條件是「現在或可預見未來會用到第二個 API」。9.C30 Microsoft 365 case 策略段直接揭露「Multi-model 是 Cosmos DB 的差異化價值」、但這個價值對「只用 MongoDB API」的團隊不成立、不能套到所有讀者。

### Framing 4：跨雲 hedging vs 單雲 lock-in 的 trade-off

選 Cosmos DB（單雲、Azure-only）跟選 MongoDB Atlas（跨雲、AWS / GCP / Azure 都能跑）的核心 trade-off 不是「哪個技術更強」、是 *未來不確定性的對沖價值* — 對應 [vendor lock-in](/backend/knowledge-cards/vendor-lock-in/) 的退出成本評估：

- Atlas：跨雲部署能力、未來換雲商不用換 DB、9.C37 Forbes 用 GCP 但保留跨雲彈性
- Cosmos DB / DynamoDB / Spanner：三大雲商各自的單雲 DB、選一個就綁該雲商生態

對 *未來雲商策略尚未底定* 的團隊、Atlas 的 hedging 價值 *高*、即使當下單雲就夠用 — 因為 5 年後換雲商的工程成本可能遠高於每月多付的 hosting 費用。對 *已綁 Azure 生態* 的團隊（Microsoft 365 dogfood、企業 AAD / Office / Power Platform 整合）、Cosmos DB 的 Azure-only 是 *整合延伸*、不是 *lock-in 損失* — 雲商已綁、再加一個 lock-in 不增邊際成本。

引用時必須明示這是 *未來不確定性 vs 當下整合* 的 hedging trade-off、不是「跨雲一定比較好」。讀者該問自己：「我們未來 5 年雲商策略是已定還是未定」、答案會直接決定 Atlas vs Cosmos DB 的選擇方向。

## 兩個 API 的機制差異

四層 framing 講完、再進 API 機制 — 不是為了「哪個快」、是為了讓 selection 後的實作不踩坑。

兩個 API 的關係：底層是同一個 Cosmos DB 分散式 document store、API layer 翻譯不同 wire protocol。MongoDB API 把 MongoDB 操作翻譯成 Cosmos DB internal、不是真的跑 MongoDB engine；SQL API 直接操作 Cosmos DB native query language。

**MongoDB API**：

- 相容 MongoDB wire protocol（時間敏感 claim、查 [最新支援版本](https://learn.microsoft.com/azure/cosmos-db/mongodb/feature-support-60)、目前對齊 6.0 / 7.0 但仍落後 native MongoDB）
- Driver 不變：直接用 mongo-go-driver / pymongo / mongoose
- 翻譯層有 overhead、相同 query 的 RU 通常比 SQL API 多 10-20%

**SQL API**：

- Cosmos DB native query language（SQL-like、不是標準 SQL、不支援 JOIN）
- 直接操作 JSON document、ARRAY / nested field native 支援
- 完整 Cosmos DB feature 支援（Change Feed、stored procedure、trigger）

**關鍵差異點**：

- `$lookup`（join）：MongoDB API 支援度有限、跨 partition 性能差；SQL API 沒 JOIN（document model 哲學）
- Aggregation pipeline：部分 stage 不支援或行為不同（時間敏感、查 [支援列表](https://learn.microsoft.com/azure/cosmos-db/mongodb/feature-support-60#aggregation-pipeline)）
- Index：MongoDB API hint / explain 行為跟 native MongoDB 不同
- Change stream：MongoDB API 提供 change stream wire compat、但底層是 Cosmos DB Change Feed（語義 / ordering / retention 有差）
- Transaction：兩邊都限同 partition、跨 partition transaction 都要改 workflow

API kind 是 *account 層設定*、*建 account 時選擇、無法事後切換*。MongoDB API → SQL API 的「升級」實際上是 export → recreate account → import + 重寫 application 的全量遷移、不是 in-place 切換。

## Migration playbook：MongoDB → Cosmos DB MongoDB API

「同 model 換 vendor」型遷移（Framing 1 第三型）的 6 規格面 audit：

### 規格面 1：Driver

- 主要 driver：Azure 生態整合、需要更好的 global distribution、Atlas 跨雲成本不必要（單雲團隊）
- 對應 Framing 4 的「已綁 Azure 生態」條件

### 規格面 2：No-go condition

- 跨雲需求（Framing 4、Atlas 仍是首選、Forbes 案例證據）
- 需要 native MongoDB latest feature（MongoDB API server version 落後 native MongoDB）
- 未來雲商策略未定（hedging 價值喪失）
- 純 MongoDB 投資、無 Azure 生態其他服務整合（Framing 3 multi-model 不成立）

### 規格面 3：Diff audit（6 維度）

- **Schema**：document shape 不變（wire compat）；但 `_id` 行為跟 Cosmos DB partition key 綁定方式要審
- **Operational**：自管 MongoDB → managed Cosmos DB、replica set / sharding 變成 partition + region、備份 / monitoring 全換
- **Paradigm**：不變（仍 document model）
- **Components**：MongoDB driver 保留、aggregation pipeline 部分需重寫
- **Application change**：connection string、authentication mechanism（SCRAM → Azure key / AAD）、read preference 對應 consistency level
- **Topology**：replica set → multi-region replication、shard key → partition key

遷移類型判定：**Type B drop-in（partial）**、wire compat 但有相容性 gap、必須 dual-write per query pattern 驗證、不是一次切換。

### 規格面 4：Phase plan

- Phase 0：相容性 audit、列 unsupported aggregation stage、production query corpus 對齊
- Phase 1：partition key 設計（從 shard key 翻譯）、見 [partition-key-design](../partition-key-design/)
- Phase 2：bulk export-import（mongodump → Cosmos DB Data Migration Tool）
- Phase 3：CDC sync（MongoDB oplog → Azure Data Factory / 自寫 connector）
- Phase 4：shadow read 驗證 query 一致性、量 RU consumption baseline
- Phase 5：read cutover（讀切 Cosmos、寫仍 MongoDB）
- Phase 6：write cutover
- Phase 7：cleanup、退役 MongoDB cluster、保留 dump 90 天

### 規格面 5：Evidence

- query 一致性 diff log、aggregation result checksum、RU consumption baseline、replication lag
- 對應 [schema-migration-rollout-evidence](/backend/01-database/schema-migration-rollout-evidence/) 的 dual-write 驗證

### 規格面 6：Cutover + cleanup

- read-only window < 10 min、aggregation result 對齊驗證
- Rollback 條件：query error rate > 1% 或 RU consumption 異常偏高（翻譯層 cost 高於估算）

## 失敗模式

### Failure 1：假設 wire compat = 100% 行為相同

「100% wire compat」是 vendor 行銷話術、實際是「在某些 query pattern 下相容」— aggregation pipeline 跑出不同結果、上 production 才發現。9.C30 case 揭露的「『MongoDB 不夠用』是行銷話術。實際是 *MongoDB 在某些 workload pattern 下不夠用*」同模型反向適用 — *相容性* 也是「在某些 query pattern 下相容」、不是普遍相容。

修法：production query corpus dual-write 跑一遍、case-by-case 驗證每個 query pattern、不能假設 wire compat = 行為 100% 一致。Phase 4 shadow read 不是「跑一些 test」、是 *把所有 production query 跑一遍、對 checksum*。

### Failure 2：`_id` 當 partition key

MongoDB 的 `_id` 默認 ObjectId、跟 Cosmos DB partition key 邏輯不同；直接拿 `_id` 當 partition key 容易在 high-cardinality 但低均勻度的 access pattern 下 hot partition（VIP 用戶、機器人帳號）。要審 application 的真實 query pattern、選會均勻散佈的欄位、見 [partition-key-design](../partition-key-design/)。

### Failure 3：Change stream resume token 跨 API 不可用

MongoDB API 提供 change stream wire compat、但 resume token 格式跟 native MongoDB 不同、跨環境 resume 會失敗。CDC pipeline 在遷移期間需要分兩段：MongoDB 端用原生 resume token、Cosmos DB 端用 Change Feed continuation token、不能 *把 token 從 MongoDB 帶到 Cosmos DB 繼續*。

### Failure 4：評估時只測 happy path

unsupported aggregation stage 在 dev 環境的 sample data 看不出、production 才爆。常見漏的 stage：`$graphLookup` / `$facet` / `$bucket` / 部分 `$lookup` pattern / window function。Phase 0 audit 要把 production aggregation pipeline 拉出來、對照 [Cosmos DB MongoDB API feature support](https://learn.microsoft.com/azure/cosmos-db/mongodb/feature-support-60) 清單。

### Failure 5：把 dogfood 案例數字當 benchmark

9.C30 Microsoft 365 case 自承沒提具體 throughput / latency / cost 數字、不能拿 dogfood 案例的「成功」推論「我們團隊遷過去也會成功」— 規模 / workload pattern / 團隊能力都不同。寫 sizing 計畫時要回到 [ru-cost-model-sizing](../ru-cost-model-sizing/) 用自己的 query corpus 量、不是抄 dogfood case。

### Failure 6：選 MongoDB API 後想升級 native MongoDB feature

MongoDB API server version 升級節奏跟 native MongoDB 不同步、新 feature 等待時間長。選 MongoDB API 等於放棄「拿到 native MongoDB 最新 feature」、若團隊 long-term commit Cosmos DB、SQL API 反而是更穩的選擇（feature 自己決定、不等翻譯層）。這條 trade-off 在 selection 階段就要決定、不能 phase 6 才發現。

## 容量與觀測

- 必看 metric：MongoDB API 特有 `MongoRequests` / `MongoRequestCharge`、diagnostic log 看 aggregation stage 是否被翻譯成 cross-partition query
- 容量規劃：MongoDB API 翻譯層有 overhead、相同 query SQL API 通常便宜 10-20% — 但這個差距通常不足以驅動 API 切換（切換成本太高、見 Failure 6）
- RU baseline：Phase 4 shadow read 階段量每個 query pattern 的 `x-ms-request-charge`、進 [ru-cost-model-sizing](../ru-cost-model-sizing/) 的 capacity forecast
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：API kind 選擇進 cost forecast、不是 sizing 後才補

## Cosmos DB unique selection value 整合（四層 framing 收束）

讀者讀完本篇要能回答：「我該選 Cosmos DB MongoDB API、Cosmos DB SQL API、還是留 Atlas」 — 答案的四層判讀（對應 Framing 1-4）：

- **遷移路徑（Framing 1）**：你是要保留 + 補周邊、換託管、還是換 vendor？三型風險不同、Forbes 時程不代表 Microsoft 365 時程
- **dogfood signal（Framing 2）**：你能用 frame 借鑑 Microsoft 365、但避免拿 dogfood 數字當 benchmark
- **multi-model 是否真用上（Framing 3）**：你的系統未來會不會用 graph / Cassandra / Table API？只用一個 API 時 multi-model unique value 不成立
- **跨雲 hedging vs Azure 整合（Framing 4）**：你的雲商策略是已定還是未定？已綁 Azure 時 lock-in 是整合延伸、未定時 lock-in 是 hedging 損失

四層回答完、selection 才能落地、不是「Azure 上要不要用 Cosmos DB」單一問題。

## Anti-recommendation

- 純 MongoDB 投資、未來不會綁 Azure、應留在 Atlas — 跨雲彈性的長期價值高於每月 hosting 差價
- MongoDB API 是「Azure 上的 MongoDB 替代品」、*不是* MongoDB 升級版 — 想要 native MongoDB latest feature 應留在 Atlas / 自管 MongoDB
- 跨雲 hedging 是 selection 主 driver 時、Cosmos DB（單雲）+ DynamoDB（單雲）+ Spanner（單雲）都不該進候選名單
- 只用 document model、不用其他 4 個 API 時、multi-model 不該變成 selection 理由 — 此時 Atlas managed 服務的 MongoDB 原生行為通常更穩

## 相關連結

- [Cosmos DB vendor overview](/backend/01-database/vendors/cosmosdb/) — 本文是該頁尾「MongoDB API vs native SQL API trade-off」backlog 的深度展開
- [9.C30 Microsoft 365 dogfood case](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — 本文主案例、四層 framing 的證據錨點
- [9.C36 Coinbase](/backend/09-performance-capacity/cases/coinbase-mongodb-document-platform/) — 三型遷移路徑「保留 + 補周邊」對照
- [9.C37 Forbes](/backend/09-performance-capacity/cases/forbes-mongodb-atlas-multi-cloud-migration/) — 三型遷移路徑「同 DB 換託管」對照
- [partition-key-design](../partition-key-design/) — Phase 1 partition key 從 shard key 翻譯
- [ru-cost-model-sizing](../ru-cost-model-sizing/) — Phase 4 RU consumption baseline
- [consistency-levels-engineering](../consistency-levels-engineering/) — read preference 對應 consistency level
- [MongoDB vendor](/backend/01-database/vendors/mongodb/) — Atlas 對照
- [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/) — 跨 vendor 遷移共通模型
- [Database 卡片](/backend/knowledge-cards/database/) / [Change Data Capture 卡片](/backend/knowledge-cards/change-data-capture/) — 概念基底
- 官方：[Cosmos DB MongoDB API feature support](https://learn.microsoft.com/azure/cosmos-db/mongodb/feature-support-60)
