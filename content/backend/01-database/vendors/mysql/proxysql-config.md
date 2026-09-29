---
title: "MySQL ProxySQL 配置：connection / query / route / response 四段 lifecycle 跟 query rule 設計"
date: 2026-05-19
description: "ProxySQL 是 MySQL 生態的 connection pool + query routing 標準。本文走 connection → query parse → route → response 四段 lifecycle、query rule engine 的 rule chain 設計、Hostgroup / Server / User 三層 schema、配置 step-by-step（讀寫分離 + replica lag-aware routing）、5 production 踩雷（query rule 順序錯亂 / connection 漂移 / write 路由到 replica / runtime / disk schema drift / mirror traffic 副作用）、跟 Replication / Orchestrator / HAProxy 整合"
weight: 14
tags: ["backend", "database", "mysql", "proxysql", "connection-pool", "deep-article"]
---

> 這篇涵蓋 ProxySQL 的配置：query 從 connection 接入、query parse 與 rule match、backend route 到 response 返回的 lifecycle，以及 rule chain 設計。

---

## ProxySQL Lifecycle：每個 query 走 4 段

從 application 連 ProxySQL 到拿到 response、每個 query 都走完整 4 段：

```text
1. Connection 接入        →  application connect 到 ProxySQL（不是 MySQL）
2. Query parse + rule match  → ProxySQL 解析 query、match query rule chain
3. Backend route          →  決定走哪個 hostgroup（primary / replica）+ 哪個 server
4. Response 返回          →  將 result set 回 application、connection 可被 reuse
```

lifecycle 的每一段都有自己的配置、failure mode 與觀測 metric。ProxySQL 不是 *簡單的 connection pool*、是 *query-aware proxy* — 看得到 SQL 內容才能做 [read/write split](/backend/knowledge-cards/read-write-split/)、replica lag-aware routing、query mirroring。

跟 [PostgreSQL pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/) 比、pgBouncer 是 *transaction-level pool*（只看連線、不看 SQL）、ProxySQL 是 *query-level proxy*（看 SQL、做 routing decision）。能力不同、target use case 不同。

## Connection 接入：Hostgroup / Server / User 三層 schema

ProxySQL 不直接 expose backend MySQL、用 *hostgroup* 作為 routing 抽象。Application 不知道有幾個 backend、只知道 ProxySQL。

**核心 table（在 `main` database）**：

| Table                          | 角色                                                                 |
| ------------------------------ | -------------------------------------------------------------------- |
| `mysql_servers`                | 列每個 backend MySQL server、屬於哪個 hostgroup                      |
| `mysql_replication_hostgroups` | 定義 writer hostgroup ↔ reader hostgroup 配對、自動偵測 primary 切換 |
| `mysql_users`                  | 列允許連 ProxySQL 的 application user、預設 hostgroup                |
| `mysql_query_rules`            | Query rule chain、決定哪個 query 走哪個 hostgroup                    |

**典型部署**：

```sql
-- 進 ProxySQL admin (6032 port)
mysql -uadmin -padmin -h127.0.0.1 -P6032

-- 設 2 個 hostgroup：10=writer、20=reader
INSERT INTO mysql_servers(hostgroup_id, hostname, port, weight, max_connections)
VALUES
  (10, 'primary.example.com', 3306, 1000, 200),
  (20, 'replica1.example.com', 3306, 1000, 100),
  (20, 'replica2.example.com', 3306, 1000, 100);

-- 自動偵測 primary（用 read_only flag）
INSERT INTO mysql_replication_hostgroups(writer_hostgroup, reader_hostgroup, comment)
VALUES (10, 20, 'production cluster');

-- 設 application user、default_hostgroup 設 10（writer）：沒被任何 query rule 命中的 INSERT / UPDATE / DELETE 落到這裡
INSERT INTO mysql_users(username, password, default_hostgroup, max_connections)
VALUES ('app', 'app_password', 10, 1000);

-- 套用設定到 runtime
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL USERS TO RUNTIME;

-- 持久化到 disk（重啟保留）
SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL USERS TO DISK;
```

