---
title: "1.2 Schema Design 與資料建模"
date: 2026-05-13
description: "整理 table、index、key、partition、denormalization 與命名規則"
weight: 2
tags: ["backend", "database", "schema"]
---

資料綱要設計（schema design）的核心責任是把業務狀態轉成可維護、可查詢、可演進的資料結構。資料建模做得好、交易邊界、查詢效率、migration 成本與事故修復路徑都會更穩定。

本章是 01 模組的基礎章節之一、結合 [1.3 transaction boundary](/backend/01-database/transaction-boundary/)（交易範圍）、[1.7 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/)（演進證據）與 [1.10 KV / Document 容量規劃](/backend/01-database/kv-document-capacity-planning/)（partition key 設計）一起讀。讀完後能回答：table 怎麼切、index 怎麼選、什麼時候 denormalize、partition 怎麼設、命名怎麼治理。

## 先定義狀態責任

資料模型第一步是定義狀態責任：哪些欄位代表正式狀態、哪些欄位是派生值、哪些欄位只為追蹤與審計。這個分層會直接決定 table 邊界與 relation 方向。

在訂單服務中、訂單主檔、付款狀態、庫存扣減屬於正式狀態；展示排序欄位、快取摘要屬於派生值；版本號、更新時間與來源欄位屬於可追蹤證據。把三類混在同一模型裡、後續查詢與演進成本會持續上升。

詳見 [1.8 State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)。

## Table 與 Relation

table 切分要對齊業務聚合邊界。聚合內需要交易一致性的欄位、放在同一交易可控範圍；跨聚合流程透過事件或引用關係接續。relation 的責任是表達資料約束、不是替代流程編排。

主鍵策略要先回答「如何穩定識別」與「如何支援查詢」。自然鍵可讀性高但變動風險高；代理鍵穩定且易擴展、常搭配業務唯一鍵一起使用。外鍵策略則要平衡完整性與演進自由度：正式核心域可強約束、跨域整合可由應用層保護並保留遷移彈性。

**主鍵選擇實務**：

ID 設計不只是「選個格式」，而是在五個維度做取捨。先理解取捨、再按場景選型。

### ID 設計的五個取捨維度

| 維度 | 說明 | 範例 |
| ---- | ---- | ---- |
| **唯一性** | 跨機器、跨時間不碰撞 | 分散式系統的核心需求 |
| **有序性** | 是否可按生成順序排序 | B-tree 插入效能、時間軸查詢 |
| **隱私性** | 是否洩漏業務資訊（量級、時間、機器） | 外部可見的 ID 不應洩漏用戶數量 |
| **儲存成本** | 佔多少 byte、index 體積 | 高 TPS 場景每 byte 都乘以百萬筆 |
| **產生效能** | 需要鎖？需要 crypto/rand？需要 network call？ | 熱路徑上的 ID 產生 ns 級差異有影響 |

### ID 類型選型矩陣

| ID 類型 | 大小 | 唯一性 | 有序性 | 隱私性 | 產生效能 | 適合場景 |
| ------- | ---- | ------ | ------ | ------ | -------- | -------- |
| **Bigint sequence** | 8 byte | 單機唯一 | 嚴格有序 | 低（可猜量級） | 最快（DB 自增） | 單機、內部 ID |
| **UUID v4** | 16 byte | 全域唯一 | 無序 | 高（不可預測） | 中（crypto/rand） | 外部可見 ID、隱私敏感 |
| **UUID v7** | 16 byte | 全域唯一 | 時間有序 | 中（時間可推） | 中（timestamp + crypto/rand） | 內部 ID、事件追蹤、DB 主鍵 |
| **ULID** | 16 byte | 全域唯一 | 時間有序 | 中 | 中 | 類 UUID v7（先於 v7 標準化） |
| **Snowflake** | 8 byte | 需要 machine_id 協調 | 時間有序 | 低（含 machine_id） | 快（無 crypto） | 高 TPS + 分散式 + 空間敏感 |
| **NanoID** | 可變 | 依長度 | 無序 | 高 | 快（PRNG 即可） | URL-safe 短 ID |

