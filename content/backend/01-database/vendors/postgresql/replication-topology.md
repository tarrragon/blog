---
title: "PostgreSQL Replication Topology：async / sync / quorum 三模式跟 LSN + replication slot 的三軸組合"
date: 2026-05-19
description: "PostgreSQL streaming replication 不是「sync 或 async」、是 *durability / latency / consistency* 三軸組合 + LSN-based 進度追蹤 + replication slot 治理。本文走 3 軸取捨模型、async / sync / quorum-based sync 行為對比、LSN + replication slot 機制、配置 step-by-step、5 production 踩雷（standby lag 暴衝 / sync standby 退回 async / orphan replication slot / cascading replication 雪崩 / failover 後 timeline 分歧）、跟 Patroni HA + logical replication 整合"
weight: 12
tags: ["backend", "database", "postgresql", "replication", "streaming-replication", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *streaming replication topology* — 從 single primary 到 multi-standby 部署的 3 個 trade-off 軸 + LSN + replication slot 機制。

---

## Replication 的 3 個 trade-off 軸 + mode 選擇

PG streaming replication mode 選擇看起來是「async 還是 sync」、實際是 3 個獨立 trade-off 軸的組合、async / sync / quorum-based sync 是這些軸的常見組合 *名稱*：

| 軸              | 端 A                      | 端 B                              | PG 旋鈕                                                |
| --------------- | ------------------------- | --------------------------------- | ------------------------------------------------------ |
| **Durability**  | primary 寫完就 commit     | 至少一個 standby 收到才 commit    | `synchronous_commit` / `synchronous_standby_names`     |
| **Latency**     | client 等 primary 寫完 OK | client 等 standby ack（額外 RTT） | 同上                                                   |
| **Consistency** | standby 隨時可能 stale    | standby 跟 primary 保證讀到一致   | application read routing rule（不是 replication 旋鈕） |

跟這三軸獨立的、是 *replication 機制本身的可維護性*：

- **LSN（Log Sequence Number）**：PG 用全域 byte offset 標 WAL 進度、所有 standby 同步用 LSN 對齊、不像 MySQL 早期 binlog position + file 雙欄
- **Replication slot**：primary 紀錄每個 standby 已接收的 LSN、防 standby 失聯期間 WAL 被清掉、是 streaming replication 的 *持久化進度追蹤*

跟 [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/) 對比、PG 的 LSN + replication slot 直接內建 *standby 進度追蹤*、不像 MySQL 5.7- 要靠 binlog position + GTID 雙機制；但 slot 是 *primary 紀錄*、orphan slot 是 PG-specific 議題（slot 留 WAL 直到 standby 重連、standby 永久失聯 → primary disk 爆）。

## Async streaming：default + 高 throughput 的代價

Async 是 PG 預設、行為：

1. Primary 寫 WAL 進 `pg_wal/` 目錄、commit、回應 client OK
2. WAL sender process 把 WAL stream 給 standby
3. Standby WAL receiver 寫 standby 的 `pg_wal/`、startup 進程 redo 套用

**Trade-off**：

- Durability：primary commit 後 standby 還沒收 → primary 永久故障 → *data loss*（已 commit 的 transaction 在 standby 不存在）
- Latency：client 寫入延遲 = primary 自身 fsync WAL 的時間（`fsync=on` + `synchronous_commit=on` 預設、通常 < 1ms 在 SSD / NVMe）
- Consistency：standby 可能 lag、application 讀 standby 會 stale；用 `pg_stat_replication.write_lag / flush_lag / replay_lag` 看

**配置**：

```ini
# postgresql.conf on primary
wal_level = replica          # 至少 replica（logical 是 superset）
max_wal_senders = 10         # 並行 WAL sender process 數（依 standby 數量）
wal_keep_size = 1024MB       # WAL 保留量（slot 為主、但 backup buffer）
synchronous_commit = on      # 預設、primary 自己 fsync WAL
# synchronous_standby_names 留空 = async
```

**適用**：

- 主流選擇（90% 場景）
- Failover loss 在容忍範圍（多數 web 應用容忍 1-2 秒 data loss）
- Read scaling 為主要 driver、絕對 durability 非首要

## Sync streaming：至少一個 standby flush WAL 才 commit

Sync mode 在 async 基礎上加 *primary 等指定 standby flush WAL 才回 client*：

1. Primary 寫 WAL、send to standby
2. Standby 收到 WAL、寫進 `pg_wal/`、fsync、回 ack
3. *Primary 等 ack* → commit → 回 client

`synchronous_commit` 有 5 個 level、不是 binary：

| Level          | 行為                                                                   | Latency 影響            | Crash data loss                    |
| -------------- | ---------------------------------------------------------------------- | ----------------------- | ---------------------------------- |
| `off`          | primary 不等自己 fsync、background flush                               | +0                      | primary crash 丟 0-1 秒            |
| `local`        | primary fsync own WAL（不等 standby）                                  | baseline                | primary crash 0、standby 丟        |
| `remote_write` | primary fsync + standby 收到（不必 standby fsync）                     | +1 RTT 大致             | OS crash on standby 丟             |
| `on` (預設)    | primary fsync + standby fsync（standby 收進 disk）                     | +1 RTT + fsync          | 全 crash 都不丟                    |
| `remote_apply` | primary fsync + standby fsync + standby 已 *replay*（visible to read） | +1 RTT + fsync + replay | 全 crash 都不丟 + replica 立刻可讀 |

**配置（synchronous）**：

```ini
synchronous_commit = on
synchronous_standby_names = 'FIRST 1 (standby1, standby2)'
# 'FIRST 1' = 第一個 active standby ack 即可
# 'ANY 2 (s1, s2, s3)' = 任 2 個 ack 即可（quorum-based）
```

**Quorum-based sync**：用 `ANY N` 語法、達到 N 個 ack 就 commit、提高 latency stability（不依賴特定 standby）：

```ini
synchronous_standby_names = 'ANY 2 (standby1, standby2, standby3)'
# 3 個 standby 中任 2 個 ack 即 commit
```

**適用**：

- 金融交易 / 訂單 / payment ledger（不允許 data loss）
- 已有 multi-AZ deploy、replica 物理上可靠
- 可接受寫入延遲 +1-3ms (跨 AZ)

**不適用**：

- 跨 region sync（RTT 50-200ms）— 寫吞吐砍半、改用 *region-local sync + cross-region async*
- 寫吞吐 > 50K WPS + 容忍 sub-second loss — async 即可

## LSN + Replication Slot：PG 的進度追蹤機制

PG 每個 WAL 寫入都標 *LSN*（64-bit byte offset）。Standby 紀錄 *已收到 / 已 flush / 已 replay* 的 LSN、primary 透過 streaming protocol 知道每個 standby 進度。

**Replication slot** 是 *primary 端的 standby 進度紀錄*：

```sql
-- 建 physical replication slot（給 streaming replication 用）
SELECT * FROM pg_create_physical_replication_slot('standby1_slot');

-- 查 slot 狀態
SELECT slot_name, active, restart_lsn, confirmed_flush_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;
```

**Slot 的核心責任**：

- *防 WAL premature deletion*：standby 失聯（restart / network blip）、primary 仍保留 slot 對應 LSN 之後的 WAL、standby 重連可繼續 stream
- *無需 base backup re-build*：跟沒 slot 的 standby 對比、有 slot 的 standby 失聯後重連、不用重建

**Slot 跟 `wal_keep_size`**：

- `wal_keep_size`（PG 13+）/ `wal_keep_segments`（< 13）：minimum WAL 保留量、不依賴 slot
- Slot 是 *動態保留*：直到 slot 的 standby 推進 LSN 才釋放對應 WAL
- 兩者組合：`wal_keep_size` 是底線、slot 是 standby-specific 動態保留

**Standby 配置（用 slot）**：

```ini
# standby1 postgresql.conf
primary_conninfo = 'host=primary.example.com port=5432 user=replication password=...'
primary_slot_name = 'standby1_slot'   # 用 primary 上預先建的 slot
hot_standby = on                       # 讓 standby 接受 read query
```

`standby.signal` 空檔案在 PG_DATA 內、告訴 PG 這是 standby、進入 recovery mode。

## 配置 step-by-step（sync streaming + slot）

實務最常見組合：sync streaming + replication slot + cross-AZ replica。

### Step 1：Primary 配置

```ini
# postgresql.conf
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
synchronous_commit = on
synchronous_standby_names = 'FIRST 1 (standby1, standby2)'
wal_keep_size = 1024MB

# pg_hba.conf — 允許 replication 連線
host replication replication 10.0.0.0/16 scram-sha-256
```

Restart primary 套用。

### Step 2：建 replication user + slot

```sql
CREATE USER replication WITH REPLICATION PASSWORD '...';
SELECT * FROM pg_create_physical_replication_slot('standby1_slot');
SELECT * FROM pg_create_physical_replication_slot('standby2_slot');
```

### Step 3：Standby base backup

```bash
# 在 standby 上跑
pg_basebackup -h primary.example.com -D /var/lib/postgresql/data \
  -U replication -P -X stream \
  -S standby1_slot -R
# -R: 自動生成 standby.signal + primary_conninfo
# -X stream: 邊 backup 邊 stream 增量 WAL（避免 backup 期間 WAL gap）
```

### Step 4：Standby 啟動

```bash
# standby /var/lib/postgresql/data/postgresql.auto.conf 已有：
# primary_conninfo = 'host=primary.example.com user=replication password=... application_name=standby1'
# primary_slot_name = 'standby1_slot'

pg_ctl -D /var/lib/postgresql/data start
```

### Step 5：驗證

```sql
-- Primary: 確認 standby 連上
SELECT application_name, state, sync_state, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
-- 應顯示 standby1 / streaming / sync / 各 lag

-- Standby: 確認在 recovery + 收到 WAL
SELECT pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

## 5 個 Production 踩雷

### 1. Standby lag 暴衝 — Single replay process bottleneck

PG standby 是 *single startup process* 套用 WAL（不像 MySQL multi-thread replication）、primary 高並發寫入時 standby 跟不上、lag 從 < 100ms 飆到分鐘級。常見觸發：批次 UPDATE / DELETE、大 transaction、index 建立、autovacuum 大量 dead tuple cleanup。

修法：

- *Parallel WAL apply*（PG 14+）：`max_parallel_workers_per_gather` 增加 background worker、但仍受 startup process 主導
- 對 *read scaling* 場景接受 standby lag、application 用 *primary read 對 latency-critical query*
- *Cascading replication* 對 high-fan-out 解決 sender CPU bottleneck、但 standby replay 仍 single-thread

監控：`pg_stat_replication.replay_lag` 是 *最後一個 commit 到 standby replay 的時間差*、超過 threshold 即告警。

### 2. Sync standby 失聯時 primary commit 卡住

`synchronous_standby_names = 'FIRST 1 (standby1)'` + standby1 down → primary commit *等永遠*。Application 全部 timeout。

修法：

- 用 `ANY N` quorum：`synchronous_standby_names = 'ANY 1 (standby1, standby2)'` — 任一 standby ack 即可
- 設多 standby、防單一失聯
- 監控 sync standby 健康、自動 failover 切 sync mode 到其他 standby（Patroni 自動做）
- 緊急情況：在 primary 跑 `ALTER SYSTEM SET synchronous_standby_names = ''; SELECT pg_reload_conf();` 暫時退 async（接受 data loss risk）

### 3. Orphan replication slot — Primary disk 爆

Standby 失聯（永久故障 / 重 decommission 但忘了 drop slot）、primary slot 持續保留 WAL、`pg_wal/` 累積到 disk 滿、primary 也掛。

修法：

- 監控 `pg_replication_slots.active` — `false` 持續 > N 小時是警訊
- 監控 slot lag：

   ```sql
   SELECT slot_name, active,
          pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
   FROM pg_replication_slots WHERE retained_wal > 10GB;
   ```

- 設 `max_slot_wal_keep_size`（PG 13+）— slot 對應 WAL 超過 limit 自動 invalidate slot（standby 之後要 base backup 重來）
- DR runbook 紀錄 *standby 退役流程* 必須包含 `pg_drop_replication_slot('xxx')`

### 4. Cascading replication 雪崩

Topology `primary → standby1 → standby2 → ...`（每層遞迴 stream）。Standby1 startup process 卡住、後續 standby 都被 block、整條 chain 雪崩。

修法：

- 避免超過 2 層 cascade（primary → tier1 → tier2 是上限）
- 跨 region 用 *region-local tier1 + cross-region tier2*、不是長 chain
- 真的大規模、改用 *binlog server* style：[Citus / pgcat](https://github.com/postgresml/pgcat) 等中介、或 logical replication 解耦

### 5. Failover 後 timeline 分歧

Primary 失敗、standby1 promote 為新 primary、其他 standby（standby2 / 3）原本連舊 primary、必須重新連 standby1。但 PG 用 *timeline*（每次 promotion 增 1）標 WAL 分支、原 standby 的 timeline 跟新 primary 不同。重連時看到 timeline mismatch、報錯。

修法：

- *pg_rewind* 工具：對比新 primary 跟舊 standby 的 timeline 分歧點、把舊 standby 上 *新 primary 沒有的 WAL* 倒退、然後從分歧點重新跟新 primary 同步
- *Base backup re-build*：對舊 standby 重建 — 慢但保證乾淨
- [Patroni](/backend/01-database/vendors/postgresql/patroni-ha/) 自動處理 pg_rewind / base backup 選擇

## 容量 / cost 對照

| 配置                            | 寫吞吐影響  | Standby overhead            | 適合 workload                          |
| ------------------------------- | ----------- | --------------------------- | -------------------------------------- |
| Async streaming + slot          | baseline    | 低（WAL receive + startup） | 高吞吐、容忍 sub-second loss           |
| Sync `remote_write` + 1 standby | -5% ~ -10%  | 同上 + RTT                  | 一般 production、可接受 OS crash 丟    |
| Sync `on` + 1 standby           | -10% ~ -20% | 同上 + fsync                | 金融、訂單、不容忍 data loss           |
| Sync `on` + ANY 2 quorum        | -15% ~ -30% | 同上、跨 AZ                 | 強 durability + multi-AZ HA            |
| Sync `remote_apply` + 1 standby | -20% ~ -40% | 同上 + replay               | 強一致 read on standby（少用、成本高） |

跨 AZ sync 通常加 1-3ms、跨 region 加 50-200ms — 寫密集 workload 跨 region sync 通常不划算、改用 *region-local sync + cross-region async chain*。

## 整合 / 下一步

### Patroni HA

[Patroni](/backend/01-database/vendors/postgresql/patroni-ha/) 是 PG HA 自動 failover 標準、依賴 DCS（etcd / Consul）+ 本文 replication topology。Patroni 自動：

- 偵測 primary 失聯、promote 適合 standby
- 處理 timeline 分歧（pg_rewind）
- 重配 sync standby（避免 sync standby 失聯卡 primary）

### Logical Replication + Debezium

[Logical replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 是 *跟 streaming replication 共用 WAL* 但不同 abstraction — logical decoding output event、streaming replication output physical bytes。Logical replication slot 跟 physical slot 共存、各自獨立 retention。

### PITR + WAL Archiving

[PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/) 用 *archive_command* 把 WAL ship 到 S3、跟 streaming replication 並行：

- Streaming：給 *活的 standby*（real-time read scaling / HA）
- Archive：給 *PITR + 新 standby base backup source*

兩者使用同一 WAL stream、不衝突。

### Connection 路由（pgBouncer + read/write split）

[pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/) 不做 read/write split（transaction pool 不看 SQL）。Read replica routing 通常用 *application-level* 或 *HAProxy 監控 standby health*。

### 跟 MySQL Replication Topology 對比

| 維度               | PG streaming replication                   | MySQL replication                           |
| ------------------ | ------------------------------------------ | ------------------------------------------- |
| 進度追蹤           | LSN（單一 byte offset）                    | GTID 或 binlog (file, position)             |
| 標準工具           | streaming replication（physical）+ logical | binlog ROW format                           |
| Sync 機制          | `synchronous_commit` + standby names       | semi-sync plugin                            |
| Quorum             | `ANY N` syntax                             | `rpl_semi_sync_master_wait_for_slave_count` |
| Replay parallelism | Single startup process                     | Multi-thread (logical clock / writeset)     |
| Replica routing    | pgBouncer 不看 SQL、需外接                 | ProxySQL 內建 query routing                 |

兩者 high-level 對等、低層機制有顯著差異。詳見 [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（HA failover、依賴本文 replication topology）
- [PG Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（不同 abstraction、共用 WAL）
- [PG PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)（streaming + archive 並行）
- [PG pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/)（connection pool、不做 read/write split）
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（sibling、不同機制）
- [quorum 卡片](/backend/knowledge-cards/quorum/) / [stale-read 卡片](/backend/knowledge-cards/stale-read/) / [eventual-consistency 卡片](/backend/knowledge-cards/eventual-consistency/)
- 官方：[PG Streaming Replication](https://www.postgresql.org/docs/current/warm-standby.html) / [pg_basebackup](https://www.postgresql.org/docs/current/app-pgbasebackup.html)
