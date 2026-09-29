---
title: "PostgreSQL BDR / Multi-Master：用 BDR、pgEdge、Bucardo 做 active-active 寫入跟 conflict 治理"
date: 2026-05-19
description: "PG 預設是 single-primary、active-active 多寫入入口需要 *BDR (EDB)* / *pgEdge* / *Bucardo* 等 extension。本文走 3 種 multi-master 方案對比、conflict detection + resolution model、async vs sync 取捨、配置 step-by-step（pgEdge 為主）、5 production 踩雷（last-write-wins data loss / sequence collision / DDL replication / conflict log 治理 / failover 後 timeline 分歧）、跟 MySQL Group Replication sibling 對比"
weight: 20
tags: ["backend", "database", "postgresql", "multi-master", "bdr", "active-active", "deep-article"]
---

> 這篇涵蓋 PostgreSQL 靠 extension 做到的 multi-master / active-active replication：BDR、pgEdge、Bucardo 的對比、conflict model、配置與 production 踩雷。

---

## PG 預設沒 multi-master、得用 extension

PG core 是 *single-primary streaming replication*：

- 寫入只能進 primary
- Standby 接受 read（hot_standby）但拒絕 write
- Failover 後新 primary 接管、不能多入口

對需要 *active-active*（多 region 各自接受 local write）的場景、PG 提供 3 條 extension 路徑：

| 方案        | 來源              | 機制                               | License          |
| ----------- | ----------------- | ---------------------------------- | ---------------- |
| **BDR**     | EDB（Enterprise） | Logical replication-based、雙向    | 商業（EDB 訂閱） |
| **pgEdge**  | pgEdge Inc.       | 基於 BDR、開源、加 Spock extension | 開源（Spock）    |
| **Bucardo** | community         | Trigger-based、async、Perl 寫      | 開源（BSD）      |

每條路徑有不同 trade-off。對 99% PG production case、*不需要 multi-master* — single-primary streaming replication + read replica scaling 已夠。Multi-master 是 *特殊需求*（跨 region active-active write / 不可中斷 maintenance）才上。

跟 [MySQL Group Replication](/backend/01-database/vendors/mysql/group-replication/) 對比：MySQL GR 是 *官方內建*（5.7+）、PG 沒對應內建選項。MySQL 用戶 GR / InnoDB Cluster 直接套、PG 用戶要選 extension + license trade-off。

## BDR、pgEdge、Bucardo 對比

### BDR (EDB Postgres Distributed)

EDB 商業 distributed 方案、跑在 EDB Postgres Advanced Server 或 PG community 上。

**特性**：

- 雙向 logical replication、N-way active-active
- Built-in conflict detection + resolution（LWW / column-level / user-defined）
- Eager（sync）跟 async 兩種 mode
- Tightly integrated with EDB tooling

**Trade-off**：

- 商業 license、EDB 訂閱
- 對 cross-region multi-master 成熟（北美 enterprise 廣用）
- 對 *新 PG version* 通常滯後幾個月

### pgEdge（基於 Spock extension）

pgEdge 開源 multi-master、基於 *Spock* extension（從 BDR 衍生）：

**特性**：

- 開源、可自管
- 跟 BDR 架構接近、無 license fee
- Conflict resolution 用 LWW + column-level
- 對 *edge / 地理分散* 場景設計

**Trade-off**：

- 較新（2023+）、社群驗證度低於 BDR
- Conflict resolution policy 比 BDR 簡單
- 部分 EDB 商業 feature 沒對應

### Bucardo

PG community async multi-master、Perl 寫、trigger-based：

**特性**：

- 完全開源
- Trigger-based（不依賴 logical replication）
- 支援 multi-source replication（fan-in / fan-out）

**Trade-off**：

- Async only — *higher latency conflict*
- Trigger overhead（影響 primary 寫吞吐）
- 維護 Perl + tools chain 不普及
- 對 *Sync 一致性* 需求不適用

## Multi-Master Conflict Model

任何 multi-master 方案都要解決 *同一 row 兩地同時改* 的 conflict：

### Conflict 來源

```text
Region A (primary 1)          Region B (primary 2)
UPDATE orders                 UPDATE orders
SET status='shipped'          SET status='cancelled'
WHERE id=100                  WHERE id=100
     ↓                              ↓
   合併？哪個贏？
```

兩個 region 各自 commit 之後，extension 在套用對方送來的變更時才發現同一 row 已被本地改過；這時由 extension 照事先設定的 resolution 策略處理，下面四種策略裡 LWW、column-level 與 user-defined trigger 由 extension 自動處理，manual reconciliation 則把 conflict 寫進 log table 交給人處理。

### Conflict Resolution Strategies

**1. Last-Write-Wins (LWW)** — 最常見：

- 比較 transaction commit timestamp、晚的贏
- 簡單但 *data loss*（前一個 commit 的變更被覆蓋）
- 需要 *clock 同步*（NTP）—  clock skew 造成不可預測

**2. Column-level conflict resolution**：