### 選型決策流程

```
需要跨機器唯一？
  └─ 否 → Bigint sequence（最簡單、效能最好）
  └─ 是 → ID 對外部可見？
           └─ 是 → 隱私敏感？
                    └─ 是 → UUID v4（不可預測）
                    └─ 否 → UUID v7（有序、DB 友好）
           └─ 否 → 空間敏感（8 byte vs 16 byte）？
                    └─ 是 → Snowflake（需要 machine_id 協調）
                    └─ 否 → UUID v7（簡單、標準）
```

### 有序 ID 的 DB 效能影響

B-tree 索引的插入效能和 key 的分布有直接關係。UUID v4 的隨機分布導致每次插入都可能落在 B-tree 的不同 leaf page，造成大量隨機 I/O（page split、cache miss）。UUID v7 的時間戳前綴讓插入集中在 B-tree 的尾端，接近 sequential insert。

| 測試場景（PostgreSQL、1000 萬筆） | UUID v4 | UUID v7 | Bigint |
| --------------------------------- | ------- | ------- | ------ |
| INSERT 吞吐 | ~5,000/sec | ~15,000/sec | ~20,000/sec |
| Index 大小 | ~400 MB | ~350 MB | ~200 MB |
| 範圍查詢延遲 | 要額外建 timestamp index | UUID 本身有序 | 天然有序 |

上表數字是量級估算，實際效能依硬體和 workload 而定。核心結論：UUID v7 的插入效能約為 v4 的 3 倍，接近 bigint sequential。

### 隱私考量：v4 vs v7

UUID v7 的前 48 bit 是 Unix 時間戳（毫秒精度）。攻擊者拿到 UUID v7 可以推算「這個 ID 在幾點幾分產生」。這在不同場景有不同風險：

| 場景 | v7 洩漏的資訊 | 風險等級 | 建議 |
| ---- | ------------- | -------- | ---- |
| 內部事件追蹤 ID | 事件產生時間 | 無風險（log 本身有 timestamp） | v7 |
| DB 主鍵（內部） | 資料建立時間 | 低風險 | v7 |
| Session ID（自用工具） | Session 開始時間 | 低風險 | v7 |
| Session ID（商業產品、有外部使用者） | 使用者活動時間 | 中風險（可交叉比對身份） | v4 |
| API key / token | 簽發時間 | 高風險（可推斷 key 輪換週期） | v4 或加密 |
| 訂單 ID（外部可見） | 下單時間 + 量級趨勢 | 中風險 | v4 或 NanoID |

經驗法則：**對外暴露給不可信第三方的 ID 用 v4（不可預測），內部 ID 用 v7（有序、效能好）。**

### 各語言的標準庫支援

| 語言 | UUID v4 | UUID v7 | 套件 |
| ---- | ------- | ------- | ---- |
| Python 3.14+ | `uuid.uuid4()` | `uuid.uuid7()` | 標準庫 |
| Python < 3.14 | `uuid.uuid4()` | `uuid_utils.uuid7()` | 第三方 |
| Go | `google/uuid` v4 | `google/uuid` v7（1.6+） | 事實標準 |
| TypeScript | `crypto.randomUUID()` | 標準庫無（`uuidv7` npm） | 第三方 |
| Dart | `uuid` package | `uuid` package v4+（支援 v7） | pub.dev |
| PostgreSQL | `gen_random_uuid()` | `uuidv7()`（pg_uuidv7 extension） | 擴展 |

Go 的 `google/uuid` v1.6+ 內建 `uuid.NewV7()`，效能約 350ns/op（含 crypto/rand），和 JSON 解析（5-10μs）、DB 寫入（200μs）相比不是瓶頸。

