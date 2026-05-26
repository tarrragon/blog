# Cosmos DB MongoDB API vs SQL API：相容性、aggregation 差異、何時用哪個

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/)（含 Migration Playbook 6 規格面）與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：團隊已用 MongoDB / 考慮從 MongoDB Atlas 遷到 Azure、Cosmos DB 提供「MongoDB API（wire protocol 相容）」跟「native SQL API」兩條路；MongoDB API 的相容範圍隨 server version 演進、aggregation pipeline / index / change stream 行為跟原生 MongoDB 有差；SQL API 是 Cosmos DB native、能力最完整但要重寫
- 讀者徵兆：「MongoDB API 我們的 aggregation pipeline 跑得起來嗎」「`$lookup` 在 Cosmos DB MongoDB API 支援嗎」「change stream 跟 Change Feed 是同一回事嗎」「為什麼有人說 MongoDB API 只是過渡、最終要遷 SQL API」
- 真實壓力：Microsoft 自家 Microsoft 365 從 MongoDB 遷到 Cosmos DB MongoDB API、planet-scale 分析；中型 SaaS 評估 Atlas vs Cosmos DB MongoDB API 的 lock-in 成本
- Case anchor: [9.C30 Microsoft 365](/backend/09-performance-capacity/cases/microsoft-365-cosmos-db-analytics/) — MongoDB → Cosmos DB MongoDB API、planet-scale 分析、dogfood 證據

## 核心機制（Vendor-specific mechanism）

- 兩個 API 的關係：底層是同一個 Cosmos DB 分散式 KV/document store、API layer 翻譯不同 wire protocol
- MongoDB API：
  - 相容 MongoDB wire protocol（時間敏感 claim、查最新支援版本如 6.0 / 7.0）
  - Driver 不變：直接用 mongo-go-driver / pymongo / mongoose 等
  - 翻譯層：MongoDB 操作翻譯成 Cosmos DB internal、不是真的跑 MongoDB engine
- SQL API：
  - Cosmos DB native query language（SQL-like、不是標準 SQL）
  - 直接操作 JSON document、ARRAY / nested field native 支援
  - 完整 Cosmos DB feature 支援（Change Feed、stored procedure、trigger）
- 關鍵差異點：
  - `$lookup`（join）：MongoDB API 支援度有限、跨 partition 性能差；SQL API 也沒 JOIN（document model 哲學）
  - Aggregation pipeline：部分 stage 不支援或行為不同（時間敏感、查支援列表）
  - Index：MongoDB API hint / explain 行為跟 native MongoDB 不同
  - Change stream：MongoDB API 提供 change stream wire compat、但底層是 Cosmos DB Change Feed（語義 / ordering / retention 有差）
  - Transaction：MongoDB API multi-document transaction 限制 partition、SQL API 也限同 partition
- 對應 knowledge card：[database](/backend/knowledge-cards/database/)、[change-data-capture](/backend/knowledge-cards/change-data-capture/)

## 操作流程（Operations）

