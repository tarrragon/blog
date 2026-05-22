---
title: "MySQL Replication Topology：async / semi-sync / GTID 不是三選一、是三個 trade-off 軸的疊加"
date: 2026-05-19
description: "MySQL replication 不是「選 async 還是 semi-sync」、是 *durability / latency / consistency* 三個 trade-off 軸的疊加；GTID 是跨 mode 的 infrastructure layer、不是第三種 mode。本文走 3 軸取捨模型 → async / semi-sync 行為對比 → GTID 替代 binlog-position 的好處 → 配置 step-by-step → 5 production 踩雷（lag 暴衝 / semi-sync 退回 async / GTID gap / Loss-Less semi-sync 真的 loss-less / chained replication 雪崩）→ 跟 Aurora MySQL / Vitess / ProxySQL / Orchestrator 整合"
weight: 12
tags: ["backend", "database", "mysql", "replication", "gtid", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *replication topology* — 從 single primary 到 multi-replica 部署的 3 個 trade-off 軸跟 5 段配置。

---

## Replication 的 3 個 trade-off 軸 + mode 選擇

Replication mode 選擇看起來是「選 async 還是 semi-sync」、但決策實際是 3 個獨立 trade-off 軸的權衡、async / semi-sync 是這些軸的兩個常見組合 *名稱*：

| 軸              | 端 A                      | 端 B                              | MySQL 旋鈕                                             |
| --------------- | ------------------------- | --------------------------------- | ------------------------------------------------------ |
| **Durability**  | primary 寫完就 commit     | 至少一個 standby 收到才 commit    | `rpl_semi_sync_master_enabled` / sync ack count        |
| **Latency**     | client 等 primary 寫完 OK | client 等 standby ack（額外 RTT） | `rpl_semi_sync_master_timeout`                         |
| **Consistency** | replica 隨時可能 stale    | replica 跟 primary 保證讀到一致   | application read routing rule（不是 replication 旋鈕） |

「async vs semi-sync」實際上是 *durability + latency 兩軸* 的選擇、不影響 *consistency 軸*（consistency 在 read routing 層決定）。Group Replication / MySQL Cluster（synchronous multi-primary）會同時改三軸、是另一個故事、不在本文 scope。

跟這三軸獨立的、是 *replication 機制本身的可維護性*。binlog position-based replication 用 `(file, position)` 標 replica 進度、failover 時要對齊 position 容易出錯；[**GTID（Global Transaction Identifier）**](/backend/knowledge-cards/gtid/)用全域 transaction ID 標進度、failover / re-pointing 不必算 position。GTID 是 *跨 mode 的 infrastructure*、不是第三種 mode。

## Async replication：default + 高 throughput 的代價

Async 是 MySQL 預設、行為：

1. Primary 寫 binlog、立刻 commit、回應 client OK
2. Replica 的 IO thread 從 primary pull binlog event 到 local relay log
3. Replica 的 SQL thread apply relay log（單 thread 或 multi-thread parallel）

**Trade-off**：

- Durability：primary 寫完 commit、replica 還沒 pull = primary 在這瞬間 crash + 永久故障 → *data loss*（已 commit 的 transaction 在 replica 不存在）
- Latency：client 不等 replica、寫入延遲 = primary 自身寫 binlog 的時間（通常 < 1ms with `innodb_flush_log_at_trx_commit=1`）
- Consistency：replica 可能 lag、application 讀 replica 會 stale；用 `SHOW SLAVE STATUS` 看 `Seconds_Behind_Master`

**適用**：

- 主流選擇（90% 場景）
- Failover loss 在容忍範圍（多數 web 應用容忍 1-2 秒 data loss）
- Read scaling 為主要 driver、絕對 durability 非首要

**不適用**：

- 金融交易 / 訂單系統、不允許 any data loss
- Compliance 要求 zero data loss（PCI-DSS / 部分監管場景）

## Semi-sync replication：至少一個 standby ack 才 commit

Semi-sync 在 async 基礎上加 *primary 等至少 N 個 replica ack 才 commit* 的步驟：

1. Primary 寫 binlog
2. Primary 發送 binlog event 到所有 replica
3. *Primary 等至少 N 個 replica 回 ack*（N 是 `rpl_semi_sync_master_wait_for_slave_count`、預設 1）
4. Primary commit、回應 client

**Trade-off**：

- Durability：至少 N 個 replica 收到 binlog（不一定 apply）、primary crash 後 replica 還有 binlog 可 promote、保證 zero data loss（但是 *binlog-level*、不是 *applied-level*）
- Latency：client 等 primary + 一輪 replica ack RTT；跨 AZ 通常 +1-3ms、跨 region 可能 +50-200ms
- Consistency：跟 async 一樣、replica apply 仍 async、application 讀 replica 仍可能 stale

**MySQL 5.7+ 區分 *standard* 跟 *Loss-Less* semi-sync**：

- Standard semi-sync（5.5-5.6）：primary 先 commit 再等 ack、ack 超時 fallback 成 async — *仍可能 lose data*
- Loss-Less semi-sync（5.7+、`rpl_semi_sync_master_wait_point=AFTER_SYNC`）：primary 寫完 binlog 但 *先等 ack 再 commit*、ack 超時 fallback async 之前已寫 binlog 仍保證 durable

Production 場景必須用 Loss-Less semi-sync、不是 standard。

**適用**：

- 金融交易 / 訂單 / payment ledger
- 不允許 data loss、可接受寫入延遲 +1-3ms
- 已有 multi-AZ / multi-region 部署、replica 物理上可靠

**不適用**：

- 跨 region semi-sync（RTT 50-200ms）通常不划算 — 寫吞吐砍半、改用 *region-local sync replica + cross-region async chain*
- 寫吞吐 > 50K WPS 且容忍 sub-second loss — async 即可

## GTID-based replication：機制升級、跨 mode 都需要

GTID 把每個 transaction 標一個全域 ID：`<server_uuid>:<transaction_id>`。Replica 紀錄「已 apply 的 GTID set」、不再用 `(binlog_file, position)`。

**為什麼 GTID 比 binlog position 好**：

- **Failover re-pointing 簡單**：promote 新 primary 後、其他 replica 重新 attach 不必算 `MASTER_LOG_FILE` + `MASTER_LOG_POS`、用 `CHANGE MASTER TO MASTER_AUTO_POSITION=1` 即可
- **Multi-source replication 可行**：一個 replica 從多個 primary 拉、各 primary 的 GTID set 獨立 track
- **Consistency check 容易**：兩個 server 對 GTID set、就知道誰落後、有無 gap
- **跟 group replication / MySQL Cluster 必需**：5.7+ 多 primary 場景 GTID 是前提

**設定流程**（兩階段、不能直接開）：

1. **Phase 1 (預備、所有 server 同 mode)**：

    ```ini
    gtid_mode = ON_PERMISSIVE  -- 接受 GTID 跟 non-GTID transaction
    enforce_gtid_consistency = ON  -- 拒絕無法用 GTID 表達的 statement（CREATE TABLE...SELECT 等）
    ```

2. **Phase 2 (rolling、全部 server 都 Phase 1 後)**：

    ```ini
    gtid_mode = ON  -- 只接受 GTID transaction
    ```

跳 phase 直接 `gtid_mode=ON` 會讓 replication break（既有 non-GTID transaction 無法處理）。Production 啟用 GTID 要排 maintenance window、跑完 phase 1 觀察 1-2 天再進 phase 2。

## 配置 step-by-step（Loss-Less semi-sync + GTID 組合）

實務最常見組合：Loss-Less semi-sync + GTID。配置順序：

### Step 1：Primary + replica 都開 GTID（兩 phase 跑完）

```ini
# my.cnf on primary AND replica
gtid_mode = ON
enforce_gtid_consistency = ON
log_bin = mysql-bin
log_slave_updates = 1  -- replica 也記 binlog (chained replication 需要)
binlog_format = ROW    -- ROW 比 STATEMENT 安全
sync_binlog = 1        -- 每次 commit fsync binlog
innodb_flush_log_at_trx_commit = 1  -- 每次 commit fsync InnoDB log
```

### Step 2：Primary 安裝 semi-sync plugin

```sql
INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';
SET GLOBAL rpl_semi_sync_master_enabled = 1;
SET GLOBAL rpl_semi_sync_master_wait_for_slave_count = 1;  -- 至少 1 個 ack
SET GLOBAL rpl_semi_sync_master_wait_point = AFTER_SYNC;   -- Loss-Less
SET GLOBAL rpl_semi_sync_master_timeout = 10000;           -- 10s timeout、超時 fallback async
```

### Step 3：Replica 安裝 semi-sync plugin

```sql
INSTALL PLUGIN rpl_semi_sync_slave SONAME 'semisync_slave.so';
SET GLOBAL rpl_semi_sync_slave_enabled = 1;
STOP SLAVE IO_THREAD;
START SLAVE IO_THREAD;  -- 重啟 IO thread 啟用 semi-sync
```

### Step 4：Replica attach primary

```sql
CHANGE MASTER TO
  MASTER_HOST='primary.example.com',
  MASTER_PORT=3306,
  MASTER_USER='repl',
  MASTER_PASSWORD='...',
  MASTER_AUTO_POSITION=1;  -- 用 GTID auto-position
START SLAVE;
```

### Step 5：驗證

```sql
-- Primary: 確認 semi-sync 啟用 + 有 active client
SHOW STATUS LIKE 'Rpl_semi_sync_master_status';      -- ON
SHOW STATUS LIKE 'Rpl_semi_sync_master_clients';     -- ≥ 1
SHOW STATUS LIKE 'Rpl_semi_sync_master_yes_tx';      -- > 0 (有 transaction 走 semi-sync)
SHOW STATUS LIKE 'Rpl_semi_sync_master_no_tx';       -- 應該 = 0 (沒有 fallback 成 async)

-- Replica: 確認 GTID + IO thread 正常
SHOW SLAVE STATUS\G
-- Slave_IO_Running: Yes
-- Slave_SQL_Running: Yes
-- Retrieved_Gtid_Set: 跟 primary Executed_Gtid_Set 接近
-- Seconds_Behind_Master: 觀察 lag
```

## 5 個 Production 踩雷

### 1. Replication lag 暴衝 — 單 SQL thread bottleneck

預設 replica 的 SQL thread 是 *單 thread* apply、primary 多 thread 寫入時 replica 跟不上、lag 從 < 100ms 飆到分鐘級。常見觸發：批次 UPDATE / DELETE、大 transaction、index rebuild。

修法：

- 啟用 *multi-thread replication*：`slave_parallel_workers = 8`（per database 或 per logical clock parallel）
- 5.7+ 用 `slave_parallel_type = LOGICAL_CLOCK`：依 primary 上的 group commit 並行度自動 parallel
- 8.0+ 的 *writeset-based parallel*：`binlog_transaction_dependency_tracking = WRITESET`、更細粒度並行

監控：`Seconds_Behind_Master` 是 *表面指標*、實際看 `Executed_Gtid_Set` 跟 primary 對比的 GTID gap 更準。

### 2. Semi-sync timeout fallback 成 async（沒監控就看不見）

`rpl_semi_sync_master_timeout` 預設 10000ms（10 秒）、超時後 *自動 fallback async*、直到 replica 重連。Application 視角看不到任何 error、但 *durability guarantee 已失效*。

修法：

- 監控 `Rpl_semi_sync_master_status` — fallback 後變 OFF
- 監控 `Rpl_semi_sync_master_no_tx` — fallback 期間每個 transaction 都計數
- Alert 規則：5 分鐘內 `no_tx` 增加 > 0 即告警
- Timeout 設太短（< 5s）容易 false positive、設太長（> 30s）crash 時 data loss 風險增

### 3. GTID gap — replica 無法 attach

Replica 重新 attach primary 時報 `ERROR 1236: ... transactions you need from master are purged`、原因是 primary 的 `binlog_expire_logs_seconds` 過短、需要的 binlog 已被清掉。GTID 模式下這個錯誤更明顯（直接看 GTID gap）、但 binlog position 模式下也一樣。

修法：

- `binlog_expire_logs_seconds = 604800`（7 天）作為 baseline
- 大流量 server 確認 disk 容量能撐 7 天 binlog（一個高峰小時 binlog 可能 GB 級）
- 真的 gap 太大時用 *base backup + replay binlog* 重建 replica、不要硬 reset GTID

### 4. Loss-Less semi-sync 不一定真的 loss-less

`AFTER_SYNC` 模式 *primary 寫 binlog → 等 ack → commit*、看起來 zero loss。但 *primary 寫完 binlog 還沒等 ack 時 crash* + replica *剛好沒收到那個 binlog event* + replica promote — 這個 binlog event 在新 primary 不存在、但舊 primary 的 binlog 仍紀錄為 *已寫 binlog 未 commit*。client 收到 *connection lost*、不知道 transaction 是否成功。

修法：

- 接受這個 *edge case unknown state*、application 用 idempotency key + retry 處理
- Loss-Less semi-sync 保證的是 *已 commit transaction 不會丟*、不是 *所有寫入都 ack-and-tell*
- 真的 zero unknown state 需要 group replication / Galera Cluster / MySQL Cluster（synchronous multi-primary）

### 5. Chained replication 雪崩

Topology 是 `primary → replica1 → replica2 → ...`（hub-and-spoke 之外的選擇、節省 primary 出口頻寬）。Replica1 SQL thread 卡住、replica2 跟 replica3 都被 block、整條 chain 雪崩。

修法：

- 避免超過 2 層 chain（primary → tier1 replica → tier2 replica 是上限）
- 用 *parallel binary log relay*（5.7+ `slave_pending_jobs_size_max` + parallel workers）讓 chain 中段不阻塞
- 規模真的大、改用 *binlog server*（如 Maxwell / MaxScale）解耦 chain dependency
- 跨 region 用 *region-local hub + cross-region async*、不是長 chain

## 容量 / cost 對照

| 配置                                | 寫吞吐影響  | Replica overhead            | 適合 workload                             |
| ----------------------------------- | ----------- | --------------------------- | ----------------------------------------- |
| Async + binlog position             | baseline    | 低（IO + SQL thread）       | 高吞吐、容忍 sub-second loss              |
| Async + GTID                        | baseline    | 同上、failover 容易         | 大多數 production 預設                    |
| Loss-Less semi-sync + GTID（1 ack） | -10% ~ -20% | 同上 + ack RTT              | 金融、訂單、不容忍 data loss              |
| Loss-Less semi-sync + GTID（2 ack） | -15% ~ -30% | 同上、跨 AZ                 | 強 durability + multi-AZ HA               |
| Group Replication（synchronous）    | -30% ~ -50% | 高（每 transaction quorum） | 不允許 single-primary、multi-primary 寫入 |

跨 AZ semi-sync 通常加 1-3ms、跨 region 加 50-200ms — 寫密集 workload 跨 region semi-sync 通常不划算、改用 *region-local sync + cross-region async chain*。

## 整合 / 下一步

### Aurora MySQL

Aurora MySQL 用 *AWS-managed storage layer*、storage 自動 replicate 6 份跨 3 AZ、不需要應用層配 semi-sync。從自管 MySQL 遷 Aurora 時、上方所有 semi-sync 配置 *消失*、改成 Aurora storage quorum（4 of 6 write、3 of 6 read）。

trade-off 軸的 *durability* 完全交給 Aurora、application 只關心 *latency* + *consistency*。詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

### Vitess（sharding layer）

Vitess shard 內部仍用 MySQL replication（async or semi-sync）、Vitess 不取代 replication topology、是 *上層 routing*。Vitess `vttablet` 每個 shard 有自己的 primary + replica、跟本文 topology 設計一致。

Vitess 比較大議題在 *cross-shard transaction*（VReplication 跨 shard binlog stream）、不是 replication topology — 詳見 MySQL backlog 中 *Vitess sharding 設計* 篇（待寫）。

### ProxySQL（read replica routing）

ProxySQL 是 MySQL 生態的 *connection pool + query routing* 標準、按 query type（SELECT vs DML）跟 replica lag 自動 route。寫入路 primary、讀走 replica、replica lag > N 秒時暫時退路 primary 維持 consistency。

ProxySQL 跟本文 replication topology 是 *互補不重疊* — replication 設定哪些 server 有什麼資料、ProxySQL 設定 query 怎麼分配。詳見 MySQL backlog 中 *ProxySQL 配置* 篇（待寫）。

### Orchestrator（HA failover）

Orchestrator 是 MySQL HA topology 管理 + 自動 failover 工具、用 GTID 偵測 replica 進度、failover 時自動 promote 最新 replica。對比 PostgreSQL 的 Patroni（詳見 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)）— 兩者角色相同、Orchestrator 需要 GTID + 對 MySQL 行為熟、Patroni 需要 DCS（etcd / Consul）+ 對 PG 行為熟。

