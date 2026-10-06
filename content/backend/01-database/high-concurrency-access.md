---
title: "1.1 高併發下的 SQL 讀寫邊界"
date: 2026-05-13
description: "說明高併發服務如何共用資料庫 client、控制 transaction、管理 connection pool、避免資料庫成為瓶頸"
weight: 1
tags: ["backend", "database"]
---

這篇整理高併發服務存取 SQL 資料庫時要控制的邊界：資料庫 client 與 [connection pool](/backend/knowledge-cards/connection-pool/)、交易範圍、hot row、read replica、查詢 timeout，以及什麼條件下該換掉 SQL。範圍從應用程式端的連線池開始，到資料庫端的 `max_connections` 與 replica 為止。

高併發服務處理 SQL 的核心原則是共用資料庫 client、讓 connection pool 管理連線生命週期。並發升高時要控制的是連線數、交易範圍、查詢時間與下游壓力；每個 request 各自建立連線會放大握手、排隊與資源回收成本。服務層的飽和判讀在 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 跟 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。

## 本章目標

學完本章後、讀者能夠：

1. 理解資料庫 client 為什麼應該共用
2. 分辨 query、exec、rows 與 [transaction](/backend/knowledge-cards/transaction/) 的不同邊界
3. 了解連線池參數對高併發的影響
4. 設計多層 connection pool 架構（app + middleware + DB）
5. 識別 hot row / lock contention 並選擇對策
6. 用 read replica 擴 read traffic、注意 replication lag
7. 用 `context` 與 [timeout](/backend/knowledge-cards/timeout/) 控制慢查詢
8. 判斷什麼情況該換 KV / 緩衝模式而非繼續硬擴 SQL

---

## 資料庫 client 通常代表連線池入口

多數後端語言的資料庫 client 都會包住連線池或連線管理能力。一般情況下、服務會在啟動時建立可重用的 [database](/backend/knowledge-cards/database/) handle、讓 request handler、worker 或 service layer 共用它、並在需要時從池子裡取出可用連線。

這種模型的好處是：

- 呼叫端不用自己管理每個連線的生命週期
- 多個 request 或 worker 可以同時發出資料庫操作
- 連線回收與重用由 client 內建的連線池處理（Go 的 `database/sql` 裡是 `sql.DB`）

## 高併發需要有界連線

高併發時的核心風險是把 application concurrency 誤解成 database concurrency。語言端的 thread、task、coroutine 或 goroutine 可能很容易建立、但資料庫有自己的容量上限；連線池只是把壓力從應用端平滑地送到下游、無法消滅壓力。

連線池調校的核心觀念，以 Go `database/sql` 的 `sql.DB` 設定為例（其他語言的 driver pool 有對應的參數）：

- `SetMaxOpenConns` 太低、request 會在應用端排隊。
- `SetMaxOpenConns` 太高、可能把 DB 直接打滿。
- `SetMaxIdleConns` 決定尖峰過後保留多少條閒置連線；留得太少，下一波請求要重新建立連線。
- `SetConnMaxLifetime` / `SetConnMaxIdleTime` 影響長連線與資源回收節奏。

### 第一個爆的通常是連線、不是 CPU 或 disk

SQL DB 在 surge 場景的 *first bottleneck* 不是 CPU、也不是 disk I/O、是 *連線數量*。原因：傳統 RDB（PostgreSQL、MySQL）每個連線吃記憶體 + 一個 process / thread，資料庫端的連線上限 `max_connections` 因此設不高（PostgreSQL 預設 100、MySQL 預設 151，實務設定值見下方〈Database 端 max_connections〉）。流量湧入時、application 想開更多連線、DB 直接拒絕（PostgreSQL：`FATAL: too many connections`）、看起來像 DB 故障、實際是連線數限制。