- 不同 column 各自 LWW（status column 跟 amount column 獨立解）
- 比 row-level LWW 細、但需 application semantics 配合

**3. User-defined trigger**：

- 寫 PG function 解 conflict
- 對 *特殊 business logic*（如：金額相加、不是覆蓋）有用
- 維護成本高

**4. Manual [reconciliation](/backend/knowledge-cards/data-reconciliation/)**：

- Conflict 寫進 log table、application / DBA 手動處理
- 對 *無法自動 resolve* 場景（如金融）
- 高 ops cost

對 99% case 用 LWW、接受 small data loss、application 設計 *idempotent / commutative* 操作避免衝突。

### Conflict 機率取決於 application pattern

- *Tenant-isolated* application（user_id 各自寫自己的 row）：基本無 conflict
- *Shared counter / inventory* application：高 conflict、multi-master 不適合
- *Append-only event log*：conflict 低、適合 multi-master

## 配置 step-by-step（pgEdge 為主）

pgEdge 開源、最常見的 self-hosted 選擇。

### 在每個 region node 裝 pgEdge

```bash
# Install pgEdge CLI
curl -fsSL https://pgedge-upstream.s3.amazonaws.com/REPO/install.py | python3

# Setup PG + Spock + pgEdge
./pgedge install pg16
./pgedge install spock
```

### 在每個 node 建立 Spock node

```sql
-- 在 node1（us-east） 跑
SELECT spock.node_create(node_name := 'node1', dsn := 'host=node1.example.com port=5432 dbname=production');

-- 在 node2（eu-west）跑
SELECT spock.node_create(node_name := 'node2', dsn := 'host=node2.example.com port=5432 dbname=production');
```

### 建 replication set 並互相 subscribe

```sql
-- 在 node1 建 default replication set + 加 tables
SELECT spock.repset_add_all_tables('default', ARRAY['public']);

-- 在 node1 subscribe node2
SELECT spock.sub_create(
    subscription_name := 'sub_n1_n2',
    provider_dsn := 'host=node2.example.com port=5432 dbname=production'
);

-- 在 node2 subscribe node1（雙向）
SELECT spock.sub_create(
    subscription_name := 'sub_n2_n1',
    provider_dsn := 'host=node1.example.com port=5432 dbname=production'
);
```

### 設 conflict resolution

```sql
-- 設 LWW（預設；截至 2026-09 的 Spock 文件，last_update_wins 是唯一支援的值，需要 track_commit_timestamp = on）
ALTER SYSTEM SET spock.conflict_resolution = 'last_update_wins';
SELECT pg_reload_conf();
```

### 驗證 subscription 狀態與 replication lag

```sql
-- 看 subscription 狀態
SELECT * FROM spock.subscription;

-- 看 replication lag
SELECT * FROM pg_stat_replication;
```

## Production 踩雷

### LWW data loss — Application 沒設計 commutative

LWW 預設、兩 region 同時 UPDATE 同 row → 晚的 commit 贏、早的丟失。Application 看不到「我寫的不見了」、debug 困難。

修法：

- Application schema 設計 *tenant-isolated*（user_id 各自寫自己 row）
- 對 *shared counter / inventory* 用 *commutative operation*（INCREMENT not SET）
- 重要寫入加 *audit log* — conflict 仍寫到 audit、application 看 audit 知道發生過
- 真的需要 strict consistency 別用 multi-master、用 single-primary + reader 或 distributed SQL

### Sequence collision — 兩個 region 各自 nextval 拿到同號

`SERIAL` / `IDENTITY` 用 sequence、兩 region 各自 nextval 可能拿到同 number、INSERT 衝突（PK duplicate）。

修法：

- 用 *staggered sequence range*：每個 node 的 sequence 設上下限，node1 發 1 到 1,000,000、node2 發 1,000,001 到 2,000,000。只用 `setval` 設起點不會擋住 node1 發到 1,000,001，上限要用 `MAXVALUE` 設：

  ```sql
  -- node1：orders.id 只發 1 到 1,000,000
  ALTER SEQUENCE orders_id_seq MAXVALUE 1000000;
  -- node2：orders.id 只發 1,000,001 到 2,000,000
  ALTER SEQUENCE orders_id_seq MINVALUE 1000001 MAXVALUE 2000000 START 1000001 RESTART;
  -- 範圍用完時 INSERT 失敗：
  -- ERROR:  nextval: reached maximum value of sequence "orders_id_seq" (1000000)
  ```

- 或用 *UUID*（v4 / v7）作 PK、跨 node 無 collision
- 或 *sequence per-node namespace*：起點錯開、步長等於 node 數，兩個 node 分別發奇數與偶數：

  ```sql
  -- node1：1, 3, 5, ...
  CREATE SEQUENCE orders_id_node1 START 1 INCREMENT 2;
  -- node2：2, 4, 6, ...
  CREATE SEQUENCE orders_id_node2 START 2 INCREMENT 2;
  ```

### Logical replication 不自動 replicate DDL