注意 ProxySQL 的 *三層 state*：`disk`（持久化）→ `memory`（編輯區）→ `runtime`（實際運作）。每次改完要 `LOAD ... TO RUNTIME` 才生效、`SAVE ... TO DISK` 才能 reboot 保留。沒 `SAVE` 重啟後 config 消失是新手最常踩的雷。

## Query Parse 與 Rule Match：query rule engine

ProxySQL 不只 forward connection、看 *SQL 內容* 決定怎麼 route。Query rule 是 *ordered chain*、match 第一個符合的 rule。

**Query rule 核心欄位**：

| 欄位                    | 意義                                                              |
| ----------------------- | ----------------------------------------------------------------- |
| `rule_id`               | 排序（越小越先 match）                                            |
| `match_pattern`         | regex 比對 SQL（支援 `^SELECT` / `FOR UPDATE` 等）                |
| `destination_hostgroup` | match 後送哪個 hostgroup                                          |
| `apply`                 | match 後是否停 chain（1=stop、0=繼續看後面 rule）                 |
| `cache_ttl`             | result cache TTL（毫秒）— ProxySQL 內建 query cache               |
| `mirror_hostgroup`      | query 鏡像送到第二個 hostgroup（不等 response、用於 shadow test） |

**典型讀寫分離 rule**：

```sql
-- Rule 100: SELECT ... FOR UPDATE 必須走 primary
INSERT INTO mysql_query_rules(rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (100, 1, '^SELECT.*FOR UPDATE$', 10, 1);

-- Rule 200: 一般 SELECT 走 replica（reader）
INSERT INTO mysql_query_rules(rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (200, 1, '^SELECT', 20, 1);

-- Rule 300: BEGIN / START TRANSACTION 走 primary
INSERT INTO mysql_query_rules(rule_id, active, match_pattern, destination_hostgroup, apply)
VALUES (300, 1, '^(BEGIN|START TRANSACTION)', 10, 1);

-- 其他（INSERT / UPDATE / DELETE）預設走 default_hostgroup（user 設的）
-- application user default 設 10 (writer)、所以寫入自動走 primary

LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL QUERY RULES TO DISK;
```

**Rule 順序很重要**：`rule_id` 100 先 match、200 再 match、依此類推。Rule 200 比 100 寬鬆（任何 SELECT）、所以 `FOR UPDATE` 必須先 match rule 100 才不會誤送 replica。

## Backend Route：replica lag-aware 與 circuit breaker

Rule match 後 ProxySQL 從 hostgroup 內挑一個 server。Backend selection 不是 pure round-robin、考慮：

- *Weight*：每個 server `weight` 比例分配（典型用於 replica capacity 不同）
- *Replica lag*：若 hostgroup 設 `max_replication_lag`、lag 超過 threshold 的 replica 自動暫時退出
- *Connection count*：避免某個 server connection 滿
- *Server status*：`mysql_servers.status` (ONLINE / SHUNNED / OFFLINE_SOFT / OFFLINE_HARD) 決定是否可用

**Replica lag-aware routing 配置**：

```sql
-- 給整個 reader hostgroup 設 lag threshold
UPDATE mysql_servers
SET max_replication_lag = 5  -- 秒
WHERE hostgroup_id = 20;

LOAD MYSQL SERVERS TO RUNTIME;
```

ProxySQL 內部用 *monitor module* 定期跑 `SHOW SLAVE STATUS`、lag 超過 5 秒 → 該 replica 暫時退出 reader hostgroup。讀 query 自動避開 lagging replica。

**Circuit breaker（自動 shun）**：server 連續失敗 → ProxySQL 自動 `SHUNNED`、避免持續打 broken server。但 *application 層仍要處理 retry*、ProxySQL 不保證 query 100% 成功。

## Response 返回：connection multiplexing

ProxySQL 對 application connection 跟 backend connection 是 *N:M 多工*：

- Application connection 跟 ProxySQL 1:1
- ProxySQL 跟 backend MySQL connection 共用 pool（multiplexing）

**Multiplexing 條件**：

- Transaction 內：connection 綁定特定 backend（保 transaction atomicity）
- 跨 transaction：connection 可以換 backend
- `SET` statement 改 session variable：connection 黏死 backend（防 session state leak）
- User variable（`@var`）：connection 黏死 backend

