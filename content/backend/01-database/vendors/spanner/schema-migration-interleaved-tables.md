---
title: "Spanner Schema Migration Without Downtime + Interleaved Tables"
date: 2026-05-27
description: "Spanner DDL 是 long-running operation、用 TrueTime 給每次 schema change 分配 version timestamp、所有 read / write 對應自己 transaction timestamp 看到對應 schema。Interleaved table 是 storage-level parent-child 物理交錯、不是 logical FK。本文走 schema change lifecycle、interleaved layout 機制、backfill capacity 影響、5 production 踩雷、跟 PostgreSQL online schema change 對照"
weight: 32
tags: ["backend", "database", "spanner", "global-sql", "schema-migration", "interleaved-tables", "ddl", "deep-article"]
---

> 本文是 [Cloud Spanner](/backend/01-database/vendors/spanner/) overview 的 implementation-layer deep article。Overview 已說明 Spanner 在全球 OLTP 譜系的定位、本文聚焦 *schema migration without downtime + interleaved tables* — Spanner 兩個跟傳統 SQL 差異最大的 schema 機制。

---

## 問題情境：DDL 不停機跟 parent-child 物理 layout 的兩個疑問

傳統 PostgreSQL / MySQL DDL 拿 ACCESS EXCLUSIVE / metadata lock、線上跑 ALTER TABLE 動輒鎖表幾分鐘、大型 schema change 要 pt-osc / gh-ost / pg_repack 等外掛工具。Spanner 宣稱「schema change 不停機」、但團隊不知道實際機制跟邊界。讀者徵兆通常從這幾個地方浮現：「Spanner ALTER 真的不卡寫入嗎」「INDEX backfill 跑了 12 小時是正常嗎」「parent-child 的 INTERLEAVE IN PARENT 是什麼黑魔法」「ON DELETE CASCADE 在 interleaved table 為什麼是 storage-level 而不是 application-level」。

真實壓力：multi-tenant SaaS 要對 100 億 row 的 orders 表加 column + 加 index、不能停機、不能讓 p99 write latency 超過 SLA。團隊以為「Spanner schema change 不停機」等同於「DDL 瞬間完成」、實際 ALTER 是 long-running operation、index backfill 在大表上跑數小時到數天、capacity 規劃要把 backfill 期間的 CPU 升幅算進去。

Case anchor：**缺案例**。9.C10 是 Google internal dogfood case、未展開 schema migration 細節、且 9.C10 不是 customer-facing capacity reference。本文用通用 pattern + 官方文件 + 反向回 [PostgreSQL Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/) 對照、待後續 customer case audit 補強。

## 核心機制：DDL 是 long-running、TrueTime 對齊 schema version

### Schema change 的 lifecycle

Spanner DDL 不是同步 ALTER、是 *long-running operation*。TrueTime 給每次 schema change 分配一個 version timestamp、所有 read / write 用各自 transaction timestamp 對應「當下看到哪個 schema version」。讀者要理解的核心是：DDL 不是「鎖表→改→解鎖」、是「廣播新 schema version、讓現有 transaction 用舊 schema、新 transaction 用新 schema、背景 backfill 物理資料」。

```text
時間軸：

T0 (DDL 開始)
     |
     | ──── 舊 schema 仍可用、新 schema metadata 廣播 ────
     |
T1 (metadata 完成)
     |
     | ──── 新 transaction 用新 schema、舊 transaction 完成自己 ────
     | ──── backfill 開始（背景）────
     |
T2 (backfill 完成)
     |
     | ──── 新 schema fully serve ────
```

DDL 本身瞬間完成的部分是 *metadata 廣播*（毫秒到秒級）、慢的部分是 *backfill*（依資料量、可能數小時到數天）。讀者常見誤解是把 metadata 完成當「DDL 完成」、實際 query 還沒走新 index 因為 backfill 沒跑完。

### 不停機的關鍵：不同 DDL 的兩階段行為

