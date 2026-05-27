---
title: "1.4 Repository Adapter 實作"
date: 2026-05-13
description: "Port / Adapter 邊界、row mapping、error translation、ORM vs query builder 選型、contract test 設計"
weight: 4
tags: ["backend", "database", "repository-adapter"]
---

資料庫倉儲轉接層（repository adapter）的核心責任是把應用層語意轉成資料庫可執行操作、並把資料庫錯誤回譯成業務可判讀結果。它是 `domain model` 和 `SQL model` 之間的邊界層、不承擔業務流程編排。

本章從 hexagonal architecture 的 port / adapter 模式出發、處理 mapping、error translation、testing 跟跨服務 transaction 等實作議題。讀完後讀者能設計一個可演進、可測試、可換 DB 的 repository 層。

## Port / Adapter 邊界

Repository 在 hexagonal architecture（也叫 ports & adapters）中是 *outbound port* 的實作。

**Port（domain layer 定義）**：

- 抽象 interface / protocol、描述 *領域語意*
- 不暴露 SQL、不暴露 DB 細節
- 例：`type OrderRepository interface { Find(id) Order; Save(order); ... }`

**Adapter（infrastructure layer 實作）**：

- 實作 port、負責跟具體 DB 對話
- 翻譯 domain entity ↔ DB row
- 翻譯 DB error → domain error
- 例：`type SQLOrderRepository struct { db *sql.DB }`

**為什麼這層抽象有價值**：

1. **可替換性**：DB 換 vendor 時、domain layer 不必改
2. **可測試性**：在 domain layer test 時可注入 memory fake、不必起 DB
3. **語意清楚**：domain 不被 SQL 細節污染、business rule 集中
4. **演進可控**：schema 改動時、只在 adapter 改 mapping、不擴散到全程式

詳見 [Repository Adapter 卡片](/backend/knowledge-cards/repository-adapter/)。

## Adapter 三個核心責任

adapter 接收應用層輸入、負責三件事：查詢與命令組裝、row mapping、錯誤翻譯。業務規則判斷留在 service / usecase 層、adapter 聚焦在資料持久化語意與資料庫行為。

邊界清楚的好處是演進可控。schema 調整時、只需要在 adapter 收斂欄位映射與查詢變更、不用把 SQL 細節滲透回 domain 層。

### 1. 查詢與命令組裝

把 domain 操作翻成具體 SQL / NoSQL query。實作層級有取捨：

- **Raw SQL**：完全控制、易追 query plan、但容易拼錯字、易 SQL injection
- **Query builder**（GORM Build、Knex、SQLAlchemy Core）：型別安全、不寫字串、但學 DSL
- **ORM**（GORM、SQLAlchemy ORM、Active Record）：高抽象、自動 mapping、但隱藏細節、容易產生 N+1

詳見下方「ORM vs Query Builder vs Raw SQL」段。

### 2. Row Mapping 與 Nullable Handling

row mapping 的責任是把資料庫欄位轉成穩定模型。欄位型別、時間格式、枚舉值、可空欄位都要有明確轉換規則。可空欄位需要顯式處理、避免把「缺值」誤當有效預設值。

**Nullable handling 模式**：

- **Optional type**：Go `sql.NullString`、Java `Optional<T>`、Rust `Option<T>`、Python `Optional[T]`
- **Sentinel value**：用特殊值代表 null（不推薦、易混淆）
- **Default fallback**：null → 預設值（要明確、不要悄悄轉換）

資料模型演進時、新舊欄位可能共存。adapter 要支援過渡期讀寫相容、讓版本切換能分批進行。詳見 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)。

### 3. Error Translation

error translation 的責任是把底層錯誤分類成應用層可決策訊號。唯一鍵衝突、外鍵限制、交易衝突、連線逾時、都需要翻譯成可行動錯誤類型、而不是將原生錯誤字串直接外漏。

**常見錯誤分類**：

| Domain error          | SQL error 對應                              | 應用層動作                |
| --------------------- | ------------------------------------------- | ------------------------- |
| `ErrAlreadyExists`    | `unique_violation`（PostgreSQL 23505）      | 409 Conflict / 業務 retry |
| `ErrNotFound`         | empty result set                            | 404                       |
| `ErrConstraintFailed` | `foreign_key_violation`（23503）            | 400 Bad Request           |
| `ErrConflict`         | `serialization_failure`（40001）            | retry with backoff        |
| `ErrTimeout`          | `query_canceled`（57014）/ context deadline | retry / circuit break     |
| `ErrUnavailable`      | connection refused / pool exhausted         | circuit break / fallback  |

這層翻譯會直接影響重試、回退與事故判讀。分類越穩定、越能在 06/08 模組形成一致決策語言。

## ORM vs Query Builder vs Raw SQL

選 mapping 工具是 repository adapter 的核心取捨。

### Raw SQL

- 優勢：完全控制 query plan、易 tune
- 優勢：大規模 query 性能最好
- 限制：易拼錯字、IDE 支援差
- 風險：一不小心就 SQL injection（用 prepared statement / parameterized query）
- 適合：性能極限關鍵 / 複雜 query / 已有 SQL 專家團隊