**結果**：application 看到的是「自己有 1000 個 connection」、ProxySQL 後端可能只有 100 connection 到 MySQL。對 connection-bound MySQL（max_connections 限制）是關鍵 cost saving。

## 5 個 Production 踩雷

### Query rule 順序錯亂：`FOR UPDATE` 被一般 SELECT rule 送到 replica

寬鬆的 `^SELECT` rule 拿到比 `^SELECT.*FOR UPDATE$` 更小的 `rule_id`（例如寬鬆 rule 編成 100、精確 rule 編成 200）。ProxySQL 依 `rule_id` 由小到大比對，`SELECT ... FOR UPDATE` 先命中寬鬆 rule，而那條 rule 的 `apply=1` 讓比對停下，query 被送到 replica；replica 上沒有對應的 row lock，application 以為自己持有 lock，併發交易之間出現 race condition。

修法：

- `rule_id` 排序：精確 rule（多條件 regex）放小、寬鬆 rule 放大
- 用 `apply=1` 強制停 chain、不要讓 query 繼續往下 match
- 跑 ProxySQL `SHOW PROCESSLIST` + audit log 確認 routing 正確

### Connection 漂移：multiplexing 換了 backend connection 之後的 session variable

Application 跑 `SET sql_mode=...` 之後，下一個 SELECT 被 query rule 送到 reader hostgroup，用的是另一條 backend connection。ProxySQL 對 `sql_mode` 這類它有追蹤的 session 變數，會把值記在 client session 上，換到另一條 backend connection 時先在那條連線上補設同一個值：`SET sql_mode='ANSI_QUOTES'` 在 hostgroup 10 執行之後，接著送到 hostgroup 20 的 `SELECT @@sql_mode` 回的仍是 `ANSI_QUOTES`。漂移發生在 ProxySQL 沒有追蹤的 session 狀態上；追蹤清單隨 ProxySQL 版本變動，以手上版本的官方文件為準。

修法：

- 用 `mysql-multiplexing=false` 全 disable（最簡單但浪費 connection pool 效率）
- 或把 application 每條連線都要先跑的 `SET` 寫進全域變數 `mysql-init_connect`，ProxySQL 每開一條 backend connection 就先執行它
- 避免 application 中途改 session variable，改成全部走 `mysql-init_connect`

### Write 不小心 route 到 replica：`default_hostgroup` 設錯

Application user `default_hostgroup` 設 20 (reader)、INSERT / UPDATE / DELETE 沒 match 到任何 rule（沒寫 catch-all write rule）、走 default → 送 replica → replica 是 read-only → error。或更糟：replica 不是 read-only mode、寫入 *寫到 replica 上*、replication 反向不同步、data corruption。

修法：

- Application user `default_hostgroup` 設 10 (writer) — 寫入預設走 primary
- Replica MySQL 一定要 `read_only=1`（防 stale write 寫到 replica）
- 監控 `mysql_query_rules` match 率、寫入 query 應該大部分透過 default_hostgroup 路由、不是個別 rule

### Runtime / disk schema drift：改了 runtime 沒 save、重啟 config 消失

`LOAD ... TO RUNTIME` 跟 `SAVE ... TO DISK` 是兩個獨立操作。On-call 在事故中改 ProxySQL 配置（add server、調 query rule）、`LOAD` 套到 runtime 但忘記 `SAVE`、隔天 ProxySQL 重啟（OS update / crash）、config 回到 disk 版本、半夜 alert。

修法：

- 每次 `LOAD ... TO RUNTIME` 後立刻 `SAVE ... TO DISK`（變成 habit）
- 用 IaC（Terraform / Ansible）管 ProxySQL config、不要手動改 admin
- 監控：對比 `runtime_mysql_servers` 跟 `disk.mysql_servers`、有 diff 即告警（`main.mysql_servers` 是 memory 那一層，`LOAD` 之後它與 runtime 一致、比不出沒有 `SAVE` 的情形）

### Mirror traffic 副作用：INSERT 鏡像到 staging 寫了兩次

`mirror_hostgroup` 把 query 鏡像送到第二個 hostgroup（不等 response、用於 shadow test 新 schema）。但 *鏡像是真實執行*、不是 dry-run。鏡像 INSERT 到 staging hostgroup → staging 真的多了 row。如果 staging hostgroup 接到 production 表（誤接）、production 寫入 doubled。

