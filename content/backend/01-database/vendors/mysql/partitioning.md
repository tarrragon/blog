---
title: "MySQL Partitioning：partition lifecycle 五段、跟 Vitess sharding 不同的「同 instance 內水平切割」"
date: 2026-05-19
description: "MySQL native partitioning 是 *同一個 MySQL instance 內的水平切割*、不是 Vitess sharding（跨 instance）。本文走 partition lifecycle 五段（design → create → query → maintenance → drop）、4 種 partition type（RANGE / LIST / HASH / KEY + COLUMNS / sub-partitioning）的 trade-off、partition pruning 怎麼運作、5 production 踩雷（PK 必須含 partition key / global index 沒原生 / partition exchange 細節 / orphan partition / cross-partition query 慢）、跟 PG declarative-partitioning 對比"
weight: 22
tags: ["backend", "database", "mysql", "partitioning", "deep-article"]
---

> 本文是 [MySQL](/backend/01-database/vendors/mysql/) overview 的 implementation-layer deep article。Overview 已說明 MySQL 在 OLTP 譜系的定位、本文聚焦 *native partitioning* — 5 段 lifecycle + 4 種 type + 跟 Vitess sharding / PG partitioning 對比。

---

## Partition lifecycle 五段

MySQL native partitioning 是 *同 instance 內把一個邏輯 table 拆成多個 physical sub-table*、optimizer 可選擇只 scan 相關 partition。整個 partition lifecycle 5 段：

```text
Design       決定 partition key / type / 數量
   ↓
Create       CREATE TABLE ... PARTITION BY ...
   ↓
Query        WHERE clause + partition pruning
   ↓
Maintenance  ADD / DROP / REORGANIZE / EXCHANGE
   ↓
Drop         整個 partition 一次刪（比 DELETE FROM 快 1000x）
```

每段都有獨立工程決策。設計階段選錯 partition key、後續 maintenance + query 全部 broken。

跟 [Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/) 對比：

- *MySQL partitioning*：同 instance、optimizer 自動 pruning、無 cross-instance network cost
- *Vitess sharding*：跨 instance、application 透過 VTGate routing、可線性 scale

兩者不衝突、可組合：Vitess shard 內部 *再* 用 MySQL partition（例如：shard 切 16 個、每個 shard 的 table 再按月份 partition）。

## 4 種 partition type

### RANGE partitioning — 連續區間切割

最常見、適合 time-series / 連續數字：

```sql
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2),
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id, created_at)              -- PK 必須含 partition key
)
PARTITION BY RANGE (TO_DAYS(created_at)) (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01')),
    PARTITION p202603 VALUES LESS THAN (TO_DAYS('2026-04-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE  -- 未來資料 fallback
);
```

優點：

- Partition pruning 高效（時間 range query）
- 整個月 archive 直接 `ALTER TABLE orders DROP PARTITION p202601`、毫秒級

缺點：

- 必須 *預先建* 未來 partition（或用 `p_future` fallback、但 fallback partition 變大就失去 pruning 意義）
- *Hot partition* — 最新 partition 接收所有 INSERT、其他 partition 純歷史

### LIST partitioning — 離散值切割

適合 enum-like value：

```sql
CREATE TABLE users (
    id BIGINT,
    name VARCHAR(100),
    region VARCHAR(10) NOT NULL,
    PRIMARY KEY (id, region)
)
PARTITION BY LIST COLUMNS (region) (
    PARTITION p_asia VALUES IN ('TW', 'JP', 'KR', 'CN'),
    PARTITION p_americas VALUES IN ('US', 'CA', 'BR'),
    PARTITION p_emea VALUES IN ('GB', 'DE', 'FR', 'IT')
);
```

優點：對 enum-like value 直接命中、pruning 簡單。

缺點：value list 不能變更（不 supported `ALTER PARTITION ADD VALUE`）、新國家代碼必須 REORGANIZE。

### HASH partitioning — 均勻分布

對 numeric / string column 取 hash、均勻分布：

```sql
CREATE TABLE events (
    id BIGINT,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(50),
    PRIMARY KEY (id, user_id)
)
PARTITION BY HASH (user_id) PARTITIONS 8;
```

優點：均勻分布、沒有 hot partition。

缺點：

- *Range query 沒效* — `WHERE user_id BETWEEN 100 AND 200` 不能 pruning、scan 全部 partition
- Partition 數量改變需要 REORGANIZE 整張表

