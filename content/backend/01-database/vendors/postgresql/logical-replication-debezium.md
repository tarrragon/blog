---
title: "PostgreSQL Logical Replication + Debezium CDC：replication slot × failure × recovery 對照"
date: 2026-05-18
description: "PostgreSQL logical replication slot 跟 Debezium CDC 的失效模式對照表：slot lag 撐爆 primary disk / schema change 斷流 / 初始 COPY 鎖表 / zombie slot 不釋放 / replay storm 後 offset reset；publication / subscription / pgoutput 配置、跟 Kafka outbox pattern 整合"
weight: 14
tags: ["backend", "database", "postgresql", "logical-replication", "debezium", "cdc", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 提到 logical decoding / Debezium CDC、本文聚焦 *replication slot 生命週期 + 5 個 production failure mode 跟 recovery* 的對照。

## Replication slot × Failure × Recovery 對照

Logical replication 跟 Debezium CDC 的 production 議題集中在 *replication slot* — 它是 PostgreSQL 內保證 WAL 不被回收的 anchor point；slot 設不對、整個 CDC pipeline 失效。各 failure mode 對 slot 的影響跟 recovery 路徑：

| Failure mode               | 對 slot 影響                                | Primary 端徵兆                          | Recovery 路徑                                   |
| -------------------------- | ------------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| Consumer 卡住 / lag        | slot LSN 不前進、WAL 留著                  | `pg_wal` 目錄持續長大、disk 撐爆        | 修 consumer / 加 throttle / 必要時 drop slot   |
| Consumer crash 無 restart  | slot 留在 active state                     | 跟 lag 同、不會自動清                   | 手動 `SELECT pg_drop_replication_slot('name')` |
| Schema change（ADD COLUMN） | 多數 plugin 自動處理、無感                  | 通常無感                                | -                                               |
| Schema change（DROP / RENAME COLUMN）| 多數 plugin 直接斷                  | Consumer log 報錯、slot active 卻不前進 | 重建 publication / 重 init load                |
| Initial COPY               | slot 建立時跑 snapshot、long-running tx     | 大表 COPY 期間鎖跟 WAL 都受影響        | 用 `CREATE_REPLICATION_SLOT ... NOEXPORT_SNAPSHOT` 分階段 |
| Promotion (failover)       | physical slot 跟 logical slot 處理不同      | logical slot 在 PG 16- 不跨 failover     | PG 16+ logical slot 持久化、或 consumer 重 init load |
| Replay storm（offset 重置）| slot 不變、consumer 重讀                   | Kafka 端流量爆、application 看 duplicate | Idempotent consumer 設計、或 transactional outbox |

每個 failure mode 對應的詳細配置 + recovery 步驟、下面分段展開。

## Logical replication 基礎：publication + subscription + slot

```sql
-- Primary：建 publication
CREATE PUBLICATION app_changes FOR TABLE orders, events;

-- Subscriber：建 subscription（自動建 replication slot）
CREATE SUBSCRIPTION app_sub
  CONNECTION 'host=primary user=replicator dbname=app'
  PUBLICATION app_changes
  WITH (slot_name = 'app_sub_slot', copy_data = true);
```

關鍵物件：

- **publication**（primary 端）：宣告 *哪些表 + 哪些操作（INSERT/UPDATE/DELETE/TRUNCATE）* 對外暴露
- **subscription**（subscriber 端、若是 PG-to-PG）：訂閱 + 自動建 slot + 自動 initial COPY
- **replication slot**：primary 端、保證 *consumer 還沒消費的 WAL* 不被回收

`copy_data = true` 觸發 initial COPY（snapshot）+ 後續 streaming；`copy_data = false` 只 streaming、適合 already-in-sync 場景。

## Debezium CDC：用 logical replication slot 但繞過 subscription

Debezium 不是 PostgreSQL subscriber、是 *直接讀 replication slot* 的外部 consumer：

```properties
# Debezium PostgreSQL connector
connector.class=io.debezium.connector.postgresql.PostgresConnector
database.hostname=primary
database.dbname=app
plugin.name=pgoutput                            # 內建、PG 10+ 推薦
slot.name=debezium_app
publication.name=app_changes
publication.autocreate.mode=filtered            # debezium 自動建 publication
table.include.list=public.orders,public.events
snapshot.mode=initial                            # 起始 snapshot 後 streaming
```

差異：

- Debezium 用 `pgoutput`（PG 10+ 內建）或 `wal2json`（外掛 plugin）解 WAL、轉成結構化事件送 Kafka
- 不像 PG-to-PG subscription、Debezium 沒 subscription object、是 *外部 consumer 自管* replication slot
- Failure mode 上 *consumer 端是 Debezium 自己*、所以 lag 來源是 Debezium 處理速度 / Kafka 寫入速度

## Production 故障演練

### Case 1：consumer lag、slot LSN 不前進、primary disk 爆

**徵兆**：primary `pg_wal` 目錄持續長大、`df -h` 看磁碟 90%+；`pg_replication_slots` 看 `confirmed_flush_lsn` 卡在某 LSN、`pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)` 數十 GB。

**根因**：consumer（Debezium / subscriber）處理慢於 primary 寫入；replication slot *保證 WAL 不回收*、但 consumer 沒消費 → WAL 堆積。

**修法**：

1. **監測**：Prometheus alert `pg_replication_slot_lag_bytes > 5GB` 觸發前 catch
2. **修 consumer**：throttle primary 寫入 OR scale Debezium / subscriber 處理能力
3. **緊急**：`SELECT pg_drop_replication_slot('debezium_app')` 釋放 WAL — 但 consumer 必須重 init load（資料缺一塊）
4. **架構**：用 *max_slot_wal_keep_size*（PG 13+）設 slot 能保留 WAL 上限、超出自動 invalidate slot、保護 primary disk

### Case 2：consumer crash 後 slot 變 zombie

**徵兆**：Debezium pod OOM crash、新 pod 起來時報 `slot is active for PID X`、無法 attach；primary 端 `pg_replication_slots.active = true`、`active_pid` 指向已經死掉的 process。

**根因**：PostgreSQL 把 slot 標 active 是基於 *當下有 connection*；consumer crash 但 connection 沒被 server 端發現（network 沒 RST）、slot 留在 active state。

**修法**：

```sql
-- 手動清 zombie slot
SELECT pg_terminate_backend(active_pid) FROM pg_replication_slots
  WHERE slot_name = 'debezium_app' AND active;

-- 或直接 drop（會丟資料、consumer 要重 init）
SELECT pg_drop_replication_slot('debezium_app');
```

預防：

1. PostgreSQL `tcp_keepalives_idle / interval / count` 設較短（300 / 60 / 6）、network drop 較快被發現
2. Consumer 端用 *graceful shutdown* + `pg_terminate_backend(active_pid)` 在 startup 前主動清 stale connection

### Case 3：schema change（DROP / RENAME COLUMN）斷流

**徵兆**：Debezium consumer 突然停 produce 訊息、log 報 `column XYZ does not exist`；primary 端 slot 還 active、但 `confirmed_flush_lsn` 不前進。

**根因**：pgoutput plugin 把 WAL 解成 row event 時、用的 schema 是 *當下 catalog*；如果中間 DROP COLUMN、之前 WAL 內的 row event 含已不存在欄位、解析失敗。

**修法**：

1. **預防**：schema change 走 *expand-contract pattern*
   - Phase 1: ADD COLUMN new_col（不影響 logical replication）
   - Phase 2: application 雙寫 old + new
   - Phase 3: 等 consumer catch up old column 訊息
   - Phase 4: DROP COLUMN old_col（此時無 in-flight WAL 帶 old_col）
2. **緊急**：DROP existing slot、重建 publication 跟 slot、consumer 重 init load
3. **長期**：用 Debezium *snapshot.mode=schema_only_recovery* 在 schema 變動時不重灌資料、只 reset schema

### Case 4：initial COPY 大表鎖太久

**徵兆**：對 1TB 表跑 `CREATE SUBSCRIPTION ... WITH (copy_data=true)` 後、application 對該表 query / write 阻塞 30+ 分鐘；application timeout 大量。

**根因**：initial COPY 默認跑在 *single transaction*、整個 snapshot LSN 鎖住、長 transaction 跟 vacuum 衝突；同時對 subscriber 端鎖表寫入。

**修法**：

1. **分階段 init**：
```sql
-- Primary：建 publication 不 copy
CREATE PUBLICATION app_changes FOR TABLE big_table;

-- Subscriber：建 subscription 不 copy
CREATE SUBSCRIPTION app_sub
  CONNECTION '...'
  PUBLICATION app_changes
  WITH (copy_data = false);

-- 手動跑 partition-by-partition COPY（若是 partition table）
-- 或用 pg_dump / pg_basebackup 拿 snapshot
```
2. **PG 16+ parallel init**：`max_sync_workers_per_subscription = 4` 平行 COPY 多個表
3. **Debezium replacement**：用 incremental snapshot（Debezium 1.6+）、background trickle copy、不鎖長 transaction

### Case 5：replay storm 後 consumer offset reset

**徵兆**：Debezium 修 bug / 重 deploy 後、`snapshot.mode=initial` 觸發整個資料重灌；Kafka topic 流量爆 10x、下游 application 看到大量 duplicate event。

**根因**：Debezium offset store（Kafka topic 或 file）被誤刪 / corruption；重啟時不知道從哪 LSN 開始、預設 fall back 到 initial snapshot。

**修法**：

1. **預防**：Debezium offset store 跟 Kafka cluster *backup 一起做*、不要單獨依賴 Kafka topic
2. **架構**：consumer side 設計 *idempotent* — 用 event 自帶的 (source LSN + transaction ID) 當 dedupe key
3. **transactional outbox pattern**：CDC 只 capture outbox 表、application 主動寫 outbox + business data 在同 transaction；duplicate 由 application 自己 dedupe

## 容量規劃

| 維度                          | 估算                                                          | 警戒                                              |
| ----------------------------- | ------------------------------------------------------------- | ------------------------------------------------- |
| Replication slot lag          | `pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)`  | > 1GB lag 訊號 consumer 跟不上                    |
| Primary `pg_wal` size         | retention × peak WAL rate                                     | 預留 disk 容量 = max_slot_wal_keep_size + 30% buffer |
| Debezium throughput           | ~5-10K row/s 單 connector、多表平行可拉                       | 跟 primary write rate 對比                        |
| Initial COPY time             | 100GB ~ 10-30 分鐘（看 network + subscriber IO）              | TB 級必須分階段                                   |
| Slot 數量                     | 每 slot 佔 primary 一份 WAL 保留 buffer                       | 5+ slot 同時跑 disk 壓力倍增                      |
| max_replication_slots         | 預設 10、production 跑 CDC + standby 各佔 slot 要拉到 20-50   | 達上限會拒新 slot 建立                            |

實務 default：

- Debezium production：1 connector per source schema、不要 1 connector 跨 50 個表
- Slot retention：`max_slot_wal_keep_size = 100GB`、超出 invalidate slot 保護 primary
- Monitor cadence：1 分鐘 sample lag + 5 分鐘 alert threshold

## 整合 / 下一步

### 跟 [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) 整合

logical slot 在 PG 16- 不跨 failover、是長期痛點：

1. **PG 16-**：failover 後 logical consumer 必須重 init（slot 在新 leader 上不存在）
2. **PG 16+**：`failover` parameter 讓 logical slot 在 standby 同步、failover 後 consumer 直接接
3. Patroni 16+ 支援 logical slot persistence 配置、配合用

### 跟 Kafka outbox pattern

production-grade CDC 不直接 read business table、是 read *outbox table*：

```sql
-- Application transaction
BEGIN;
  INSERT INTO orders (...) VALUES (...);
  INSERT INTO outbox (event_type, payload, created_at) VALUES ('order_created', '...', now());
COMMIT;
```

Debezium 只 capture outbox table、event payload 已是 application-shaped JSON、不用解 row event。好處：

1. Schema change 不影響 CDC（outbox table schema 穩定）
2. 跨表 transaction 對應到單 event（outbox 是業務語意層）
3. Replay 可靠 — outbox 是 append-only、可重讀

### 跟 [partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/) 整合

partitioned table 的 logical replication：

1. PG 13+ `publish_via_partition_root = true` — publication 從 parent 角度看、不是 per-partition
2. Subscriber 端可 partition 不同 strategy（甚至不 partition）
3. Schema change 對 partition table 更複雜、走 expand-contract 嚴格

### 下一步議題

- **Logical replication conflict**：subscriber 端寫衝突的處理（PG 17+ 加 conflict resolution）
- **bi-directional replication（pg_active）**：多 region active-active、衝突解決設計
- **Decoder plugin 對比**：pgoutput / wal2json / decoderbufs 效能跟易用性

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 上游 chapter：[Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/) — schema change × CDC 對應
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