修法：

- Mirror 只用於 *獨立 staging cluster*、不混用 production schema
- Mirror 設定要 review（規則 `match_pattern` 跟 `mirror_hostgroup` 配對）
- 開 mirror 前在 staging 跑 dry-run、確認 schema 跟 production isolated

## 容量規劃要點

對 100 application instance × 50 connection / instance = 5000 application connection 場景：

| 配置                     | ProxySQL 設定                                | MySQL backend 配置                                     |
| ------------------------ | -------------------------------------------- | ------------------------------------------------------ |
| Application → ProxySQL   | `mysql-max_connections=10000`                | 不影響                                                 |
| ProxySQL → MySQL primary | `max_connections=200`（per server）          | MySQL `max_connections=300`（多 100 buffer for admin） |
| ProxySQL → MySQL replica | `max_connections=200`（per server）          | 同上                                                   |
| ProxySQL 數量（HA）      | 至少 2 instance（HAProxy / VIP）             | -                                                      |
| Memory per ProxySQL      | 2-4 GB（query rule cache + connection pool） | -                                                      |

ProxySQL 本身需要 HA：放兩個 instance 後面接 VIP（keepalived）或 HAProxy。Application 連 VIP / HAProxy、不直接連 ProxySQL hostname（單點失效）。

## 跟其他模組整合

### 跟 Replication topology

ProxySQL 透過 *monitor module* 自動偵測 primary（檢查 `read_only` flag）+ replica lag（檢查 `Seconds_Behind_Master`）。這個 monitor 依賴 MySQL replication 已配好（GTID + binlog ROW format）。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 Orchestrator HA

Orchestrator 自動 failover 後新 primary 的 `read_only` flag 變 0、舊 primary 變 1。ProxySQL monitor 偵測到、自動把 hostgroup 10（writer）的 server 切換、application 不必改 connection string。

Orchestrator 自己怎麼做 HA 與怎麼挑新 primary，見 [MySQL Orchestrator Failover](/backend/01-database/vendors/mysql/orchestrator-failover/)。

### 跟 OSC tool（gh-ost / pt-osc）

ProxySQL 可以 *暫時 throttle* application 對某張表的寫入（query rule `delay` 欄位）、配合 OSC tool cut-over 時段降低 metadata lock 衝突。

詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

### 跟 Aurora MySQL / RDS Proxy

Aurora MySQL 推 *RDS Proxy*（AWS managed proxy）取代 ProxySQL — 跟 IAM 整合、failover < 30 秒。但 RDS Proxy *沒有 query routing rule engine*（只做 connection pool）、不能讀寫分離。Aurora user 仍可能用 ProxySQL 在前面、再用 RDS Proxy 作 backend connection pool。

詳見 [Aurora vendor page](/backend/01-database/vendors/aurora/)。

### 跟 PostgreSQL pgBouncer 對比

| 維度              | ProxySQL（MySQL）   | pgBouncer（PostgreSQL）        |
| ----------------- | ------------------- | ------------------------------ |
| 抽象層            | Query-level proxy   | Transaction-level pool         |
| Query routing     | 內建（rule engine） | 無（不看 SQL）                 |
| Connection pool   | 內建                | 核心功能                       |
| Read/write split  | 內建（自動 + rule） | 要 application 層或 HAProxy 配 |
| Replica lag-aware | 內建                | 無                             |
| Query cache       | 內建                | 無                             |

ProxySQL 是 *query 層中介*、pgBouncer 是 *connection 層中介*。詳見 [pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/)。

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)（read replica routing 前提）
- [MySQL Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)（OSC + ProxySQL throttle 整合）
- [PostgreSQL pgBouncer](/backend/01-database/vendors/postgresql/pgbouncer-config/)（PG sibling、不同抽象層）
- [Aurora vendor page](/backend/01-database/vendors/aurora/)（RDS Proxy + ProxySQL 取捨）
- [Connection Pool 卡片](/backend/knowledge-cards/connection-pool/)
- 官方：[ProxySQL Documentation](https://proxysql.com/documentation/)