對應 [Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — NTT DOCOMO 串流平台選 DynamoDB 而非 RDB 的原因之一是「connection limit 在快速流量增加時變成 bottleneck」。DynamoDB 的 HTTP API 模型沒有 connection state、天然解決這個瓶頸。

**判讀順序**：surge 期間 DB 看起來慢，先比對目前連線數與 `max_connections`，再看 CPU / disk：

```sql
-- PostgreSQL：各狀態的 client 連線數，與上限比對
SELECT state, count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' GROUP BY state;
SHOW max_connections;

-- MySQL：目前連線數與上限
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
```

連線數已經貼著上限時，再加 CPU 沒用；要加 middleware pool（pgBouncer / ProxySQL）或換 HTTP-based DB。

## 多層 Connection Pool 架構

實務上 production-grade 服務的 connection pool 通常分三層：

### Application pool（每個 instance 內）

- 每個 application instance 維護自己的 driver-level pool
- 典型大小：30-50 connection / instance
- 工具：HikariCP（Java）、SQLAlchemy pool（Python）、`sql.DB`（Go）
- 一個 instance 跑多個 worker 程序（例如 gunicorn）時，每個程序各一個池，總數要乘上 worker 數；PHP-FPM 沒有程序內的池，連線數跟 worker 數走，見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈各語言執行模型下的連線模型〉

### Middleware pool（共享層）

- PostgreSQL：[pgBouncer](https://www.pgbouncer.org/)（最常見、transaction pooling）、[PgCat](https://github.com/postgresml/pgcat)（rust、支援 sharding）
- MySQL：[ProxySQL](https://proxysql.com/)（query routing + pool）
- 為什麼需要：多個 application instance 同時打 DB、總 connection 數會爆
- pgBouncer 把 1000 application connection mux 到 50 個 DB connection、應用感覺有 1000 connection、DB 只看到 50

### Database 端 max_connections

- PostgreSQL default 100、實務常設 200-500
- MySQL default 151、實務常設 1000-5000
- 每個 connection 吃記憶體（PG ~10MB、MySQL ~3MB）、設太高會 OOM

**典型配置範例**（中型網路服務）：

```text
50 application instance × 30 connection (app pool)                 = 1500 條 client 連線
  → pgBouncer transaction pool (4 instance × 45 server connection) = 180 條 DB 連線
  → PostgreSQL primary (max_connections = 200)                     剩 20 條留給維運連線
```

1500 條 application connection 經 pgBouncer 收成 180 條 DB connection，約 8 倍 multiplexing。

**反模式**：

- 跳過 middleware pool、application 直連 DB
- 應用 instance 50 個 × 30 connection = 1500 connection、PostgreSQL 直接拒絕

對應 [Lemino case](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 是 surge 場景的隱性 bottleneck、Lemino 選擇遷移到 DynamoDB 而不是擴 connection pool（因為 HTTP-based KV 沒這個問題）。

### Query 反模式如何放大連線池壓力

連線池被占滿的根本原因不只是「連線數不夠」、還有「單一連線被占用的時間太長」。Query 反模式直接放大每筆 request 的連線占用時間：

- **N+1 query** 讓一個 request 占用連線從 1 個 round trip 拉長到 N+1 個。同樣的 throughput、需要 N+1 倍的連線數來 sustain
- **Long-running transaction** 把一個連線從幾毫秒占用變成幾秒，相當於把連線池的有效容量除以幾百倍
- **缺索引的 query** 在熱表上跑 full scan、單筆 query 從 10ms 變成 1-5 秒、連線占用時間放大兩個數量級
- **`SELECT *` 載入大欄位**：reader 在反序列化大物件期間連線一直 hold、不是 query 本身慢、是 serialization overhead 拉長占用

這些反模式單獨看是「query 寫法問題」、但放到連線池語境就是「連線池容量被間接削減」。先用 [1.13 query 反模式](/backend/01-database/query-anti-patterns/) 的清單收回連線占用時間、再考慮加 [9.14 connection pooler](/backend/09-performance-capacity/connection-pool-amplification/) 中介層 — 順序顛倒會讓 pooler 治標不治本。

## 讀取與寫入要分開看

讀取的核心風險通常是慢查詢、掃描過大、N+1、熱點資料與連線被占住太久。寫入的核心風險則常常是 transaction 太大、衝突太高、鎖時間太長、重試邏輯不清楚。

### 讀取

- 用索引支援常見查詢條件。
- 避免一次載入過多資料。
- 需要分頁時、先考慮接續標記（cursor）或穩定排序。
- 熱讀資料可以在上層加 cache、同時保留資料庫作為正式狀態來源。

### 寫入

- transaction 只包住真正需要一致性的範圍。
- transaction 範圍只保留必要資料操作、外部 API 呼叫、使用者等待或長迴圈應放在交易外。
- 高衝突寫入要搭配重試、唯一鍵或明確去重策略。
- 需要高吞吐時、先評估批次化、分段處理與有界並發。

詳見 [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/) 對 transaction 設計的深度討論。

## Hot Row / Lock Contention 識別與處理

當多個 request 同時想 update 同一筆資料、會在 DB 層出現 lock contention。這跟 KV 的 [hot partition](/backend/knowledge-cards/hot-partition/) 是同類問題、但 *機制不同*。

**典型 hot row 場景**：

- inventory counter：所有用戶搶同一個 product 庫存
- counter / metrics：實時計數器（view count、like count）
- queue / job ledger：所有 worker 競爭同一個 job table
- session：高頻 session 更新

**識別訊號**：整體 QPS 沒滿、但某些 endpoint p99 飆，而資料庫端看得到大量在等鎖的 session：

```sql
-- PostgreSQL：正在等鎖的 session，以及擋住它的 pid
SELECT pid, pg_blocking_pids(pid) AS blocked_by, wait_event_type, wait_event, query
FROM pg_stat_activity WHERE wait_event_type = 'Lock';
--  pid | blocked_by | wait_event_type | wait_event    | query
--  134 | {128}      | Lock            | transactionid | UPDATE products SET stock = stock - 1 WHERE id = 7;

-- MySQL 8.4：InnoDB 的列鎖等待
SELECT waiting_pid, waiting_query, blocking_pid FROM sys.innodb_lock_waits;
--  waiting_pid | waiting_query                                      | blocking_pid
--           23 | UPDATE products SET stock = stock - 1 WHERE id = 7 |           22
```

MySQL 的 `SHOW PROCESSLIST` 對等列鎖的 session 顯示的狀態是 `updating`，從那裡看不出它在等鎖；`INFORMATION_SCHEMA.INNODB_LOCK_WAITS` 在 MySQL 8.4 已經不存在，查詢會回 `Unknown table`。

**對策**：

**分散熱點**：

- counter shard：把 1 個 counter 拆成 N 列 sub-counter，寫入時由應用程式隨機挑一列加一、讀取時把 N 列加總。拆成 10 列時，同時寫入的 request 分散到 10 列上，10 倍是寫入吞吐的上限（實測只有數倍，見 1.18）

  ```sql
  CREATE TABLE view_counter (
    item_id INTEGER, shard INTEGER, cnt INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, shard)
  );
  -- 每個 item 先建 10 列，shard 0-9
  INSERT INTO view_counter (item_id, shard) VALUES
    (42, 0), (42, 1), (42, 2), (42, 3), (42, 4), (42, 5), (42, 6), (42, 7), (42, 8), (42, 9);

  -- 寫入：shard 由應用程式在 0-9 隨機挑好再帶進來
  UPDATE view_counter SET cnt = cnt + 1 WHERE item_id = 42 AND shard = 3;
  UPDATE view_counter SET cnt = cnt + 1 WHERE item_id = 42 AND shard = 7;
  UPDATE view_counter SET cnt = cnt + 1 WHERE item_id = 42 AND shard = 3;

  -- 讀取：10 列加總
  SELECT SUM(cnt) FROM view_counter WHERE item_id = 42;  -- 3
  ```

- 對應 [Hot Partition 卡片](/backend/knowledge-cards/hot-partition/) 在 SQL DB 的對應做法

**Asynchronous batching**：

- 不要每次點擊就 update counter、先進 in-memory buffer、定期 flush
- 應用層 Redis INCR + 定期同步回 SQL

熱點列的吞吐量為什麼受提交寫盤的時間限制、加開連線只會放大延遲，以及改成只新增事件再彙總時要處理的漏算、重複計算與彙總排程的互斥，見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)。

**Optimistic concurrency control**：讀的時候記下 `version`，寫的時候只在 `version` 沒被別人改過時才更新，並把 `version` 加一；更新到零列就代表有人先寫了，應用層重讀再 retry。這個做法不用 `SELECT ... FOR UPDATE` 先鎖住那一列。

```sql
-- 兩個 request 都讀到 stock = 10、version = 3
SELECT stock, version FROM products WHERE id = 7;

-- 先到的 request：更新成功，影響 1 列
UPDATE products SET stock = stock - 1, version = version + 1 WHERE id = 7 AND version = 3;

-- 後到的 request：version 已經是 4，影響 0 列 → 重讀後 retry
UPDATE products SET stock = stock - 1, version = version + 1 WHERE id = 7 AND version = 3;
```

**換 KV / cache**：

- counter workload 本來就不適合 SQL transaction
- 用 Redis INCR、DynamoDB 的 atomic counter

**Queue + worker 序列化**：

- 把搶資源的 request 排隊、worker 序列化處理
- 對應 [Tixcraft 案例](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 售票把 inventory 搶購塞進 DynamoDB queue、legacy server 慢慢消費、避免 SQL hot row

## Read Replica Scaling

當 read traffic 超過 primary 吞吐、用 read replica 擴 read。

**Read replica 機制**：

- PostgreSQL：streaming replication（async / sync）
- MySQL：async replication（binlog）
- Aurora：storage-level replication（lag 10-30ms）

**Routing 策略**：

**Read / write split（application-level）**：

- 應用層判斷 query 類型、寫走 primary、讀走 replica
- 工具：application 自管（各框架的路由規則見 [1.17 應用程式存取資料庫的工具分層](/backend/01-database/data-access-layers/)〈讀寫分離與多個資料庫：連線的路由由哪一層決定〉）

**Routing 自動化（middleware）**：

- ProxySQL（MySQL，依 SQL 文字比對規則分流）、Pgpool-II（PostgreSQL）；PgBouncer 只做連線池，不依 SQL 內容分流讀寫
- HAProxy + health check

**Stale read 容忍策略**：

- 「能容忍秒級 stale」的 read → replica（用戶 profile、報表）
- 「不能 stale」的 read → primary（剛寫入後的查詢、餘額確認）
- [read-after-write consistency](/backend/knowledge-cards/read-after-write/)：用 session token 標記「剛寫過」、N 秒內讀走 primary

**Replication lag 監控**：

- PostgreSQL：`pg_stat_replication.replay_lag`
- MySQL 8.4：`SHOW REPLICA STATUS\G` 的 `Seconds_Behind_Source`
- Aurora：CloudWatch `AuroraReplicaLag`
- 對應案例：[DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — replication lag 從 30 秒降到 10-30ms、是切換到 Aurora 的關鍵改善

**注意事項**：

- replica 數量不是無限、Aurora 最多 15 個、PostgreSQL 通常 3-5 個（chain replication 更多但複雜）
- 跨 region replica 通常 async、不能保證 read-after-write
- 對應 [FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) Super Bowl 5-10x peak、需要動態加 replica

### 儲存層 replication vs compute 層 replication

Aurora / Cosmos DB / Spanner 的 replication 跟傳統 PostgreSQL streaming replication 是兩種本質不同的設計、決定 read replica 怎麼擴、replication lag 落在什麼量級、容量規劃要顧哪些瓶頸。

**傳統 RDB（compute 層 replication）**：

- primary 寫入後、把 WAL / binlog 流到 replica
- replica 自己 replay log、消耗 CPU 跟 disk
- primary 寫入量大、replica 跟不上、replication lag 飆
- 加 replica 增加 primary 的 *replication 負擔*、不能無限加

**Aurora / Cosmos DB（storage 層 replication）**：

- compute 跟 storage 分離、storage 是分散式 log-based
- replication 在 *storage 層* 處理、不經過 compute
- replica 不用自己 replay、直接讀同一份 storage
- 加 read replica 不增加 primary 寫入負擔
- replication lag 從 30 秒級降到 10-30ms（Aurora）

**儲存層與 compute 層 replication 的差異為什麼反映到應用層設計**：compute 層 replication 的 replication lag 通常在秒級、應用層必須處理「剛寫的資料 N 秒內讀不到」的情境 — 常見補丁是 read-after-write consistency（session token 標記「剛寫過」、N 秒內走 primary）、cache invalidation 延遲、或刻意走 primary 的關鍵查詢路徑。Storage 層 replication 的 lag 在毫秒級，cache invalidation 延遲這類補丁可以大幅簡化；lag 仍然不是零，剛寫入就要讀到的查詢（餘額確認）照樣要走 primary 或帶 freshness token。對應 [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 從 30 秒到 10-30ms 不只是「快」、是讓整個應用層 cache invalidation 跟 session routing 邏輯大幅簡化。對應 [Netflix Aurora consolidation](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — Aurora 75% performance improvement 主要來自 storage layer 設計、不是 CPU 改善。

**選型含義**：如果應用層有大量「秒級 stale 會出錯、毫秒級可以接受」的讀取、storage 層 replication 比 compute 層 replication 大幅簡化設計；嚴格的 read-after-write（餘額確認、剛寫的查詢）在兩種設計下都要另外處理。代價是 vendor lock-in 加深、應用層綁定特定雲商。

對應 [Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) 跟 Aurora 是同類設計（log-structured 分散式 storage）、選哪家看 application 已在哪個 cloud、技術哲學一致。Sharding 觸發點（managed DB 容量上限）跟業務一致性需求決定 sharding 粒度的討論、見 [1.11 Sharding 粒度跟業務一致性需求](/backend/01-database/global-distributed-oltp/)。

## 查詢與 rows 的生命週期要收乾淨

查詢回傳 rows 後、呼叫端要負責把它關掉、並檢查迭代錯誤。這不只是記憶體管理問題、也會影響連線何時能回到池子裡。

典型模式是：

```go
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users WHERE status = ?", status)
if err != nil {
    return err
}
defer rows.Close()

for rows.Next() {
    var id int64
    var name string
    if err := rows.Scan(&id, &name); err != nil {
        return err
    }
}
if err := rows.Err(); err != nil {
    return err
}
```

## 慢查詢要靠 timeout 與上層限流處理

在高併發服務裡、database timeout 應由 request timeout、client timeout 與資料庫 timeout 共同定義。語言端需要能把取消、[deadline](/backend/knowledge-cards/deadline/) 或 timeout 往資料庫 client 傳遞、讓慢查詢在合理時間內釋放資源。

如果下游開始變慢、通常要搭配：

- request-level timeout
- [worker pool](/backend/knowledge-cards/worker-pool/) 或 semaphore
- [queue](/backend/knowledge-cards/queue/) 長度限制
- 降級或拒絕策略

這樣做的目標是避免應用自己堆出大量等待中的工作、最後把問題放大成整個服務卡死。

## 什麼時候該換 KV / 緩衝模式而非繼續硬擴 SQL

SQL 的 transactional 模型有結構性限制、超過某個規模硬擴 SQL 不如換工具。

**換工具的訊號**：

1. **Connection saturate 但 CPU / RAM 還閒**：connection 是 SQL 的早期 bottleneck。對應 [Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — RDB connection limit 是 surge 場景的瓶頸、換 DynamoDB（HTTP-based、無 connection 概念）解決。

2. **Hot row contention 無法分散**：應用層改不了 schema、無法把 counter shard、SQL 就是 contention 源頭。換 Redis atomic counter / DynamoDB atomic update。

3. **Write throughput > 50K WPS 單機**：sharding 工程成本變高、不如換 KV 或分散式 SQL。詳見 [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) 或 [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)。

4. **Flash-sale spiky workload**：用 SQL 接搶購、connection 跟 lock 都會爆。對應 [Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 用 DynamoDB 當 durable queue、legacy SQL 慢慢消費。

5. **跨 region 強一致 OLTP**：傳統 PostgreSQL / MySQL 跨 region 是 async、滿足不了強一致。換 Spanner / Aurora DSQL / CockroachDB（[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)）。

不要因為「現在 SQL 慢」就跳結論換 NoSQL — 先確認問題是 *結構性的*（connection、contention、跨 region）、不只是 *調校問題*（index、query、cache）。

## 語言端的責任：共用 client、控制並發、縮小交易、傳遞 timeout

這一章不討論 PostgreSQL、MySQL、SQLite 的語法差異、也不討論 [migration](/backend/knowledge-cards/migration/) 工具本身。語言端需要掌握的是：怎麼共用 database client、怎麼控制並發、怎麼縮小 transaction、怎麼把 timeout 和取消傳下去。

具體 schema、index、[isolation level](/backend/knowledge-cards/isolation-level/) 與 migration 寫法、會放在這個模組的其他資料庫教材中。

## 案例對照

| 案例                                                                                                            | 高併發場景重點                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [AWS Prime Day 2025](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)                  | DynamoDB 1.51 億 RPS + Aurora 5000 億 txn、可預期峰值的 [dogfood baseline](/backend/01-database/large-scale-db-migration/)（vendor 自家 production-critical workload 是 selection signal） |
| [DraftKings Aurora](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/)                 | 1M ops/min、200 個獨立 cluster、replication lag 30s → 10-30ms                                                                                                                              |
| [Standard Chartered Aurora](/backend/09-performance-capacity/cases/standard-chartered-aurora-banking/)          | 4000 TPS、7 個受監管市場、各自獨立 cluster                                                                                                                                                 |
| [Netflix Aurora](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/)                          | DB 統一後 +75% 效能、storage / compute 分離釋放 read replica                                                                                                                               |
| [FanDuel](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)                          | Super Bowl 5-10x peak、Aurora MySQL + read replica scaling                                                                                                                                 |
| [Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)                          | RDB connection limit 是 surge 瓶頸、改用 DynamoDB                                                                                                                                          |
| [Clearent Azure SQL Hyperscale](/backend/09-performance-capacity/cases/clearent-azure-sql-hyperscale-payments/) | 5 億 txn/年、storage / compute 分離跟 Aurora 同類設計                                                                                                                                      |

[Prime Day](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) 是高併發章節的 *上限參考點*：Amazon 自家 Prime Day 在 24 小時內、DynamoDB 服務 1.51 億 RPS 毫秒級回應、Aurora 處理 5000 億次 transaction。這份數字的意義不是「要達到這個量級」、而是給定 *可預期峰值* 跟 *無限預算* 時、AWS 自家服務的設計上限長這樣。讀本章其他內部 baseline（connection pool、replica lag、isolation level）時、要記得最終物理上限遠高於大部分服務日常會碰到的水位。

## 跨語言適配評估

資料庫高併發邊界會受語言 runtime 影響。Thread-based runtime 要管理 thread pool 與 connection pool 的比例；async runtime 要確認 database driver 是否真正非阻塞（很多老 driver 只是包了 sync 在 thread pool 上、會吃 thread limit）；輕量 task runtime（Go、Erlang）要限制同時查詢數量、避免把大量 task 轉成下游連線壓力。強型別語言可以用型別保護 row mapping 與錯誤分類；動態語言則需要用 migration、runtime validation、[contract](/backend/knowledge-cards/contract/) test 與 fixture 保護 schema 邊界。

## 小結

高併發下處理 SQL 的核心原則：

1. **database client 共用**、不要每 request 新建
2. **連線池可控** — 三層架構（app pool + middleware + DB max_connections）
3. **transaction 要短** — 詳見 [1.3 Transaction 與一致性邊界](/backend/01-database/transaction-boundary/)
4. **rows 要關**、避免連線被占住
5. **timeout 要傳遞** — 從 request 一路到 DB
6. **Hot row 要識別** — counter shard、optimistic concurrency、async batching、或換 KV
7. **Read replica 要會用** — 但注意 lag、[stale read](/backend/knowledge-cards/stale-read/) 容忍度
8. **下游壓力要限流** — request timeout、worker pool、queue 長度、降級拒絕
9. **知道什麼時候換工具** — connection saturation、hot contention、flash-sale、跨 region 強一致都是 SQL 結構性限制的訊號

應用端並發可以很多、但資料庫連線必須受控、這兩者的邊界要分開管理。

## 讀「峰值」數字的工程細節

容量規劃時看到「100 萬 ops/分鐘」、「150 萬 RPS」這類數字、要先分清它是最大瞬時、99 百分位還是常態流量、否則容量規劃會錯位。

### 容量數字的口徑：最大瞬時、99 百分位、常態流量

| 口徑      | 含義                   | 用於規劃                            |
| --------- | ---------------------- | ----------------------------------- |
| 最大瞬時  | 某一秒的最高峰（單秒） | 不能拿這個訂 baseline、是 outlier   |
| 99 百分位 | 99% 時間在這個水位以下 | 訂 capacity 上限的依據              |
| 常態流量  | 平均的日常水位         | 訂 cost baseline、auto-scaling 起點 |

**最大瞬時** 是觀測得到的最高峰值、通常是年度某秒、不能拿來訂 baseline。在 Grafana / CloudWatch / Datadog 上看 `max` 指標就是這個數字 — 用來知道系統 *曾經* 撐過多少、不是 *日常* 要撐多少。

**99 百分位** 是 capacity 規劃的主要依據：把過去 30 天或 90 天每一秒（或每一分鐘）的流量排序，第 99 百分位就是 99% 的時間流量低於的那個水位。監控圖上常見的 `p99` 多半是請求延遲的百分位，量的是耗時，這裡要的是流量的百分位，要另外算。Auto-scaling 上限通常訂在這個值的 1.5-2 倍、確保 99% 時間有足夠 headroom。

**常態流量** 是 average / median、訂 cost baseline 跟 auto-scaling 的下限。在 PaaS（Aurora Serverless、Cosmos DB serverless）這是「最低保留容量」的依據；在 IaaS 是「永遠開著的 instance 數量」。

[Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 揭露這個議題：「9000 萬 reads / 秒」通常是年度峰值最高一秒、不是平均。讀案例時要區分最大瞬時、99 百分位與常態流量、否則容量規劃會錯位。

對應 [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 「100 萬 ops/分鐘」≈ 17K ops/秒、跨 200 個獨立 cluster 平均下來每 DB 約 80 ops/秒。讀峰值要看 *分散到多少 shard*、不只看總數。

### 延遲改善要看 percentile、不是平均

「延遲降 90%」這類敘述要追問：是 p50 還是 p99？兩者改善幅度通常差很多、平均值會掩蓋尾巴問題。

對應 [Zomato](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 「90% 延遲降」實際可能是 p50、p99 / p999 改善幅度通常較小。判讀重點：用戶體驗主要受 *p99 / p999* 影響、不是 p50。看到「平均 50ms 降到 5ms」要追問「p99 從多少降到多少」、否則可能用戶感受沒改善。

延遲監控的必要 percentile：p50、p95、p99、p99.9。p99.9 是每 1000 個 request 裡最慢那一個所在的水位，代表系統接近最差的表現、是 SLO breach 的早期訊號。

## Headroom budget：事件型 vs 突發型峰值

Headroom budget 是 *提前預留的容量空間*、給可預期或不可預期的峰值用。讀「Super Bowl +50% no sweat」這種敘述、工程意義是團隊事前預留了 headroom、不是 vendor 神奇。

對應 [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — Super Bowl 是已知事件、+50% 是歷史經驗，所以這 50% 算進事件當天的目標容量、事前 scale-up 到位，再在目標容量上加事件型的 headroom、配合 read replica 動態加減，50% 的增幅才會「不流汗」。案例頁只寫了流量 +50% 而延遲不受影響，headroom 實際留了多少沒有公開。

兩種峰值的 headroom budget 規劃完全不同：

**事件型峰值**（已知時間 + 已知幅度）：

- 例：Super Bowl、Black Friday、票券開賣、財報日
- 規劃做法：歷史 peak × 預期成長 = 事件當天的目標容量，事件前 scheduled scale-up 到目標容量再加 headroom
- headroom 預算可以較低（20-30%）、因為峰值可預測、可在事件前測試
- 對應 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)

**突發型峰值**（未知時間或未知幅度）：

- 例：突發新聞、KOL 推廣、競爭對手出包導致流量湧入、病毒式擴散
- 規劃做法：常態 baseline 預留高 headroom（50-100%）、加 auto-scaling 跟動態 capacity
- headroom 預算要高、因為事故發生前沒時間 scale
- 對應 [GR8 Tech AI 預測式擴容](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)

判讀重點：事件型 headroom 適合可預測峰值、突發型 headroom 適合不可預測峰值；兩者預算邏輯不同。把事件型 headroom 套用在突發型場景、突發事件發生時容量會不足；把突發型的高 headroom 套用在事件型、會付大量浪費成本。

## 讀寫峰值錯位：dual peak workload

部分業務有 *讀峰值跟寫峰值不同時段* 的特性、容量規劃要讓讀 peak 與寫 peak 各自發生的時段都有足夠容量，而不是只看總流量曲線上的單一 peak。

對應 [DraftKings](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) — 「write workloads spike up significantly around payout events, but opening the app during the game also activates a lot of balance queries」。比賽進行時讀爆量（用戶看餘額、看下注狀態）、比賽結束 payout 時寫爆量（賠付寫進帳本）、兩個 peak 錯位。

容量規劃含義：

- 不能只規劃「讀 peak + 寫常態」或「寫 peak + 讀常態」
- 要規劃「讀 peak 跟寫 peak 各自的容量」、即使不同時發生、底層 DB 都要撐
- read replica 動態增減可以平滑讀 peak、但寫 peak 要靠 primary capacity 撐住

**類似 dual peak 業務**：

- 體育博彩：比賽中讀、payout 時寫（DraftKings）
- 票券：開賣前 30 分鐘讀爆量（用戶看座位）、開賣瞬間寫爆量（搶票）
- 電商促銷：促銷前讀爆量（用戶看價格）、促銷瞬間寫爆量（下單）
- 股票交易：開盤前讀爆量（看開盤價）、開盤瞬間寫爆量（送單）

判讀重點：dual peak workload 是業務 *天然* 特性、不是異常。容量規劃要識別這層、否則尖峰時段會踩到沒預期的瓶頸。

## 關鍵路徑切分：低頻流量保護

當系統有「高頻流量（如選位、瀏覽）」跟「低頻但關鍵流量（如付款、結算）」共存時、必須切分、否則高頻流量會塞爆低頻路徑、讓低頻關鍵業務無法完成。

對應 [Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 拓元把 Payment EC2 拉出來、直連傳統金流 server、不放在搶票流量會打到的 ELB / DB 後面。讓「選位 + 下單」的高頻流量塞爆時、「付款」的低頻流量仍能跑。

**切分策略**：

- **資料路徑切分**：高頻 query 走 DynamoDB / read replica、低頻關鍵 query 走 primary
- **連線池切分**：高頻 service 跟低頻 service 用不同 connection pool、避免高頻吃光連線
- **runtime 切分**：低頻關鍵 service 部署到獨立 instance、不跟高頻共用 CPU / memory
- **限流切分**：高頻 endpoint 設高限流、低頻關鍵 endpoint 設保護性低限流（避免 cascading failure）

判讀重點：切分前要先盤「哪些流量是業務關鍵但量小」、這些路徑要事先保護、不能等爆了再分開。

## 下一步路由

- 上游：[Connection Pool 卡片](/backend/knowledge-cards/connection-pool/)
- 上游：[1.13 應用層查詢反模式與 Query 預算](/backend/01-database/query-anti-patterns/)（connection saturation 常因 N+1 / long transaction 放大、先檢查 query 寫法）
- 平行：[1.2 Schema Design](/backend/01-database/schema-design/)、[1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)
- 下游：[1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/)（SQL 不夠用時的替代）/ [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) / [1.12 大規模 DB 遷移實戰](/backend/01-database/large-scale-db-migration/)（換 DB engine 的決策跟流程）
- 跨模組：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)、[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)、[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)、[9.13 擴展軸](/backend/09-performance-capacity/scaling-axes/)（hot row 是不可分散瓶頸的 application 層表現）
- Vendor：[PostgreSQL](/backend/01-database/vendors/postgresql/)、[MySQL](/backend/01-database/vendors/mysql/)、[Aurora](/backend/01-database/vendors/aurora/)
- [規模成長路線](/backend/scale-growth-walls/)下一站 → [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)（連線池 / replica 擴完後、進入應用層快取設計）
- MongoDB connection storm 深入：[MongoDB connection 管理與 cache 層](/backend/01-database/vendors/mongodb/connection-management-and-cache-layer/) / [replica set read preference](/backend/01-database/vendors/mongodb/replica-set-read-preference/)
- Aurora read replica 擴展：[Aurora read replica scaling](/backend/01-database/vendors/aurora/read-replica-scaling/)（reader endpoint / lag 治理）
- Freshness token 卡片：[Freshness Token](/backend/knowledge-cards/freshness-token/)（read-after-write 保證選項）
