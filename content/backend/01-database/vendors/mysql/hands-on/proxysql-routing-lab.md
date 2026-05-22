---
title: "MySQL ProxySQL Routing Lab"
date: 2026-05-22
description: "MySQL ProxySQL hostgroup、read/write split、query rule、backend health 與 routing evidence"
tags: ["backend", "database", "mysql", "hands-on", "proxysql"]
---

MySQL ProxySQL routing lab 的核心責任是讓讀者看到 database proxy 如何把 application query 導向不同 hostgroup。這篇承接 [ProxySQL Config](../../proxysql-config/)。

本文的驗收標準是：你能定義 writer / reader hostgroup、建立 query rule、觀察 routing stats，並寫下 stale read 與 failover 風險。

## Hostgroup Model

Hostgroup model 的核心責任是把 backend 分成 writer 與 reader。

```text
hostgroup 10: writer
hostgroup 20: reader
```

在單節點 lab 中，writer / reader 可以先指向同一 MySQL；正式環境應用 replica 作 reader，並搭配 replication lag guard。

## Query Rule

Query rule 的核心責任是示範 routing policy。

```sql
-- Conceptual ProxySQL admin commands. Adjust host / credential for your lab.
INSERT INTO mysql_query_rules(rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES
  (10, 1, '^SELECT', 20, 1),
  (20, 1, '.*', 10, 1);
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL QUERY RULES TO DISK;
```

這個規則把 `SELECT` 導向 reader，其餘導向 writer。Production 要排除 `SELECT ... FOR UPDATE`、transaction、read-after-write 與 session state。

## Routing Evidence

Routing evidence 的核心責任是確認 query 真的走到預期 hostgroup。

```sql
SELECT hostgroup, srv_host, Queries
FROM stats_mysql_connection_pool;

SELECT rule_id, hits
FROM stats_mysql_query_rules
ORDER BY rule_id;
```

Evidence 要和 application log 對齊。若某個 workflow 寫後立刻讀，routing rule 要保證它走 writer 或具備 freshness policy。

## Failure Note

Failure note 的核心責任是記錄 proxy 常見風險。

| 風險              | 控制方式                               |
| ----------------- | -------------------------------------- |
| Stale read        | lag guard、read-after-write to writer  |
| Transaction split | transaction pinning、query rule review |
| Bad regex         | query digest / allowlist               |
| Backend unhealthy | health check、hostgroup failover       |
| Credential drift  | ProxySQL user sync / secret rotation   |

完成本篇後，完整設定讀 [ProxySQL Config](../../proxysql-config/)；replica 與 failover 讀 [Replication Failover Lab](../replication-failover-lab/)。
