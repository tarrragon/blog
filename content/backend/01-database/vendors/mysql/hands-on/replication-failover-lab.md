---
title: "MySQL Replication Failover Lab"
date: 2026-05-22
description: "MySQL source / replica、replication lag、promotion、client route、Orchestrator frame 與 validation evidence"
tags: ["backend", "database", "mysql", "hands-on", "replication", "failover"]
---

MySQL replication failover lab 的核心責任是讓讀者觀察 source / replica 拓撲在 promotion 時的資料與 client route。這篇承接 [Replication Topology](../../replication-topology/) 與 [Orchestrator Failover](../../orchestrator-failover/)。

本文的驗收標準是：你能記錄 replication status、lag、promotion timeline、client error sample、validation query 與 incident decision log。

## Baseline Replication

Baseline replication 的核心責任是先保存 source / replica 狀態。實際建立 replication 依 GTID、binlog file position、Docker topology 或 managed service 而異；本文聚焦演練 evidence。

```sql
SHOW REPLICA STATUS\G
SHOW BINARY LOG STATUS;
```

Baseline 要記錄：

1. Source host / replica host。
2. GTID executed / retrieved。
3. IO thread / SQL thread。
4. Seconds behind source。
5. Read endpoint / write endpoint。

## Client Workload

Client workload 的核心責任是讓 failover 對 application 可見。

```bash
while true; do
  mysql -h "$MYSQL_WRITE_HOST" -u app_user -papp_pw appdb \
    -e "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key) VALUES (1, 1, UUID());"
  sleep 1
done
```

這個 synthetic workload 產生成功、timeout、duplicate、read-only 或 connection error。正式演練要避免碰 production side effect。

## Promotion Frame

Promotion frame 的核心責任是把 failover action 寫成可審查步驟。

```text
failover_start:
old_source:
candidate_replica:
lag_before:
promotion_method:
accepted_data_loss:
operator:
```

Managed service、Orchestrator 或手動 promotion 都要留下同樣欄位。工具不同，決策證據一致。

## Validation

Validation 的核心責任是確認 promoted instance 可讀寫且資料符合預期。

```sql
SELECT COUNT(*) FROM ledger_entries;
SELECT MAX(created_at) FROM ledger_entries;
SHOW VARIABLES LIKE 'read_only';
SHOW VARIABLES LIKE 'super_read_only';
```

若使用 GTID，還要比較 source / replica 的 GTID set。若有 external side effect，要用 idempotency key 做 [reconciliation](/backend/knowledge-cards/data-reconciliation/)。

## Client Route

Client route 的核心責任是確認 application、ProxySQL、DNS 或 secret 已指向新 writer。

檢查項目：

1. Write endpoint 是否更新。
2. ProxySQL writer hostgroup 是否切換。
3. Application pool 是否清掉舊連線。
4. Retry 是否有 backoff。
5. Read replica 是否重新掛到新 source。

Failover 完成標準包含資料庫 promotion 與 client route 穩定。只 promote 成功，application 仍可能寫到舊 endpoint。

## Incident Log

Incident log 的核心責任是把演練結果保存。

```text
Drill id:
RTO observed:
RPO / accepted data loss:
Client errors:
Validation:
Follow-up:
```

完成本篇後，拓撲設計讀 [Replication Topology](../../replication-topology/)；自動化工具讀 [Orchestrator Failover](../../orchestrator-failover/)；routing 讀 [ProxySQL Routing Lab](../proxysql-routing-lab/)。