### KEY partitioning — MySQL 內部 hash

跟 HASH 類似、但用 MySQL 內部 hash function（不依賴 column 是否 integer）：

```sql
CREATE TABLE sessions (
    session_id VARCHAR(64),
    user_id BIGINT NOT NULL,
    data TEXT,
    PRIMARY KEY (session_id, user_id)
)
PARTITION BY KEY (user_id) PARTITIONS 16;
```

用於 *string column 或 composite column* 的均勻分布。一般場景跟 HASH 效果接近。

### Sub-partitioning — 兩層切割

RANGE + HASH 組合、深化分隔：

```sql
CREATE TABLE big_events (
    id BIGINT,
    user_id BIGINT,
    created_at DATETIME,
    PRIMARY KEY (id, created_at, user_id)
)
PARTITION BY RANGE (TO_DAYS(created_at))
SUBPARTITION BY HASH (user_id) SUBPARTITIONS 4 (
    PARTITION p202601 VALUES LESS THAN (TO_DAYS('2026-02-01')),
    PARTITION p202602 VALUES LESS THAN (TO_DAYS('2026-03-01'))
);
```

每個 RANGE partition 又拆 4 個 HASH sub-partition、共 8 個 physical storage location。適合 *時間 range + user_id hash* 兩維度。

實務罕用、複雜性高、調 query plan 困難。多數 case 用 single-level partition 即可。

## Partition Pruning — Optimizer 怎麼選 partition

`EXPLAIN PARTITIONS SELECT ...` 顯示 query 命中哪些 partition：

```sql
EXPLAIN PARTITIONS
SELECT * FROM orders WHERE created_at BETWEEN '2026-02-15' AND '2026-02-20';

+----+-------------+--------+------------+-------+
| id | select_type | table  | partitions | type  |
+----+-------------+--------+------------+-------+
|  1 | SIMPLE      | orders | p202602    | range |
+----+-------------+--------+------------+-------+
```

只命中 `p202602`、其他 partition 不 scan。

**Pruning 失效場景**：

1. **Function on partition key**：

    ```sql
    WHERE YEAR(created_at) = 2026  -- 沒 pruning、scan 全部
    ```

    應該寫成：

    ```sql
    WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'
    ```

2. **Implicit conversion**：

    ```sql
    WHERE created_at = '2026-02-15'  -- 字串 vs DATETIME、可能失效
    ```

    應該：

    ```sql
    WHERE created_at = TIMESTAMP '2026-02-15 00:00:00'
    ```

3. **OR 跨 partition**：

    ```sql
    WHERE created_at = '2026-02-15' OR user_id = 100  -- partition + non-partition column OR、scan 全部
    ```

4. **JOIN 不直接 filter partition key**：JOIN 條件不含 partition key、optimizer 估計無法 pruning。

## Partition Maintenance — ADD / DROP / REORGANIZE / EXCHANGE

### ADD partition

```sql
ALTER TABLE orders ADD PARTITION (
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01'))
);
```

對 RANGE 簡單、但要 *排在 MAXVALUE partition 之前*（如果有 `p_future`、要先 REORGANIZE）。

### DROP partition

```sql
ALTER TABLE orders DROP PARTITION p202601;
```

直接刪 partition file、毫秒級完成。是 *time-series archive 的最大優勢* — 對比 `DELETE FROM orders WHERE created_at < '...'` 跑 hours。

### REORGANIZE partition

切分 / 合併 partition：

```sql
-- 切：把 p_future 切成 p202604 + new p_future
ALTER TABLE orders REORGANIZE PARTITION p_future INTO (
    PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

REORGANIZE *rewrites partition data*、跟 OSC 一樣慢、大 partition 走 gh-ost / pt-osc 模擬（用 ghost table）。

### EXCHANGE partition

把 partition 跟 *獨立 table* swap（不複製資料）：

```sql
-- 建一個 staging table 跟 partition 同 schema
CREATE TABLE orders_staging LIKE orders;
ALTER TABLE orders_staging REMOVE PARTITIONING;  -- staging 必須是 non-partitioned

-- 把 archive partition 的資料 atomic swap 給 staging
ALTER TABLE orders EXCHANGE PARTITION p202601 WITH TABLE orders_staging;