PG logical replication（pgEdge / BDR 基礎）*不自動 replicate DDL*。每 node `CREATE TABLE` / `ALTER TABLE` 必須 *分別跑*。

修法：

- 用 *deployment automation*（Ansible / Terraform）對所有 node 同時跑 DDL
- pgEdge 提供 `spock.replicate_ddl(...)` 把 DDL 轉成可 replicate event
- BDR Enterprise 有 *DDL replication*（商業 feature）
- DDL 變更前確認 *所有 node 都健康*、減少 partial state

### Conflict log table 沒有 retention 而撐爆 disk

開啟 `spock.save_resolutions` 之後，每個 conflict 寫進 `spock.resolutions`（BDR / PGD 是 `bdr.conflict_history`）等 table、log 累積 disk 爆。

修法：

- 設 *log retention*：cron 定期 archive + delete 老 conflict log
- 監控 conflict rate — 高 conflict rate 是 application 設計問題（不是 ops 問題）
- 對 *strict business* conflict 寫進 application-level audit table、不只 system log

### Failover 後 timeline 分歧

Multi-master 設計上 *每 region 是 primary*、Region A 掛了 Region B 接管 — 但 Region A 復活後 *仍認為自己是 primary*。Region A 掛掉前已 commit、還沒 replicate 出去的寫入，要等 A 復活才送到 Region B，而 B 在接管期間可能已經改過同一批 row；這時兩邊的版本交給 LWW 比 commit timestamp，A 掛掉前那批較早的寫入被 B 接管期間的寫入覆蓋，沒有人收到通知。

修法：

- *Fence Region A 復活*：物理 fence（network firewall）+ 手動 unfence 流程
- 用 *etcd / Consul* 跟 BDR / Spock 整合 leader election（避免 split-brain）
- 對 cross-region multi-master、必須有 *runbook* 處理 region 復活流程、不靠自動

## 何時用 multi-master vs 不用

| 情境                                           | 建議                                                       |
| ---------------------------------------------- | ---------------------------------------------------------- |
| 真正 cross-region active-active write 需求     | BDR / pgEdge                                               |
| 不可中斷 maintenance（zero downtime upgrade）  | BDR / pgEdge                                               |
| 高 conflict rate（shared counter / inventory） | 不要 multi-master、用 distributed SQL                      |
| Read scaling 為主、可接受 stale read           | streaming replication + read replica（更簡單）             |
| Strict consistency 需求                        | single-primary + sync replication 或 Aurora DSQL / Spanner |
| 預算敏感 + 不想養 BDR / pgEdge ops             | 不要 multi-master、用 managed distributed SQL              |

## 跟 MySQL Group Replication 對比

| 維度                | PG Multi-Master              | MySQL Group Replication                        |
| ------------------- | ---------------------------- | ---------------------------------------------- |
| 內建？              | 否、需 extension             | 是、5.7+ 內建                                  |
| 商業 vs 開源        | BDR 商業 / pgEdge 開源       | Oracle 商業 / community 都行                   |
| Sync mode           | 可（BDR eager）              | 是（certification-based）                      |
| Conflict resolution | LWW / column / user-defined  | Certification-based（distributed transaction） |
| Production maturity | BDR 高、pgEdge 中            | 高（Oracle 推）                                |
| Use case 比例       | 少（PG 多用 single-primary） | 較多（MySQL 推 InnoDB Cluster）                |

MySQL GR 內建 + Oracle 推、PG 沒對應內建。對 multi-master 需求重的 org、MySQL 走 GR 路徑更直接。

## 跟其他模組整合

### 跟 Replication Topology

Multi-master 是 *streaming replication 之上的 logical replication 加雙向*、不取代 streaming。Streaming 仍給 standby / failover、multi-master 給 active-active write。詳見 [Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)。

### 跟 Logical Replication

pgEdge / BDR 都基於 logical replication slot、跟 [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 共用 PG logical decoding infrastructure、但 *配置 + tooling* 不同。

### 跟 MVCC

Multi-master 的 conflict 在 *commit 後* 偵測（async）、不在 transaction 內。跟單機 MVCC（同 cluster 內 transaction snapshot）不同層。詳見 [MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)。

## 相關連結

- [PostgreSQL vendor overview](/backend/01-database/vendors/postgresql/)
- [PG Replication Topology](/backend/01-database/vendors/postgresql/replication-topology/)（streaming + multi-master 共存）
- [PG Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)（logical decoding 基礎）
- [PG MVCC + Lock Model](/backend/01-database/vendors/postgresql/mvcc-lock-model/)（multi-master conflict vs 單機 MVCC）
- [PG Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)（single-primary HA 替代方案）
- [1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/)（multi-master vs distributed SQL）
- [MySQL Group Replication](/backend/01-database/vendors/mysql/group-replication/)（sibling、不同實作）
- 官方：[EDB BDR](https://www.enterprisedb.com/products/edb-postgres-distributed-bdr) / [pgEdge](https://www.pgedge.com/) / [Spock GitHub](https://github.com/pgEdge/spock) / [Bucardo](https://bucardo.org/)