### Query Builder

主流工具：Knex（Node）、SQLAlchemy Core（Python）、jOOQ（Java）、sqlc（Go）、Diesel（Rust）。

- 優勢：型別安全、IDE 自動完成
- 優勢：不需要 ORM 的複雜度
- 優勢：仍可看到生成的 SQL
- 限制：學 DSL 成本
- 適合：中等複雜度 + 想要安全性 + 想看 SQL

### ORM

主流工具：GORM（Go）、SQLAlchemy ORM（Python）、Active Record（Rails）、JPA / Hibernate（Java）、Entity Framework（.NET）、Prisma（TypeScript）。

- 優勢：CRUD 操作快速、boilerplate 少
- 優勢：自動 mapping、自動 transaction
- 優勢：migration 工具通常整合
- 限制：隱藏 SQL 細節、易產生 N+1 query
- 限制：複雜 query 反而比 raw SQL 難寫
- 風險：lazy loading 容易意外性能問題
- 適合：CRUD 為主的應用、團隊偏業務開發

### 選型決策

1. **小團隊 + CRUD-heavy**：ORM（快速 prototype、boilerplate 少）
2. **中型 + 混合需求**：Query Builder（安全 + 仍能寫複雜 query）
3. **大型 + 性能極限**：Raw SQL + Query Builder（複雜 query 用 raw、簡單用 builder）
4. **microservice 私有 store**：通常 Query Builder 為主（見 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) 模式）

### ORM 反模式

- `find()` 隨手呼叫導致 N+1 query
- lazy loading 在 view 層觸發 query
- 用 ORM 寫複雜 aggregation（應該 raw SQL）
- 不 eager load 關聯資料

## Testing 策略

repository 是 *infrastructure* 層、test 策略不同於 domain layer。

### Memory Fake（unit test 友善）

- 用 in-memory implementation 滿足 port interface
- 不必起 DB、快、可隔離
- 適合：domain layer test、test repository 的 *呼叫者*
- 反模式：用 memory fake test repository 本身（測不到實際 SQL 行為）

### Integration Test（驗證真實 DB 行為）

- 用 testcontainers / Docker 起真實 DB（PostgreSQL / MySQL）
- 跑真實 SQL、抓真實 error
- 用 transaction rollback 隔離各 test
- 適合：test repository adapter 本身

### Contract Test

- 驗證 adapter 對外語意穩定：同一輸入是否得到一致輸出、同一錯誤是否被穩定分類、同一查詢語意在 schema 演進後是否保持相容
- 測試重點不是資料庫產品特性覆蓋、而是邊界語意覆蓋
- 例：「unique 衝突必須回 `ErrAlreadyExists`」這條 contract、不管底層是 PostgreSQL / MySQL / SQLite 都成立

詳見 [Contract 卡片](/backend/knowledge-cards/contract/) 跟 [6.10 Contract Testing](/backend/06-reliability/contract-testing/)。

### SQLite 作為 test DB

- 起 quick、無 external dependency
- 但 SQL dialect 跟 PostgreSQL / MySQL 有差異
- 適合：簡單 query 的 test、不適合 production-fidelity test
- 對應 [SQLite vendor page](/backend/01-database/vendors/sqlite/)

## Transaction 傳遞

repository 操作通常要支援「我自己起 transaction」跟「在已有 transaction 內操作」兩種模式。

**Pattern 1：repository 自己起 transaction**：

```go
func (r *OrderRepo) PlaceOrder(ctx context.Context, order Order) error {
    tx, _ := r.db.BeginTx(ctx, nil)
    defer tx.Rollback()
    // ... 操作 ...
    return tx.Commit()
}
```

問題：跨多個 repository 時無法共用 transaction。

**Pattern 2：unit of work pattern**：

```go
func (s *Service) PlaceOrder(ctx context.Context, order Order) error {
    return s.uow.Do(ctx, func(tx Transaction) error {
        s.orderRepo.Save(tx, order)
        s.inventoryRepo.Decrease(tx, order.Items)
        s.paymentRepo.Create(tx, order.Payment)
        return nil
    })
}
```

把 transaction 從 repository 抽到 unit-of-work、跨 repository 共用。

**Pattern 3：context-based transaction**：

- 把 transaction 塞進 context
- repository 從 context 拿 transaction（有 → 用、沒有 → 自己起）
- Go 常用 pattern、但有「context 不該裝這種東西」的爭議

**選擇邏輯**：

- 簡單應用：pattern 1 夠用
- 跨 repository transaction：pattern 2 或 3
- 大型 application：pattern 2（最清楚）

詳見 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)。

## Microservice 私有 Store 對應

現代 microservice 設計強調「每個 service 私有 DB」、不跟其他 service 共用。

**對 repository adapter 的影響**：