-- 現在 orders_staging 有 p202601 的資料、orders 的 p202601 變空
-- 可以 dump staging 到 S3、或 INSERT 進 archive DB
```

`EXCHANGE PARTITION` 是 *metadata operation*、毫秒級完成、不複製資料。Time-series archive 工作流的核心工具。

## 5 個 Production 踩雷

### 1. PK 必須含 partition key — Schema 設計受限

MySQL partition 規則：**PK 必須包含所有 partition key column**。

```sql
-- 錯：PK 沒包含 partition key
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,  -- 只有 id
    created_at DATETIME NOT NULL
) PARTITION BY RANGE (TO_DAYS(created_at)) (...);
-- ERROR 1503: A PRIMARY KEY must include all columns in the table's partitioning function
```

```sql
-- 對：PK 包含 partition key
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id, created_at)  -- 兩 column 都進 PK
) PARTITION BY RANGE (TO_DAYS(created_at)) (...);
```

修法：

- 接受 PK 是 composite（id + partition_key column）
- AUTO_INCREMENT 仍 work、但 INSERT 必須給定 created_at
- *Unique constraint 也受影響* — 所有 UNIQUE index 必須含 partition key

對 application：原本 `WHERE id = X` 仍 work、但慢（沒 partition pruning）、必須 `WHERE id = X AND created_at >= ...` 才高效。

### 2. Global index 沒原生支援

MySQL partitioning *沒 global secondary index*（PG 有）。每個 partition 各自有自己的 local index、跨 partition 的 unique constraint 必須 *包含 partition key*。

例：希望 `user_id` 全表 unique、但 partition by `created_at`：

```sql
-- MySQL 不允許這樣 — UNIQUE 必須含 created_at
CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT,
    user_id BIGINT,
    created_at DATETIME,
    PRIMARY KEY (id, created_at),
    UNIQUE KEY (user_id, created_at)  -- 必須含 created_at、不是純 user_id
);
```

對 application：跨 partition 的 unique 需要 *application 層處理*（INSERT 前 SELECT 檢查）或改用 Vitess `lookup_hash` Vindex。

### 3. EXCHANGE partition — schema 必須完全一致

EXCHANGE 失敗常見：staging table 跟 partition 的 *index / column 順序差一個*、`ERROR 1736: Tables have different definitions`。

修法：

- 建 staging 用 `CREATE TABLE staging LIKE orders` 而非手寫
- `REMOVE PARTITIONING` 後立即 verify schema
- 跑 OSC 改 schema 時、partition + staging table 同時改、不能漏一個

### 4. Orphan partition — Future partition 預先建忘記延展

部署 cron 每月建下個月 partition、cron 失敗 / pause、下個月 INSERT 無對應 partition、寫入 `p_future`。`p_future` 一年累積後變超大、partition pruning 沒效、查最近資料 scan 全表。

修法：

- 監控 `p_future` partition size、超過 threshold alert
- Cron 失敗 alert（不是 silent fail）
- 不依賴 cron、改成 *application 層在 INSERT 前 ensure partition exists*（lazy create）

### 5. Cross-partition query 慢

```sql
SELECT user_id, SUM(amount) FROM orders GROUP BY user_id;
```

沒 partition key filter、optimizer 不能 pruning、scan 全部 partition。比 *single big table without partition* 還慢（因為跨 partition aggregation overhead）。

修法：

- 接受 partition 不是 *讀效能* 工具、是 *write + archive 效能* 工具
- 跨 partition aggregation 改 *materialized aggregation table*（trigger / scheduled job 維護）
- 跨 partition reporting 改丟 OLAP DB（BigQuery / Snowflake / ClickHouse）

## 跟 Vitess sharding 對比

| 維度               | MySQL partitioning         | Vitess sharding                |
| ------------------ | -------------------------- | ------------------------------ |
| 切割範圍           | 同 instance 內             | 跨 instance（無上限）          |
| Cross-shard query  | 不適用                     | VTGate 自動 split + aggregate  |
| Resharding         | REORGANIZE（rewrite data） | VReplication 自動              |
| Operational cost   | 低（單 instance 內）       | 高（4 component Vitess stack） |
| 可線性 scale write | 否（單 instance 寫吞吐限） | 是（加 shard）                 |
| Archive 效率       | DROP PARTITION 毫秒級      | 不是 archive 工具              |

兩者不衝突、適用不同問題。Partitioning 解決 *單 instance archive + write 集中*、sharding 解決 *跨 instance scale*。

## 跟 PostgreSQL declarative-partitioning 對比

| 維度                   | MySQL partitioning           | PostgreSQL declarative-partitioning |
| ---------------------- | ---------------------------- | ----------------------------------- |
| Partition type         | RANGE / LIST / HASH / KEY    | RANGE / LIST / HASH                 |
| Sub-partitioning       | RANGE + HASH                 | 多層 nested 支援更廣                |
| Global index           | 無                           | PG 11+ 有                           |
| Partition wise join    | 受限                         | PG 11+ 強                           |
| Cross-partition unique | 必須含 partition key         | PG 11+ 同限制、但 PG 17+ 部分解除   |
| Partition attach       | EXCHANGE PARTITION           | ATTACH PARTITION                    |
| 操作工具               | gh-ost / pt-osc 對 partition | pg_partman（成熟）                  |
| Production maturity    | 中（5.x 開始有、8.0 強化）   | 高（11+ declarative 後成熟）        |

PG partitioning 對 *跨 partition unique* 跟 *partition-wise join* 處理較好、是 reporting workload 的優勢。MySQL partitioning 對 *archive workflow*（DROP / EXCHANGE）較成熟。詳見 [PostgreSQL Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)。

## 何時用 native partitioning

| 場景                                                                | 建議                                             |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| Time-series workload + archive needs（log / event / order history） | 用 RANGE                                         |
| 大表 > 1 TB 且 query 多有 time filter                               | 用 RANGE 加速 prune                              |
| 跨 region / 跨業務切分                                              | 用 LIST                                          |
| 需要 *線性 scale write throughput*                                  | 不用 partition、用 Vitess sharding               |
| 需要 *全表 unique constraint*                                       | 不用 partition、影響太大                         |
| 主要做 ad-hoc analytical query                                      | 不用 partition、OLAP DB（ClickHouse / BigQuery） |
| 小表 < 100 GB                                                       | 不必 partition、index 夠用                       |

## 跟其他模組整合

### 跟 Online Schema Change

對 partitioned table 的 schema change（ALTER COLUMN）必須 *每個 partition 都改*。gh-ost / pt-osc 對 partitioned table 仍 work、但複雜性增加。詳見 [Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)。

### 跟 Vitess

Vitess shard 內部可再 partition、單 shard 對應一個 MySQL instance、partition 是 instance 內優化。Vitess `vtctldclient PartitionTablet` 命令處理 shard-aware partition 操作。詳見 [Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/)。

### 跟 InnoDB Tuning

每個 partition 是獨立 InnoDB tablespace（`innodb_file_per_table=ON` 預設）、buffer pool 內 cache 行為跟 single big table 不同。Partition 多時 buffer pool warm-up 時間更長。詳見 [InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)。

### 跟 Replication

Partition operation（ADD / DROP / EXCHANGE）是 DDL、走 binlog、replica apply 時可能 *locking issue*（特別是 EXCHANGE 跟 replica running query 衝突）。詳見 [Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)。

### 跟 Query Optimization

`EXPLAIN PARTITIONS` 是 partition-aware query optimization 的關鍵工具、看 query 真的命中哪些 partition。詳見 [Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)。

## 容量規劃要點

| 維度                        | 建議                                                      |
| --------------------------- | --------------------------------------------------------- |
| Partition 數量上限          | 8.0 預設 8192、實務建議 < 1000（管理成本上升）            |
| 單 partition 大小           | 10 GB - 100 GB（太小無 partition value、太大 prune 沒效） |
| RANGE 時間 partition        | 月 / 週 / 日（依資料量）                                  |
| HASH partition 數量         | 通常 power of 2（8 / 16 / 32 / 64）                       |
| Future partition pre-create | 至少 6 個月 buffer、cron 每月 add 1 個                    |

## 相關連結

- [MySQL vendor overview](/backend/01-database/vendors/mysql/)
- [MySQL Vitess sharding](/backend/01-database/vendors/mysql/vitess-sharding/)（跨 instance 切割對比）
- [MySQL Online Schema Change](/backend/01-database/vendors/mysql/online-schema-change-tools/)（partition table 的 schema change）
- [MySQL Query Optimization](/backend/01-database/vendors/mysql/query-optimization/)（EXPLAIN PARTITIONS）
- [MySQL InnoDB Tuning](/backend/01-database/vendors/mysql/innodb-tuning/)（partition + buffer pool 互動）
- [PostgreSQL Declarative Partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)（PG sibling 對比）
- [Partition 卡片](/backend/knowledge-cards/partition/)
- 官方：[MySQL Partitioning](https://dev.mysql.com/doc/refman/8.0/en/partitioning.html)