| DDL 類型                    | metadata 行為                                             | backfill 行為                                          | 阻塞？                                  |
| --------------------------- | --------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------- |
| `ADD COLUMN`（無 NOT NULL） | metadata-only、瞬間生效                                   | 不需 backfill（新 column 預設 NULL）                   | 不阻塞 write                            |
| `ADD COLUMN`（NOT NULL）    | 必須兩階段：先 ADD COLUMN with default、後 ADD CONSTRAINT | 兩階段間需 backfill default                            | 不阻塞 write、但兩階段不能合            |
| `CREATE INDEX`              | metadata 立即                                             | 背景 backfill、不阻塞 write；backfill 完才 serve query | 不阻塞 write、阻塞「該 index 的 query」 |
| `DROP COLUMN`               | metadata 立即                                             | 背景 GC dead column                                    | 不阻塞                                  |
| `ALTER COLUMN TYPE`         | 限制多、查最新文件                                        | -                                                      | -                                       |

讀者要記的是：**index backfill 完成前、query 該 index 會 fallback 到 table scan**、用 `EXPLAIN` 確認 query plan 走新 index 才算真正完成。沒做這層驗證、團隊會以為 CREATE INDEX 已經成功、實際 p99 query latency 還在表掃描的數量級。

### Interleaved table 的設計

parent table（如 `Customer`）跟 child table（如 `Order`）的 row 在 storage 層 *物理上交錯儲存* — child row 跟對應 parent row 在同一個 split。不是純 foreign key、是 storage layout：

```text
傳統 PostgreSQL FK 設計（兩張獨立表）：
Customer table:  [c1, c2, c3, ...]  → 一張表、一段 storage range
Order table:     [o1, o2, o3, ...]  → 另一張表、另一段 storage range
FK 由 planner 在 JOIN 時拼接、可能跨 page / 跨 segment

Spanner Interleaved 設計（物理交錯）：
Storage layout: [c1, c1.o1, c1.o2, c2, c2.o1, c2.o2, c2.o3, c3, ...]
                 |____________________|  |________________|
                  c1 + 其 child           c2 + 其 child
                  在同一個 split          在同一個 split
```

Interleaved 的效果：parent + child JOIN 在同一個 split 完成、不跨 split = 不跨 Paxos group = 低延遲 transaction。這條設計把「FK 是 logical constraint」翻成「parent-child access pattern 是 physical co-location」、對 access pattern 固定的 workload（customer → orders、user → posts、tenant → records）是巨大 latency benefit。

### Interleaved 的硬限

| 限制                                   | 影響                                          |
| -------------------------------------- | --------------------------------------------- |
| 必須以 parent primary key 為 prefix    | child PK 第一段必須是 parent PK、不能完全自由 |
| 最深 7 層                              | 深巢狀關係要選層級                            |
| `ON DELETE` 只能 CASCADE 或 NO ACTION  | 不像 PG FK 有 SET NULL / SET DEFAULT          |
| 一旦建立、無法直接 ALTER 改 interleave | 要改 → export + recreate + import、不是 ALTER |

最後一條是讀者最容易踩的雷 — 一開始沒設 interleaved、後悔時要 export-import 100 億 row、是大工程、不是 ALTER。Schema 設計階段要先 audit access pattern、決定哪些 parent-child 該 interleave。

### 跟通用 FK 概念的差異

PostgreSQL FK 是 logical constraint、JOIN 由 planner 處理；Spanner interleaved 是 physical layout、JOIN cost 跟 single-table access 接近。對應 [transaction-boundary](/backend/knowledge-cards/transaction-boundary/) 卡 — interleaved 讓 transaction boundary 跟 storage boundary 對齊、跨 split transaction 變少、commit wait + Paxos round-trip 也省。

## 操作流程：DDL 跟 interleaved table 的具體步驟

### 加 column

```sql
ALTER TABLE Orders ADD COLUMN tax_amount FLOAT64;
```

執行後拿 long-running operation id、用 `gcloud spanner operations list` 觀察狀態：

```bash
gcloud spanner operations list --instance=prod --database=app
gcloud spanner operations describe projects/.../operations/<op-id>
```

驗證點：operation 顯示 `done: true` 後、跑 `SELECT tax_amount FROM Orders LIMIT 1` 確認 column 可查。

### 加 index

```sql
CREATE INDEX OrdersByCustomer ON Orders(customer_id);
```

拿 operation id → 用 Monitoring metric `spanner.googleapis.com/instance/indexes/backfill_progress`（或對應的最新 metric、查官方文件）追蹤進度。Backfill 完成前 query 不會走新 index、要用 `EXPLAIN` 確認：

