---
title: "PostgreSQL declarative partitioning：partition 不是切表、是讓 planner pruning"
date: 2026-05-18
description: "Declarative partitioning 的真實價值是 query planner pruning + maintenance scope 縮小、不是「把大表切小」；RANGE / LIST / HASH 取捨、partition key 選法、5 個 production 踩雷（key 選錯不 prune / unique 不 enforce 跨 partition / ATTACH 鎖太久 / partition 數爆 / DETACH 不 reclaim 空間）、跟 autovacuum + index 設計整合"
weight: 33
tags: ["backend", "database", "postgresql", "partitioning", "performance", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明大表（> 1TB）需要 partitioning、本文聚焦 *partition 真實價值在哪、為什麼多數人第一次 partition 都做錯*。

## Partition 不是「把大表切小」、是「讓 planner pruning + 縮小 maintenance scope」

剛開始學 partitioning 的人多半從「表太大、切小一點」直覺出發；切了之後發現 — *query 變慢*（planner 還在看所有 partition）、*INSERT 變慢*（trigger / partition routing overhead）、*backup 沒變短*（總資料量沒變）。直覺錯了：partition 的工程價值來自兩個機制、跟「切小」沒直接關係：

1. **Query planner pruning**：planner 在 planning 階段 *跳過* 不可能命中 partition key 的 partition、查詢只 scan 相關 partition；前提是 *WHERE 條件含 partition key*、否則 planner 看完所有 partition、效能反而比單表差
2. **Maintenance scope 縮小**：vacuum / index rebuild / DROP / archive 只動單一 partition、不掃整表；vacuum 12 小時變 30 分鐘 / DROP 老資料 0.01 秒、是 partition 真正回本的地方

partition 是 *為了 maintenance 跟 planner pruning* 設計、不是「表變小」設計。漏掉這個 framing、partition 配置會錯。

## RANGE / LIST / HASH：partition 策略對應業務形狀

```sql
-- RANGE: 時間序列、log、event（最常見）
CREATE TABLE events (
  id bigint,
  event_time timestamptz NOT NULL,
  payload jsonb
) PARTITION BY RANGE (event_time);

CREATE TABLE events_2026_05 PARTITION OF events
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- LIST: tenant ID / region / status enum
CREATE TABLE orders (
  id bigint,
  tenant_id int NOT NULL,
  ...
) PARTITION BY LIST (tenant_id);

CREATE TABLE orders_tenant_premium PARTITION OF orders
  FOR VALUES IN (1001, 1002, 1003);

-- HASH: 均勻散落（無自然 partition key）
CREATE TABLE users (
  user_id bigint NOT NULL,
  ...
) PARTITION BY HASH (user_id);

CREATE TABLE users_0 PARTITION OF users
  FOR VALUES WITH (MODULUS 4, REMAINDER 0);
```

策略選擇關鍵：

- **RANGE** 適合 *時間 / 有序值* — query 多半帶 `WHERE event_time >= X`、prune 效率最高；archive / drop 老資料是 `DROP PARTITION` 0.01 秒
- **LIST** 適合 *離散 enum / tenant* — query 帶 `WHERE tenant_id = X` prune；缺點是 tenant 增長要手動 ALTER ADD PARTITION
- **HASH** 適合 *均勻分散、沒自然 key* — query 多半 by-PK lookup、HASH 讓單 partition 大小均勻；prune 只在 `WHERE hash_key = X` 等值查詢觸發

### 選錯 partition key 是最常見的錯誤

例：events 表用 `user_id` HASH partition、但 query 多半 `WHERE event_time BETWEEN ...`、`user_id` 不在 WHERE — planner 沒法 prune、掃所有 partition、效能比單表更差（多了 partition routing overhead）。

partition key *必須* 對應 query 最常用的 WHERE filter；錯了就退化成 *維護面有好處、查詢面有壞處* 的尷尬狀態。

## Partition pruning：planner 怎麼決定跳過

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM events
WHERE event_time >= '2026-05-01' AND event_time < '2026-05-15';

-- 期望輸出包含：
--  Append (cost=...)
--    -> Seq Scan on events_2026_05  (cost=...)
-- (只 scan 一個 partition、其他 partition pruned)
```

pruning 觸發條件：

1. WHERE 含 partition key 的 *constant expression*（`WHERE x = 5` 觸發；`WHERE x = some_function()` 不觸發 planning-time prune、但 PG 11+ execution-time prune 可救）
2. PG 11+ 支援 *execution-time pruning* — query plan 內含 partition key、runtime 才知道值（prepared statement / NestedLoop join）
3. partition key 不在 WHERE 時 — *全部 partition 掃*、是反指標、表示 partition strategy 不對

### Partition-wise join / aggregate (PG 11+)

```sql
SET enable_partitionwise_join = on;
SET enable_partitionwise_aggregate = on;

-- 兩個同 partition 策略的表 JOIN 時、planner 可 partition-wise 平行做
SELECT * FROM events e JOIN events_metadata m
  ON e.event_time = m.event_time
  WHERE e.event_time >= '2026-05-01';
```

需要兩個表 *partition strategy 完全一致*（同 partition key + 同 partition boundary）— 設計時對齊、後期不容易調整。

## Production 故障演練

### Case 1：partition key 選錯，query 變慢

**徵兆**：partition 後特定查詢從 200ms 變成 2000ms；EXPLAIN 顯示 `Append` 下面所有 partition 都被 scan、沒 partition 被 prune。

**根因**：partition by `user_id` HASH、但 query 多用 `WHERE created_at BETWEEN X AND Y`；planner 不知道 user 在哪個 partition、必須掃全部。

**修法**：

1. **驗證 step**：partition 前先 `pg_stat_statements` 看 top 10 query 的 WHERE pattern、partition key 必須對應其中 80% 流量的 filter
2. **修正**：DROP partition strategy、改 partition by `created_at` RANGE；遷移用 `pg_dump --section=data` per-partition 重灌
3. **避免**：partitioning 不可逆、設計階段 query pattern 沒看清楚不要動

### Case 2：cross-partition unique constraint 不 enforce

**徵兆**：partition 後發現 application code 寫死 duplicate user_email、但 unique constraint 沒擋；DB 內有同 email 多筆。

**根因**：PostgreSQL partition table 的 `UNIQUE` constraint *必須包含 partition key* — `UNIQUE (email)` 在 partition by `tenant_id` 的表上 *無法 enforce*（PostgreSQL 拒建）；workaround 用 `UNIQUE (email, tenant_id)`、但業務語意是「email 全域唯一」、PG 無法保證。

**修法**：

1. **架構**：跨 partition 唯一性必須在 *application 層* enforce（lock + check 模式）
2. **替代**：用 *non-partitioned* 表存唯一性目標（user_email_registry）、做寫入前 lookup
3. **設計階段檢查**：partition by X、unique constraint 必須含 X；若業務要求 unique 不含 X、partition strategy 錯

### Case 3：ATTACH PARTITION 鎖表太久

**徵兆**：新 month partition `ATTACH PARTITION` 跑 30 秒、期間整個 events 表 read 阻塞、application timeout 大量。

**根因**：`ATTACH PARTITION` 預設加 `ACCESS EXCLUSIVE` lock 在 parent table、scan 整個新 partition 驗證 CHECK constraint；大 partition + 沒 CHECK constraint 預先驗證 → 鎖時間爆。

**修法**：

```sql
-- 1. 先把要 attach 的 partition 加 CHECK constraint，用 NOT VALID 不掃描
ALTER TABLE events_2026_06 ADD CONSTRAINT events_2026_06_range
  CHECK (event_time >= '2026-06-01' AND event_time < '2026-07-01') NOT VALID;

-- 2. VALIDATE 用 SHARE UPDATE EXCLUSIVE lock、允許讀寫
ALTER TABLE events_2026_06 VALIDATE CONSTRAINT events_2026_06_range;

-- 3. ATTACH 不再需要 scan（CHECK 已 VALIDATE 過）
ALTER TABLE events ATTACH PARTITION events_2026_06
  FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
-- ATTACH 變 instant
```

### Case 4：partition 數爆炸，planner planning time 爆

**徵兆**：partition 累積到 500+（daily partition 跑 1-2 年）、簡單 query EXPLAIN 顯示 planning_time 從 1ms 漲到 200ms、application response 變慢。

**根因**：partition 越多 planner 要評估的 partition 越多、即使有 pruning、planning 階段也要 walk 全部 partition table；500+ partition 是 planning overhead 明顯的閾值。

**修法**：

1. **架構**：partition granularity 對應 retention — 不要 daily partition 留 2 年（→ weekly / monthly）
2. **archive 老 partition**：DETACH 老 partition、轉成 cold storage 表、planner 不再看
3. **`enable_partition_pruning`** 預設 on、確保啟用
4. **PG 12+**：planner 對 partition table 的 list 處理優化、planning time 上限拉高、但仍要控

### Case 5：DETACH 後磁碟空間沒回收

**徵兆**：DETACH PARTITION 後 `pg_database_size` 沒下降、預期釋放 50GB；磁碟仍滿。

**根因**：DETACH 只是把 partition 從 parent table *分離*、partition 自己仍是獨立表存在；要真釋放需要 `DROP TABLE detached_partition`。SRE 以為 DETACH = 刪掉。

**修法**：

```sql
-- 完整流程
ALTER TABLE events DETACH PARTITION events_2024_01;
-- events_2024_01 仍存在、佔磁碟

-- 確認沒 query 在用後
DROP TABLE events_2024_01;
-- 才釋放磁碟
```

### Routine：archive workflow

```sql
-- 月底跑：
-- 1. detach 13 個月前的 partition
ALTER TABLE events DETACH PARTITION events_2025_04;

-- 2. dump 到 cold storage
\COPY events_2025_04 TO '/cold/events_2025_04.csv' (FORMAT CSV);

-- 3. drop 釋放磁碟
DROP TABLE events_2025_04;
```

## 容量規劃

| 維度                       | 估算                                                  | 警戒                                            |
| -------------------------- | ----------------------------------------------------- | ----------------------------------------------- |
| 單 partition size          | 跟單表 vacuum 上限對齊（10-100GB sweet spot）         | > 200GB 時考慮 sub-partition 或細化 granularity |
| Partition 數量             | 對應 retention × granularity                          | > 200 partition 時 planning time 開始浮現       |
| Partition key cardinality  | LIST：< 100 / HASH：自定 modulus / RANGE：時間 + 維度 | 太多獨立 partition value 用 HASH                |
| Cross-partition query 比例 | EXPLAIN 看 partition scan 數                          | > 30% query 掃 > 50% partition 表示 key 選錯    |
| Maintenance window         | DROP / DETACH / ATTACH 各 partition 各自管            | hot partition 維護仍在 maintenance window       |

實務 default：

- 時間序列（events / log）：monthly RANGE partition、retention 12-24 個月
- Multi-tenant（orders / records）：tenant_id LIST partition + 大 tenant 各自獨立 partition
- 均勻散落（user / metric）：8-16 個 HASH partition、單 partition 50-100GB

## 整合 / 下一步

### 跟 [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) 整合

partitioning 是 autovacuum 問題的長期解：

1. Hot partition autovacuum 緊（scale_factor 0.05、cost_limit 5000）
2. Cold partition `autovacuum_enabled = false`
3. 但 partition 數爆會把 `autovacuum_max_workers` 跑滿、需要拉

### 跟 index 設計整合

partition table 的 index 處理：

1. PG 11+ 全域 index：`CREATE INDEX ON partitioned_table (...)` 自動在每 partition 建 local index
2. **不存在跨 partition unique** — 只能 partition-local
3. **partition-wise index scan**：PG 11+ 跟 partition-wise join 一起、index lookup 平行

### 跟 backup / PITR

partition 不是 backup 替代品 — 但能加速 *partial restore*：

1. 只 restore 特定時段的 partition、不用 restore 整個表
2. 對應 [PITR + WAL archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/) 的 partial recovery scenario

### 下一步議題

- **Sub-partitioning**：partition 內再 partition（時間 + tenant）、適合 multi-tenant + 時間序列
- **pg_partman extension**：自動建月 partition、不用 cron
- **Foreign key to partitioned table** (PG 12+)：跨 partition FK enforce、但 cascade 限制多

## 相關連結

- 上游 vendor 頁：[PostgreSQL](/backend/01-database/vendors/postgresql/)
- 上游 chapter：[Schema Design](/backend/01-database/schema-design/) — partition 是 schema 決策
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/) / [TimescaleDB Deep Dive](/backend/01-database/vendors/postgresql/timescaledb-deep-dive/)（hypertable 是 partition 自動化）
- 後續路由：[Partition Redesign](/backend/01-database/vendors/postgresql/partition-redesign/)（重排 partition strategy 的 migration playbook）
- Methodology：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)