- 每個 service 自己的 schema、自己的 adapter
- 跨 service 不直接 DB query、要透過 API
- transaction 不跨 service（用 Saga 或 outbox）
- 對應 [9.C23 Netflix](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)、[9.C7 Lyft 100+ microservice](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)

**反模式**：

- 共用 DB schema、不同 service 都 query 同一張表 → 強耦合、schema 改一個影響全部
- 跨 service 用 DB foreign key → 不能 enforce、會壞掉

## Repository Adapter 五個常見變體

實務上 repository 不止「CRUD」這個樣態：

1. **Pure CRUD repository**：Find / Save / Delete、最簡單
2. **Aggregate repository**：操作 aggregate root、含 nested entities
3. **Read model repository**（CQRS）：專門 read、不 write
4. **Event-sourced repository**：存 events、不存 state
5. **Cached repository**：包一層 cache（pass-through、refresh-ahead）

實作時要明確選哪種、不要讓一個 repository 跨多種 pattern。

## 判讀訊號

| 訊號                                  | 判讀重點                   | 對應動作                                      |
| ------------------------------------- | -------------------------- | --------------------------------------------- |
| 同一業務錯誤在不同路徑返回不同型別    | error translation 分類漂移 | 收斂錯誤分類介面與 mapping                    |
| schema 變更後應用層出現大量 null 問題 | nullable handling 規則不足 | 補顯式轉換與 fallback 規則                    |
| SQL 細節在 service 層大量出現         | adapter 邊界被繞過         | 收斂資料操作入口到 repository                 |
| 同一查詢在不同環境結果不一致          | contract test 覆蓋不足     | 補跨環境合約測試與 fixture                    |
| 事故排查時難以判斷重試與回退條件      | 錯誤分類無法對應決策       | 建立錯誤分類到 gate/incident 的映射表         |
| N+1 query 在 ORM 環境下出現           | lazy loading 反模式        | 改 eager loading 或換 query builder           |
| 跨 repository 的 transaction 不一致   | transaction 沒共用機制     | 引入 unit-of-work pattern                     |
| Test 跑很慢、需要起 DB                | test 沒分層                | unit test 用 memory fake、integration 才用 DB |

## 常見誤區

把 repository adapter 寫成「直接包 SQL 的工具函式」、容易讓業務規則與資料邏輯混雜。邊界失焦後、schema 演進與事故修復都會擴大影響面。

把資料庫錯誤原樣往上拋、也會讓上層決策不穩定。錯誤翻譯是可靠性控制面的必要前置。

把 ORM 當銀彈、忘了 SQL 還在背後。N+1 query、lazy loading 災難、複雜 aggregation 反而難寫 — 這些都是「過度信任 ORM 抽象」的後果。

把 memory fake 拿來 test repository 本身、不會抓到實際 DB bug。memory fake 是給 *呼叫者* test 用的、不是給 repository test 用的。

## 案例對照

| 案例                                                                                                       | repository / adapter 設計重點                          |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [9.C23 Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) | microservice 私有 store、每個 service 自己 repository  |
| [9.C7 Lyft 100+ microservice](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/)      | 微服務私有 DB、跨 service 不直接 DB query              |
| [9.C20 Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/)                  | TiDB → DynamoDB、repository adapter 是換 DB 的關鍵抽象 |

## 案例回寫

adapter 邊界可用 [3.C9 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 的資料一致性段落回寫。若事件中出現同一錯誤在不同路徑被不同方式處理、通常代表 adapter 的錯誤翻譯與契約分層不足。

這個案例主要支撐的是「錯誤分類與契約映射」判讀、不直接支撐 broker delivery 參數調整；若根因在 ack/retry 節奏、應回到 3.1/3.2。

回寫步驟是先盤點錯誤分類、再對齊重試與回退決策、最後把分類結果映射到 [6.10 Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/) 的驗證欄位、讓發版前可先發現漂移。

## 跨模組路由

1. 與 1.2 的交接：欄位與索引語意回到 [schema design 與資料建模](/backend/01-database/schema-design/)。
2. 與 1.3 的交接：交易錯誤與重試語意回到 [transaction 與一致性邊界](/backend/01-database/transaction-boundary/)。
3. 與 1.12 的交接：cross-DB migration 時、repository 是 *關鍵抽象* — 詳見 [大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)。
4. 與 6.10 的交接：跨服務契約一致性回到 [Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)。
5. 與 8.19 的交接：資料層錯誤判斷與回退決策回到 [Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

## 下一步路由

- 平行：[1.2 Schema Design](/backend/01-database/schema-design/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/) / [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)
- 跨模組：[6.10 Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/) / [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 跨 vendor adapter 深入：[DynamoDB single-table design](/backend/01-database/vendors/dynamodb/single-table-design-pattern/)（document KV adapter 邊界）、[MongoDB schema design pattern](/backend/01-database/vendors/mongodb/schema-design-pattern/)（document adapter 的 ODM 取捨）、[Cosmos DB MongoDB API vs SQL API](/backend/01-database/vendors/cosmosdb/mongodb-api-vs-sql-api/)（multi-API adapter 取捨）