對應 KV 案例：[9.C5 Amazon Ads partition key](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)、[9.C15 Tixcraft composite key](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 都是主鍵策略的延伸。

## Index 設計

index 設計要從查詢路徑反推、不是從欄位列表前推。每個高頻查詢至少要回答三件事：過濾條件是什麼、排序規則是什麼、回傳範圍有多大。這三件事能否由索引覆蓋、決定了 latency 與成本。

**Index 類型對照**：

| Index 類型     | 適用 query                                         | 例子                                  |
| -------------- | -------------------------------------------------- | ------------------------------------- |
| B-tree（預設） | `WHERE col = ?` / `WHERE col > ?` / `ORDER BY col` | 多數查詢                              |
| Hash           | `WHERE col = ?`（不支援 range）                    | PostgreSQL 限定、少用                 |
| GIN            | JSONB / array / full-text search                   | `WHERE jsonb_data @> ?`               |
| GiST           | 範圍 / 地理 / 自訂型別                             | PostGIS、range type                   |
| BRIN           | 大表時序資料、欄位跟物理順序相關                   | log table by timestamp                |
| Partial index  | `WHERE` 條件下才建 index                           | `WHERE status = 'pending'`            |
| Covering index | 包含所有查詢欄位、避免 heap lookup                 | `INDEX (a) INCLUDE (b, c)`            |
| Compound index | 多欄位、順序敏感                                   | `INDEX (a, b)` 對 `WHERE a=? AND b=?` |

**常見設計原則**：

1. 先保護交易關鍵查詢、再處理報表與後台查詢
2. 複合索引依查詢過濾與排序順序排列、避免僅憑欄位熱門度排列
3. 大表變更前先評估索引建立成本與回退方案、避免在高峰時段同步放大風險
4. 定期 review 未用 index（PostgreSQL `pg_stat_user_indexes`、MySQL `sys.schema_unused_indexes`）— 寫入吞吐被舊 index 拖垮
5. partial index 對 `boolean` / `status` column 特別有用 — 只 index 「pending」「failed」等小集合

**Index 反模式**：

- 每個欄位都建 index：寫入吞吐被拖垮
- 不看 EXPLAIN 就建 index：可能跟 query planner 不對齊
- 用 OR 條件依賴單一 index：query planner 不一定能用
- 大表 ALTER INDEX 不分批：lock 整個表

## Denormalization 模式

normalize 是 SQL 的預設、但 denormalize 有時是更好的工程選擇。

**Precomputed aggregate**：

- 把 COUNT / SUM 結果存在 parent row 而非每次 query 算
- 例：`posts.comment_count` 存實際值、不每次 SELECT COUNT
- 風險：consistency（comment 寫入後 count 沒更新）
- 對策：用 trigger 或應用層 transaction 確保同步、或定期 reconcile

**Embedded one-to-many**：

- 小量 1-many 關係可以 embed 成 JSONB / nested column
- 例：`order.line_items` JSON column、不另建 line_items table
- 風險：個別 line item 查詢不便
- 適合：line items 通常一起讀寫（同 transaction boundary）

**Materialized view**：

- 預計算 query 結果、定期 refresh
- 適合：複雜 JOIN / aggregation 重複跑
- 風險：refresh window 內看到舊資料

**Read model**（CQRS）：

- 寫入路徑跟讀取路徑用不同 schema
- 寫入 normalize、讀取 denormalize 成不同 read model
- 詳見 [1.8 State Ownership](/backend/01-database/state-ownership-query-boundary/)

**對應案例**：

- [9.C27 Disney+ watch list](/backend/09-performance-capacity/cases/disney-plus-content-metadata/) — denormalize 用戶 metadata、跨裝置查詢方便
- [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — DynamoDB single-table design 是極端 denormalization

## Partition 策略

單表 > 1 TB 時、partition 是必要的維運手段。partition 不是「擴 storage」、是「讓 vacuum / index / DROP 可分批跑」。

**Partition 類型**：

- **Range partition**：按 timestamp / id 範圍切。`orders_2024_q1`, `orders_2024_q2`...
- **List partition**：按枚舉值切。`orders_us`, `orders_eu`...
- **Hash partition**：按 hash 均勻切。適合無自然切分維度的大表

**Partition 設計要點**：

1. partition key 必須出現在 *多數 query 的 WHERE clause*（partition pruning 才能生效）
2. partition 數量 *適中*（10-100）— 太少 partition 太大、太多 partition metadata 開銷大
3. 老 partition 可以 DROP 或 archive、儲存成本可控
4. `cross-partition unique constraint` 限制 — 唯一鍵必須含 partition key

**對應案例**：

- [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 200 個獨立 Aurora cluster 是極端 partition by business
- [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — DynamoDB 透明 partition、應用層不必管

## Schema Evolution 友好設計

schema 從 day 1 就要為演進設計、不能假設「以後不會改」。

**避免 breaking changes**：

- **加欄位**：safe（nullable 或 default）
- **刪欄位**：unsafe（先讓所有 code 不再讀 → 部署 → 再刪）
- **改欄位類型**：unsafe（先加新欄位、雙寫、backfill、移除舊欄位）
- **改欄位名**：unsafe（同上）
- **加 NOT NULL constraint**：unsafe（先 backfill default、再加 constraint）

**Evolution-friendly schema 原則**：

1. **欄位 nullable by default**：除非業務真的不能 null、否則先 nullable、之後再 tighten
2. **避免大表 ALTER TABLE**：用 [Expand / Contract](/backend/knowledge-cards/expand-contract/) 模式
3. **predict breaking changes**：訂版本、跟 application code 同步演進
4. **schema version column**：每 row 帶 version、應用層按版本處理
5. **migration 工具版本控**：Flyway / Liquibase / Atlas / golang-migrate 必須有

詳見 [1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/) 跟 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)。

## Naming 與一致性

命名規則的責任是維持跨版本可讀性。table、column、index 的命名若沒有一致語意、migration 與故障排查會持續變慢。穩定做法是把命名和業務語意對齊、並保留可辨識版本與作用域。

**Naming 慣例**：

- **Table**：複數名詞、`snake_case`（`orders`, `payment_methods`）
- **Column**：`snake_case`、明確語意（`created_at` 不是 `ts`）
- **Foreign key**：`{referenced_table}_id`（`user_id` 指 `users.id`）
- **Boolean**：`is_*` / `has_*` / `can_*`（`is_active`, `has_subscription`）
- **Timestamp**：`*_at` for events（`created_at`, `paid_at`）、`*_on` for dates（`born_on`）
- **Index**：`idx_{table}_{cols}`（`idx_orders_user_id_created_at`）
- **Unique constraint**：`uq_{table}_{cols}`
- **Foreign key constraint**：`fk_{table}_{ref}`

**避免的反模式**：

- 縮寫不一致（`u_id` vs `user_id`）
- 隱性意義（`status` 是 enum、值在哪裡？）
- 跨表同義不同名（`user.name` vs `customer.full_name`）
- 反向命名（`name_first` vs 業界 `first_name`）

schema 演進時、命名與結構要一起考慮。欄位重命名、拆欄位、合併欄位都應配合 [Expand / Contract](/backend/knowledge-cards/expand-contract/) 與 [schema migration](/backend/knowledge-cards/schema-migration/) 策略、讓新舊版本在過渡期可共存。

## 判讀訊號

| 訊號                               | 判讀重點                       | 對應動作                               |
| ---------------------------------- | ------------------------------ | -------------------------------------- |
| 同一查詢在資料量成長後延遲快速上升 | 索引與查詢模型不對齊           | 補複合索引、重寫查詢條件               |
| migration 後查詢計畫顯著變化       | 統計資訊或索引選擇偏移         | 重建統計、校正索引與查詢               |
| 交易流程需跨多表同步更新           | table 邊界與業務聚合邊界不一致 | 重切聚合邊界、減少跨聚合同步更新       |
| 同義欄位在多表重複存在且語意漂移   | 命名與責任邊界失控             | 收斂欄位責任、補資料字典與遷移計畫     |
| 修復事故時需要多次手動比對資料     | 可追蹤欄位與關聯鍵不足         | 補追蹤欄位、設計對帳查詢與修復流程     |
| 單表 > 1 TB 且 vacuum 變慢         | 沒 partition、後續維運成本爆   | 規劃 partition by range / hash         |
| 大量 unused index                  | 寫入吞吐被舊 index 拖垮        | review pg_stat_user_indexes、定期 drop |

## 常見誤區

把 schema 設計等同於「先能寫入就好」、會把結構債延後到流量成長與事故時一次爆發。資料模型的工程價值在於可演進性、不在於初版欄位數量最少。

把索引當成效能補丁、忽略查詢模型與資料責任、也會讓後續維護成本持續疊加。索引與查詢要一起設計、才能在演進中保持穩定。

把 normalize 當成 *絕對守則*、忽略 denormalize 的工程效益。1NF / 2NF / 3NF 是理論起點、不是 *production 必須*。

## 案例對照

| 案例                                                                                              | Schema 設計重點                                  |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)         | DynamoDB single-table design、極端 denormalize   |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)     | Composite partition key、event_id × user_id_hash |
| [9.C4 DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)     | 200 個獨立 cluster、按業務切 partition           |
| [9.C27 Disney+](/backend/09-performance-capacity/cases/disney-plus-content-metadata/)             | watch list embedded design、跨裝置同步           |
| [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) | Cosmos DB synthetic partition key 強制分散       |

## 案例回寫

資料建模議題可以用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 做回寫練習。讀這個事件時、先看跨區拓樸切換如何影響資料一致性、再回到本章檢查三件事：聚合邊界是否清晰、交易查詢與對帳查詢是否分層、修復時是否有可追蹤欄位與對帳鍵。

這個案例主要支撐的是「查詢與資料模型邊界」判讀、不直接支撐 transaction retry 或 queue replay 調校；若問題是重試放大、應轉到 1.3 或 3.x 章節處理。

當事件呈現長時間人工比對或查詢語意漂移時、先修正本章的 query boundary 與 naming 一致性、再補 [1.6 資料庫轉換實作](/backend/01-database/database-migration-playbook/) 的驗證與回退路徑。

## 跨模組路由

schema 設計會直接影響後續可靠性與事故處理。

1. 與 1.3 的交接：交易一致性邊界落在 [transaction boundary](/backend/01-database/transaction-boundary/)。
2. 與 1.6 的交接：演進策略落在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
3. 與 1.7 的交接：欄位責任進入 production rollout 時、讀 [Schema Migration Rollout 證據實作示範](/backend/01-database/schema-migration-rollout-evidence/)。
4. 與 1.8 的交接：state ownership 跟 query boundary 設計落在 [State Ownership](/backend/01-database/state-ownership-query-boundary/)。
5. 與 1.10 的交接：KV / Document 的 partition key 設計落在 [KV / Document 容量規劃](/backend/01-database/kv-document-capacity-planning/)。
6. 與 4.20 的交接：查詢與資料驗證證據進入 [Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。
7. 與 6.11 的交接：高風險 schema 變更進入 [Migration Safety](/backend/06-reliability/migration-safety/)。
8. 與 8.19 的交接：資料修復與回退決策記錄進入 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

- 平行：[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)、[1.8 State Ownership](/backend/01-database/state-ownership-query-boundary/)
- 下游：[1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/) / [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/) / [1.10 KV / Document 容量規劃](/backend/01-database/kv-document-capacity-planning/)
- Vendor：[PostgreSQL index 設計](/backend/01-database/vendors/postgresql/)、[MySQL InnoDB clustered index](/backend/01-database/vendors/mysql/)、[DynamoDB single-table design](/backend/01-database/vendors/dynamodb/)
- DynamoDB schema 深入：[single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/) / [partition key 反模式](/backend/01-database/vendors/dynamodb/partition-key-antipatterns/) / [GSI / LSI 設計](/backend/01-database/vendors/dynamodb/gsi-lsi-design/)
- MongoDB schema 深入：[schema design pattern](/backend/01-database/vendors/mongodb/schema-design-pattern/) / [shard key 選型](/backend/01-database/vendors/mongodb/shard-key-selection/)
- Cosmos DB schema 深入：[partition key 設計](/backend/01-database/vendors/cosmosdb/partition-key-design/)