```sql
EXPLAIN SELECT * FROM Orders WHERE customer_id = 'c123';
-- 應看到 plan 用 OrdersByCustomer index、不是 table scan
```

### 創建 interleaved table

```sql
CREATE TABLE `Order` (
    customer_id INT64 NOT NULL,
    order_id INT64 NOT NULL,
    amount FLOAT64,
    created_at TIMESTAMP,
) PRIMARY KEY (customer_id, order_id),
  INTERLEAVE IN PARENT Customer ON DELETE CASCADE;
```

關鍵約束：

- child PK `(customer_id, order_id)` 第一段是 parent PK
- `ON DELETE CASCADE` 是 storage-level — 刪 parent row 自動刪 child row、Spanner 內部處理、不是 trigger

### 從 non-interleaved 改成 interleaved

*無法直接 ALTER*、要走 export-recreate-import：

1. 用 Dataflow / `gcloud spanner databases export` 把舊表 export 到 GCS
2. 建新表（interleaved schema）
3. 用 Dataflow / `gcloud spanner databases import` 把資料倒回
4. 應用層 cutover（feature flag / dual write）

這個流程基本上是 mini-migration、要走完整 [migration playbook](../migrate-from-cloud-sql-pg/) 的 phase plan。Schema 設計階段就決定好 interleave、避免後悔成本。

### Rollback boundary

DDL 完成前可 `gcloud spanner operations cancel` 取消；完成後加 index 要 DROP、加 column 要 DROP COLUMN（同樣是 long-running）。讀者要先確認自己在 DDL 哪個階段、cancel 跟 reverse DDL 是兩條不同路徑。

## 失敗模式：5 個 production 踩雷

### Backfill 時間沒估、event window 撞牆

100 億 row 加 index、預期 1 小時、實際 12 小時 — 沒先用 `cost` 估 + 沒監控進度 metric。事故場景：團隊在 black friday 前一週開 CREATE INDEX、以為週末跑完、實際週末仍在 backfill、event 期間 CPU 升、query latency 退化。

修法：

- DDL 前用小表 benchmark backfill 速度（rows/sec）、推估大表時間
- DDL 期間監控 `instance/cpu/smoothed_utilization`、若 > 80% 暫停或降流量
- 大 DDL 排在 capacity headroom 充足的時段、避開 event window

### Interleaved table 一開始沒設、後悔時要 recreate

100 億 row export-import + cutover 是大工程、不是 ALTER。事故場景：團隊一開始把 Customer / Order 設成獨立表、上線一年後發現 customer → orders access pattern 是 99% 的 query、JOIN 跨 split 付 commit wait + Paxos cost、想改 interleaved、發現要 mini-migration。

修法：

- Schema 設計階段就 audit access pattern、決定哪些 parent-child 該 interleave
- 寫 ADR 把 interleave 決策跟業務 access pattern 綁定、避免後悔成本

### 把 interleaved 跟 FK 混為一談

interleaved 的 `ON DELETE CASCADE` 是 storage-level、刪 parent 自動刪 child；非 interleaved FK 要 application 或 trigger 處理。事故場景：團隊以為「我加了 FK 就會 CASCADE」、實際非 interleaved table 只是 constraint check、刪 parent 時 child orphan、對帳爆炸。

修法：

- Schema 設計時明確分類：interleaved（storage-level CASCADE）vs FK constraint（只檢查、不 CASCADE）
- 非 interleaved 的 parent-child 刪除邏輯放應用層、寫入對帳測試

### 加 NOT NULL 一步到位

直接 `ALTER ADD COLUMN x INT64 NOT NULL` 會失敗、必須兩階段。事故場景：開發環境 schema 是新建空表、`ADD COLUMN NOT NULL` OK；production 表有資料、ADD 失敗、團隊以為 Spanner 不支援、回退。

修法：

```sql
-- Phase 1: ADD with default
ALTER TABLE Orders ADD COLUMN tax_amount FLOAT64 DEFAULT 0;
-- 等 backfill 完成

-- Phase 2: ADD CONSTRAINT
ALTER TABLE Orders ALTER COLUMN tax_amount SET NOT NULL;
```

