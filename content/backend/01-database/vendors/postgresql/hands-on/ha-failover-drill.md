---
title: "PostgreSQL HA Failover Drill"
date: 2026-05-22
description: "PostgreSQL Patroni 或 managed failover 的 promotion、client reconnect、pooler behavior 與 incident timeline"
tags: ["backend", "database", "postgresql", "hands-on", "failover"]
---

PostgreSQL HA failover drill 的核心責任是讓讀者觀察 primary promotion 對 application、pooler 與 incident decision 的影響。這篇承接 [Patroni HA](../../patroni-ha/) 與 [Cross-region DR](../../cross-region-dr/)。

本文的驗收標準是：你能記錄 failover timeline、replication lag snapshot、client error sample、data validation query 與 incident decision log entry。實際觸發方式依 Patroni、managed PostgreSQL 或雲平台而異；lab 重點是 evidence。

## Pre-Failover Baseline

Pre-failover baseline 的核心責任是確認 primary / standby 狀態與 client route。

```sql
SELECT pg_is_in_recovery();
SELECT now(), pg_current_wal_lsn();
SELECT application_name, state, sync_state, replay_lag
FROM pg_stat_replication;
```

在 standby 查：

```sql
SELECT pg_is_in_recovery();
SELECT now(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

Baseline 要保存 primary host、standby host、replication lag、application connection string、pooler route 與 current timeline。

## Client Workload

Client workload 的核心責任是讓 failover 對 application 的影響可見。

```bash
while true; do
  date -u
  psql "$DATABASE_URL" -c "INSERT INTO restore_markers(marker) VALUES ('failover-drill') RETURNING id, created_at;"
  sleep 1
done
```

這個 loop 會在 failover 期間產生成功、timeout、connection reset 或 read-only error。正式演練要用 synthetic workload，避免影響真實使用者。

## Trigger Failover

Trigger failover 的核心責任是以受控方式促成 promotion。Patroni lab 可以用 `patronictl failover`；managed service 則用 provider failover / reboot with failover 功能。

```text
failover_start_time:
trigger_method:
old_primary:
candidate:
operator:
reason:
```

Failover 觸發前要先確認這是演練，並且 workload、backup、rollback 與 stakeholder 都已對齊。

## Observe Promotion

Observe promotion 的核心責任是記錄資料庫與 client 的時間線。

| 時間點               | Evidence                        |
| -------------------- | ------------------------------- |
| Trigger issued       | command / provider event        |
| Old primary down     | connection error / health check |
| New primary promoted | `pg_is_in_recovery() = false`   |
| Client reconnect     | first successful write          |
| Pooler stable        | pool queue / server connection  |
| Validation complete  | row count / marker sequence     |

Promotion timeline 要保留秒級時間戳。這是評估 RTO、client retry 與 pooler behavior 的基礎。

## Data Validation

Data validation 的核心責任是確認 failover 後資料一致性。

```sql
SELECT count(*) FROM restore_markers WHERE marker = 'failover-drill';
SELECT max(created_at) FROM restore_markers;
SELECT status, count(*) FROM accounts GROUP BY status;
```

若 workload 有 idempotency key，還要檢查 duplicate。若外部 side effect 參與交易，例如 payment 或 queue，必須有 [reconciliation](/backend/knowledge-cards/data-reconciliation/) query。

## Pooler and Client Behavior

Pooler and client behavior 的核心責任是確認 failover 後連線能重新指向新 primary。

檢查項目：

1. Application retry 是否有 backoff / jitter。
2. PgBouncer / proxy 是否清掉舊 server connection。
3. DNS / endpoint TTL 是否符合 RTO。
4. Read-only error 是否被正確分類。
5. Migration / background job 是否暫停。

Failover 的完成標準包含 database promote、client reconnect 與 pooler stable。若 client 長時間連到舊 primary 或 pooler 卡住，服務仍處於 unavailable 狀態。

## Incident Decision Log

Incident decision log 的核心責任是把演練變成可審查紀錄。

```text
Incident / drill id:
Decision: promote standby
Reason:
Accepted data loss:
RTO observed:
Client impact:
Validation result:
Follow-up:
```

每次 drill 都要產生 follow-up。常見 follow-up 是調整 retry、降低 DNS TTL、補 pooler command、增加 validation query 或改善 monitoring。

## 下一步路由

完成本篇後，HA 架構讀 [Patroni HA](../../patroni-ha/)；跨區災難復原讀 [Cross-region DR](../../cross-region-dr/)；connection retry 與 pooler 行為讀 [Connection Pool Lab](../connection-pool-lab/)。
