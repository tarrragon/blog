---
title: "PostgreSQL Replication Slot Management：Physical / Logical / Failover Slot 治理"
date: 2026-05-19
description: "PG replication slot 是 *primary 端的 standby 進度紀錄*、防 WAL premature deletion。但 orphan slot 會吃 disk、failover 後 logical slot 不會自動跟新 primary、是 PG 操作的 hidden complexity。本文走 physical / logical slot 差異、slot lifecycle、failover slot synchronization（PG 17+ 新特性）、orphan slot 治理、5 production 踩雷（orphan slot disk 爆 / logical slot lag / failover 後 slot 丟 / wal_keep_size 跟 slot 衝突 / connection 同時打 slot 數量限制）"
weight: 28
tags: ["backend", "database", "postgresql", "replication-slot", "logical-replication", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *replication slot management* — physical / logical / failover slot 三類治理。

---

## Replication Slot 兩大類

PG 兩種 replication slot：

### Physical Replication Slot

對應 *streaming replication*（physical WAL byte-level）：

```sql
SELECT pg_create_physical_replication_slot('standby1_slot');
```

用於：

- Streaming replication standby（[Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)）
- pg_basebackup 用 slot 防 WAL 清理
- 高 lag standby 防 WAL premature deletion

### Logical Replication Slot

對應 *logical replication / logical decoding*：

```sql
SELECT pg_create_logical_replication_slot('my_slot', 'pgoutput');
-- 或用 wal2json plugin
SELECT pg_create_logical_replication_slot('debezium_slot', 'wal2json');
```

用於：

- PG-to-PG logical replication（publication / subscription）
- CDC（Debezium / Maxwell / pg_logical_emitter）
- Multi-master replication（BDR / pgEdge / Spock）

logical slot 跟 physical slot 共存、各自獨立 retention。

## Slot Lifecycle

```text
建立 → active（有 consumer）→ inactive（consumer 失聯）→ drop
                                    ↓
                              WAL 持續累積（直到推進 LSN 或 drop）
```

**狀態查詢**：

```sql
SELECT slot_name,
       slot_type,
       active,
       restart_lsn,
       confirmed_flush_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots;
```

關鍵欄位：

- `slot_type`：`physical` / `logical`
- `active`：true / false（consumer 是否連著）
- `restart_lsn`：slot 起點 LSN、primary 必須保留這以後的 WAL
- `confirmed_flush_lsn`：logical slot 已 confirm flush 的 LSN
- `retained_wal`：當前因 slot 累積的 WAL

## Failover Slot Synchronization (PG 17+)

PG 17 之前的 *痛點*：logical replication slot 是 *primary 上的 state*、failover 後 *新 primary 沒這個 slot*、CDC consumer 失聯、需要重建（大工程）。

PG 17 加 *failover slot synchronization*：

```sql
-- PG 17+：標 slot 為 failover-tracked
-- signature: pg_create_logical_replication_slot(slot_name, plugin, temporary, two_phase, failover)
SELECT pg_create_logical_replication_slot('my_slot', 'pgoutput', false, false, true);
--                                                                          ↑
--                                                                     failover=true（第 5 個參數）
-- 注意：第 4 個參數是 two_phase（這裡 false）、第 5 個才是 failover

-- Standby 上 enable sync_replication_slots
ALTER SYSTEM SET sync_replication_slots = on;
SELECT pg_reload_conf();
```

`sync_replication_slots = on` 後、physical replication 同步 slot state 到 standby。Failover promote standby 後、logical slot 仍可用、CDC consumer 重連即可。

PG 17 之前用 [pgEdge](https://www.pgedge.com/) / *pglogical* 等 extension 提供類似功能、現在 PG core 內建。

## Orphan Slot 治理

`active = false` 的 slot 持續累積 WAL、disk 爆是 PG production 經典事故。

### 監控 orphan slot

```sql
-- 找 inactive 太久的 slot
SELECT slot_name, active, restart_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
WHERE NOT active
  AND pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) > 1024 * 1024 * 1024;  -- > 1 GB
```

### 自動 invalidate slot（PG 13+）

```sql
-- postgresql.conf
ALTER SYSTEM SET max_slot_wal_keep_size = '50GB';  -- slot 累積 > 50GB 自動 invalidate
```

當 slot 累積 WAL 超過 `max_slot_wal_keep_size`、PG 自動 invalidate slot（`active=false` 且不再保留 WAL）。Consumer 重連會 fail、必須重建（base backup + new slot）。

這是 *trade-off*：

- 設 limit → 保護 disk、但 consumer 失聯 → 大重建工作
- 不設 limit → consumer 失聯 OK、但 disk 爆

實務多數設 `max_slot_wal_keep_size` 給 *disk capacity 50%*、避免徹底 disk full。

### 手動 drop orphan slot

```sql
-- 確認 slot 真的不需要
SELECT * FROM pg_replication_slots WHERE slot_name = 'old_standby_slot';

-- Drop
SELECT pg_drop_replication_slot('old_standby_slot');
```

DR runbook 必須包含 *standby 退役流程*：先 standby fence、再 primary drop slot。

## 5 個 Production 踩雷

### 1. Orphan slot disk 爆

最經典 PG 事故：standby decomission 沒 drop slot、primary 持續保留 WAL、`pg_wal/` 累積到 disk full、primary 也掛。

修法：

- 監控 `pg_replication_slots` + `pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn))` retained_wal
- 設 `max_slot_wal_keep_size`（PG 13+）— hard limit
- Standby 退役 runbook 強制 *先 fence、再 drop slot*
- Cron job 自動 alert orphan slot

### 2. Logical slot lag — CDC consumer 跟不上

Logical decoding 比 physical replication 慢（per-transaction logical event 重組）。CDC consumer（Debezium）跟不上 → slot lag 累積。

修法：

- 監控 `pg_replication_slots.confirmed_flush_lsn` 跟 primary `pg_current_wal_lsn()` 對比
- CDC consumer 性能調整（throughput / batch size）
- Throttle source writes（如果不能升 consumer）
- 對 hot table 拆 publication / subscription、避免單 slot 處理所有變更

詳見 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)。

### 3. Failover 後 logical slot 丟（PG 16 之前）

PG 16 之前、failover promote standby、新 primary 沒有原 logical slot。CDC consumer 試連、ERROR: `replication slot "xxx" does not exist`。

修法（PG 17+）：

- 用 *failover slot synchronization*（如上）
- `pg_create_logical_replication_slot(...,  failover := true)`
- Standby `sync_replication_slots = on`

修法（PG 16-）：

- 用 [pglogical](https://www.2ndquadrant.com/en/resources/pglogical/) 或 [pgEdge](https://www.pgedge.com/) extension
- Failover runbook 包含 *新 primary 重建 logical slot*（CDC consumer 重 snapshot）
- Pre-create slot on standby + manual sync（早期 workaround）

### 4. `wal_keep_size` 跟 slot 衝突

`wal_keep_size`（PG 13+）/ `wal_keep_segments`（< 13）跟 slot 都會保留 WAL：

- `wal_keep_size`：固定 minimum WAL 保留量
- Slot：動態保留直到 consumer 推進

兩者一起 set 時：實際保留 WAL = `max(wal_keep_size, slot 需要的量)`。

修法：

- `wal_keep_size` 設小（如 1-2 GB）作 *minimum backup*
- 主要靠 slot 動態保留 — 給 active consumer
- 監控 `pg_wal/` 大小 + 拆解 retention source（`wal_keep_size` vs slot 各佔多少）

### 5. Slot 數量上限

`max_replication_slots` 預設 10、不夠時新 slot 建不出來、報錯。

修法：

- Production 大 cluster 設 `max_replication_slots = 50` 或更多
- 對 *standby + logical replication + CDC consumer* 同時跑、計算需要的 slot 數
- 監控 `SELECT count(*) FROM pg_replication_slots` 接近 limit 時告警

## Slot Naming Convention

Production 大 cluster 多 slot、命名 convention 重要：

```text
<consumer-type>_<consumer-name>_<purpose>
例：
- physical_standby1_replication
- physical_standby2_replication
- logical_debezium_orders_cdc
- logical_pgedge_node2_subscription
- physical_pgbasebackup_temp（base backup 用、completed 後 drop）
```

清楚命名讓 *看 slot 名* 就知道用途、誰負責、能不能 drop。

## 跟其他模組整合

- [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)：physical slot 給 streaming replication 用
- [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)：logical slot 給 CDC
- [BDR / Multi-Master](/backend/01-database/vendors/postgresql/bdr-multi-master/)：multi-master 大量用 logical slot
- [PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)：WAL archive 跟 slot 是兩種 WAL retention 機制、可並行

## 監控 metric

Production 持續監控：

- `pg_replication_slots.active` — 失聯 slot
- `pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)` — slot 累積 WAL
- `pg_replication_slots.confirmed_flush_lsn` vs `pg_current_wal_lsn()` — logical slot lag
- `pg_ls_waldir()` 看 `pg_wal/` 目錄大小
- `count(*) FROM pg_replication_slots` 對 `max_replication_slots` 比例

把這些丟進 Datadog / Prometheus + alert。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（physical slot 用途）
- [PG Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（logical slot 用途）
- [PG BDR / Multi-Master](/backend/01-database/vendors/postgresql/bdr-multi-master/)（multi-master 大量 slot）
- [PG PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)（WAL retention 兩種機制）
- 官方：[PG Replication Slots](https://www.postgresql.org/docs/current/warm-standby.html#STREAMING-REPLICATION-SLOTS) / [Logical Replication Slot](https://www.postgresql.org/docs/current/logicaldecoding.html)