### Schema change 期間舊 client 還在用舊 schema

TrueTime 保證 read 看到自己 timestamp 對應的 schema version、但 client SDK cache schema 過期會 retry — 沒處理會看到 transient error。事故場景：DDL 完成後、舊 client session 看到 transient `FAILED_PRECONDITION`、團隊以為 DDL 失敗、回退。

修法：

- 應用層處理 transient retry（指數退避）
- DDL 完成後重新 deploy app instance、避免長期 stale schema cache

## 容量與觀測：Backfill 是 CPU + I/O 的額外負載

必看 metric：

```text
spanner.googleapis.com/instance/cpu/smoothed_utilization
   → backfill 期間 CPU 升幅、判讀是否撞 headroom
api/api_request_count for ExecuteSql
   → application traffic 是否受 backfill 影響
long-running operation API progress
   → DDL 自身進度（不是 query 進度）
```

Backfill 期間的 capacity impact：DDL 跑在 background priority、但仍佔 CPU、需要在 instance 有足夠 headroom（建議 < 65% CPU baseline 才開大 backfill）。capacity 規劃要把 schema migration 列入 buffer、回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)。

Observability evidence：backfill 開始 timestamp、operation id、predicted duration、實際 duration、CPU peak — 全進 incident decision log、回 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

監控盲點：DDL operation 失敗 silent fail 在 `gcloud operations describe` 才能看到、Cloud Monitoring 沒有直接 alert。團隊要寫自己的 polling script、operation 失敗時主動 alert、不靠 Cloud Monitoring default。

## 邊界與整合：何時不用 interleaved、怎麼跟 PG 對照

### 何時不用 interleaved

- 小 table（< 1M row、單機可放）：不需要 interleave、用 standard FK 就好
- 過度 interleave 7 層：把 split 變窄、反而 hot、得不償失
- access pattern 不是 parent-child JOIN：interleave 沒 benefit、純粹給 schema 加複雜度

### 跟 PostgreSQL 的對照

[PostgreSQL Online Schema Change](/backend/01-database/vendors/postgresql/online-schema-change/) 用 pg_repack / pt-osc workflow 模擬「不停機」 — 實際是用 trigger + 影子表 + cutover 把 lock 時間壓到秒級、不是真正瞬間。Spanner 是原生支援 DDL long-running operation、不需要外掛工具、但 backfill 時間在大表上仍長、跟 pg_repack 在大表上的執行時間量級接近。

差異點：

| 維度            | PostgreSQL（pg_repack / pt-osc） | Spanner                         |
| --------------- | -------------------------------- | ------------------------------- |
| Lock 時間       | 秒級（cutover 時短鎖）           | 毫秒（metadata 廣播）           |
| Backfill 時間   | 數小時                           | 數小時                          |
| 工具            | 外掛                             | 原生                            |
| Schema version  | 單版                             | TrueTime timestamp 對齊多版並存 |
| 大表加 NOT NULL | 一步到位（搭配 default）         | 必須兩階段                      |

讀者選 Spanner 不是為了「DDL 更快」、是為了「不依賴外掛 + 多版本並存」。實際在大表上的耗時兩邊差不多。

### Sibling deep articles

- [truetime-api-depth](../truetime-api-depth/)：schema version 也是 TrueTime timestamp、跟 transaction timestamp 同層機制
- [migrate-from-cloud-sql-pg](../migrate-from-cloud-sql-pg/)：target schema 設計含 interleaved、Phase 1 必讀本文
- [consistency-models-comparison](../consistency-models-comparison/)：schema change 期間多版本並存的一致性保證

### 跟 1.x 章節

[Schema Design](/backend/01-database/schema-design/) — interleaved 是 schema 設計的物理層決策、不是純 logical design。對照 [schema-migration-rollout-evidence](/backend/01-database/schema-migration-rollout-evidence/) 看 schema rollout 的 evidence 收集模式。

### Anti-recommendation

讀者讀完本文應該能判斷：interleaved 不是「強制使用」的 feature、是「access pattern 固定時的 latency benefit」。小規模 OLTP、access pattern 不確定的 workload、用 standard PostgreSQL FK 就好、為 interleaved 付 schema 後悔成本的判準很高。