詳見 MySQL backlog 中 *Orchestrator failover 設計* 篇（待寫）。

### CDC（Maxwell / Debezium）

Maxwell（Zendesk 出品、MySQL-only）跟 Debezium（Red Hat、MySQL / PG / MongoDB 都支援）都讀 MySQL binlog 轉成 event stream（Kafka / Kinesis / Pulsar）。Binlog 必須 `ROW` format、GTID 啟用後 *exactly-once* delivery 更好維護（不需算 binlog position）。

跟 PG logical replication + Debezium 對比、MySQL 用 binlog（physical / row-level）不是 logical decoding、所以 schema change 時 *CDC consumer 要 schema-aware* 處理。詳見 MySQL backlog 中 *Binary log + Maxwell / Debezium CDC* 篇（待寫）。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [PostgreSQL Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（PG sibling、streaming + LSN + slot 機制 vs MySQL binlog 對位）
- [PostgreSQL Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（PG sibling、不同 HA 機制）
- [PostgreSQL Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（PG CDC sibling、不同 replication 抽象層）
- [PostgreSQL Replication Slot Management](/backend/01-database/vendors/postgresql/replication-slot-management/)（PG slot 治理、MySQL 無對應概念）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（managed MySQL、replication 交給 storage layer）
- [1.3 Transaction Boundary](/backend/01-database/transaction-boundary/)（transaction 行為跟 replication 互動）
- [1.10 KV / Document DB 容量規劃](/backend/01-database/kv-document-capacity-planning/) / [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（替代路徑）
- [quorum 卡片](/backend/knowledge-cards/quorum/) / [eventual consistency 卡片](/backend/knowledge-cards/eventual-consistency/) / [stale read 卡片](/backend/knowledge-cards/stale-read/)
- 官方：[MySQL Replication](https://dev.mysql.com/doc/refman/8.0/en/replication.html) / [Semi-Sync](https://dev.mysql.com/doc/refman/8.0/en/replication-semisync.html) / [GTID](https://dev.mysql.com/doc/refman/8.0/en/replication-gtids.html)
