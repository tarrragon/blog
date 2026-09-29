---
title: "MySQL ProxySQL Routing Lab"
date: 2026-05-22
description: "MySQL ProxySQL hostgroup、read/write split、query rule、backend health 與 routing evidence"
tags: ["backend", "database", "mysql", "hands-on", "proxysql"]
---

MySQL ProxySQL routing lab 的核心責任是讓讀者看到 database proxy 如何把 application query 導向不同 hostgroup。這篇承接 [ProxySQL Config](../../proxysql-config/)。

本篇的範圍是在單節點 lab 上設定 ProxySQL 的 writer / reader hostgroup 與 query rule、從 routing stats 確認 query 落在哪個 hostgroup，並整理 stale read、transaction split 與 failover 等 proxy 風險的控制方式。

## Hostgroup Model

Hostgroup model 的核心責任是把 backend 分成 writer 與 reader。

```sql
-- 在 ProxySQL 所在的機器上連 admin interface：mysql -u admin -padmin -h 127.0.0.1 -P 6032
-- hostgroup 10 是 writer、20 是 reader；單節點 lab 讓兩個 hostgroup 指向同一個 MySQL
-- hostname 填 ProxySQL 連得到的 MySQL 位址：與 local lab 同一個 compose 時是 service 名稱 mysql
INSERT INTO mysql_servers(hostgroup_id, hostname, port)
VALUES (10, 'mysql', 3306), (20, 'mysql', 3306);
-- application 用這組帳密連 ProxySQL，ProxySQL 也用它連 backend；沒命中任何 query rule 的 query 走 default_hostgroup
INSERT INTO mysql_users(username, password, default_hostgroup)
VALUES ('app_user', 'app_pw', 10);
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL USERS TO RUNTIME;
```

在單節點 lab 中，writer / reader 先指向同一 MySQL；正式環境應用 replica 作 reader，並搭配 replication lag guard。

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

Routing evidence 的核心責任是確認 query 真的走到預期 hostgroup。先讓 application 的 query 經過 ProxySQL：連 ProxySQL 的 6033，而不是直連 MySQL。

```bash
# 在 ProxySQL 所在的機器上連 6033（ProxySQL 的 application port）
mysql -u app_user -papp_pw -h 127.0.0.1 -P 6033 appdb -e "SELECT COUNT(*) FROM accounts;"
mysql -u app_user -papp_pw -h 127.0.0.1 -P 6033 appdb -e "SELECT id FROM accounts WHERE id = 1 FOR UPDATE;"
mysql -u app_user -papp_pw -h 127.0.0.1 -P 6033 appdb \
  -e "INSERT INTO ledger_entries(account_id, amount_cents, idempotency_key) VALUES (1, 5, 'proxy-1');"
```

再回 admin interface 查 stats：

```sql
SELECT hostgroup, srv_host, Queries
FROM stats_mysql_connection_pool;
-- hostgroup 20 收到 2 個 query：兩句 SELECT，包含 FOR UPDATE 那一句
-- hostgroup 10 收到 1 個 query：INSERT

SELECT rule_id, hits
FROM stats_mysql_query_rules
ORDER BY rule_id;
-- rule 10（^SELECT）hits 2、rule 20（.*）hits 1
```

`SELECT ... FOR UPDATE` 被 `^SELECT` 導到 reader，就是上面 Query Rule 段要 production 排除它的原因。

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