- 選 API：建 account 時選 API kind、*無法事後切換*
- MongoDB API 連線：mongodb connection string、跟 Atlas 一樣
- SQL API 連線：Cosmos DB SDK（C# / Java / Node / Python）、document 直接操作
- 相容性驗證：用 [Data Migration Tool](https://github.com/Azure/azure-documentdb-datamigrationtool) 或自寫 script、把 production query corpus 跑一遍、列 unsupported / behavior-different 清單
- Aggregation pipeline 驗證：每個 pipeline stage 跑單元測、量 RU 消耗、對照 native MongoDB result
- 驗證點：
  - 相容性測試覆蓋 production query 90%
  - 每個 query 的 RU < SLA budget
  - Change stream lag < SLA
- Rollback boundary：API kind 不可改、rollback 等於 export → recreate account → import；MongoDB API → SQL API 需重寫 app

## Migration Playbook 6 規格面（MongoDB → Cosmos DB MongoDB API）

### Driver

- 主要 driver：Azure 生態 lock-in / 需要更好的 global distribution / Atlas 跨雲成本
- No-go condition：跨雲需求（Atlas 仍是首選）；需要 native MongoDB latest feature（API 落後）

### Diff Audit

- **Schema**：document shape 不變（wire compat）；但 `_id` 行為跟 Cosmos DB partition key 綁定方式要審
- **Operational**：自管 MongoDB → managed Cosmos DB、replica set / sharding 變成 partition + region；備份 / monitoring 全換
- **Paradigm**：不變（仍 document）
- **Components**：MongoDB driver 保留、aggregation pipeline 部分需重寫
- **Application**：connection string、authentication mechanism（SCRAM → Azure key）、read preference 對應 consistency level
- **Topology**：replica set → multi-region replication、shard key → partition key
- Type 判定：**Type B drop-in（partial）**、wire compat 但有相容性 gap

### Phase Plan

- Phase 0：相容性 audit、列 unsupported aggregation stage
- Phase 1：partition key 設計（從 shard key 翻譯）
- Phase 2：bulk export-import（mongodump → Cosmos DB Data Migration Tool）
- Phase 3：CDC sync（MongoDB oplog → Azure Data Factory / 自寫）
- Phase 4：shadow read 驗證 query 一致性
- Phase 5：read cutover（讀切 Cosmos、寫仍 MongoDB）
- Phase 6：write cutover
- Phase 7：cleanup

### Evidence

- query 一致性 diff log、aggregation result checksum、RU consumption baseline、replication lag

### Cutover

- read-only window < 10 min、aggregation result 對齊驗證、rollback 條件（query error rate > 1%）

### Cleanup

- 退役 MongoDB cluster、保留 dump 90 天、退役 oplog connector

## 失敗模式（Failure modes）

- 假設 wire compat = 100% 行為相同：aggregation pipeline 跑出不同結果、上 production 才發現
- `_id` 當 partition key：跟 MongoDB shard key 邏輯不同、容易 hot partition
- Change stream resume token 跨 API 不可用：MongoDB API change stream 的 resume token 跟原生 MongoDB 格式不同、跨環境 resume 失敗
- 評估時只測 happy path：unsupported aggregation stage 在 dev 看不出、production 才爆
- 選 MongoDB API 後想升級 feature：MongoDB API server version 升級節奏跟 native MongoDB 不同步、新 feature 等待時間長
- 不評估 SQL API：MongoDB API 永遠落後 native、若 long-term commit 到 Cosmos DB、SQL API 是更穩的選擇

## 容量與觀測（Capacity & observability）

- 必看 metric：MongoDB API 特有的 `MongoRequests`、`MongoRequestCharge`；diagnostic log 看 aggregation stage 是否被翻譯成 cross-partition query
- 容量規劃：MongoDB API 翻譯層有 overhead、相同 query SQL API 通常便宜 10-20%
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)：API kind 選擇進 cost forecast

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[partition-key-design](./partition-key-design.md)（shard key → partition key）、[ru-cost-model-sizing](./ru-cost-model-sizing.md)（MongoDB API 成本差異）、[consistency-levels-engineering](./consistency-levels-engineering.md)（read preference → consistency level）
- 跟 [MongoDB vendor](/backend/01-database/vendors/mongodb/) 對照、Atlas 跨雲 vs Cosmos DB Azure-only trade-off
- 跟 1.x 章節：[1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- Anti-recommendation：純 MongoDB 投資、未來不會綁 Azure、應留在 Atlas；MongoDB API 是「Azure 上的 MongoDB 替代品」、不是 MongoDB 升級版

## 寫作前置 checklist

- [ ] case anchor 確認：9.C30 Microsoft 365 dogfood 為主案例
- [ ] knowledge card 雙引用：database、change-data-capture
- [ ] sibling 對比：MongoDB Atlas、DocumentDB（AWS）
- [ ] 預估寫作長度：340-400 行（兩 API 對比 + migration playbook 6 規格面、密度高）
