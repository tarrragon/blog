---
title: "PostgreSQL → CockroachDB：三維皆 High 的多重歸類 migration"
date: 2026-05-19
description: "PostgreSQL → CockroachDB 是 Schema / Operational / Paradigm 三維皆 High 的 multi-axis migration、實證 [#127](/report/content-structure-by-max-diff-dimension/) 的「多重歸類跟 tie-breaking」規則；主結構走 Type E paradigm shift、Schema 差 + Operational redesign 抽出獨立段；涵蓋 transaction model 重設計、SQL dialect gap、5 個 production 踩雷"
weight: 14
tags: ["backend", "database", "postgresql", "cockroachdb", "migration", "multi-axis", "paradigm-shift"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [PostgreSQL](/backend/01-database/vendors/postgresql/) 跟 [CockroachDB](/backend/01-database/vendors/cockroachdb/)。本文是 [#127 多重歸類跟 tie-breaking](/report/content-structure-by-max-diff-dimension/) 規則的實證 — 三維皆 High 配對的處理方式不是「選 type A 或 type C 或 type E」、是 *主導維度走 Type E、其他高維度獨立加段*。

## 三維皆 High：決策矩陣

跑 [diff dimension audit](/report/content-structure-by-max-diff-dimension/) 對 PostgreSQL → CockroachDB：

| 維度                 | 評估                                                                                        | 等級     |
| -------------------- | ------------------------------------------------------------------------------------------- | -------- |
| Schema / API         | PostgreSQL wire protocol 兼容、但 SQL feature set 部分缺（CTE recursive 部分 / window function 部分 / extension 完全缺）| **High** |
| Operational model    | Single-node + Patroni → distributed Raft + 自動 rebalance；HA / backup / topology 全換      | **High** |
| Abstraction / paradigm | Single-node MVCC + transaction → distributed Serializable Snapshot Isolation (SSI)        | **High** |
| Number of components | 同 1 個 DB cluster                                                                          | Low      |
| Application change   | Transaction retry pattern 必須改、ORM 可能需 patch                                          | Medium   |

3 維 High + 1 維 Medium。按 [methodology audit Step 5](/posts/migration-playbook-methodology/) 的多重歸類處理規則：

```text
主導維度判讀 (優先序): Schema > Paradigm > Operational > Components

實際應用: Schema High + Paradigm High + Operational High
- Schema 是 High、但 CRDB 提供 PostgreSQL wire protocol 兼容
- Paradigm 是 High、是 *單機 → 分散式* 的根本轉變、讀者最關心
- Operational 是 High、但很大程度是 Paradigm 的 downstream

→ 主結構選 Paradigm（Type E）、Schema + Operational 抽獨立段補充
```

不強迫單一 type 標籤 — 本文是 *Type E 為主 + Type A / C 高維度增補* 的 multi-axis 形態。

## 結構 differentiator：Type E 主結構 + 多軸增補段

跟前批 5 個 migration playbook 對照：

| 結構元素                  | Type A Splunk → Elastic | Type B Redis → DragonflyDB | Type C PostgreSQL → Aurora | Type D Datadog → Grafana | Type E Kafka ↔ NATS | **本文（三維 High）**     |
| ------------------------- | ----------------------- | -------------------------- | -------------------------- | ------------------------ | ------------------- | ------------------------- |
| Phased translation        | yes                     | -                          | -                          | -                        | -                   | partial                   |
| Compatibility audit       | -                       | yes                        | -                          | -                        | -                   | yes                       |
| Operational redesign 對位 | -                       | -                          | yes                        | -                        | -                   | **yes（獨立段）**         |
| Schema gap 對位           | -                       | -                          | -                          | -                        | -                   | **yes（獨立段）**         |
| Parallel streams          | -                       | -                          | -                          | yes                      | -                   | -                         |
| Paradigm contrast         | -                       | -                          | -                          | -                        | yes                 | yes                       |
| Application 重設計        | -                       | -                          | -                          | -                        | yes                 | yes                       |
| 混合架構 long-term        | -                       | -                          | -                          | -                        | yes                 | partial（部分 workload）  |

本文是「Type E 為主 + Type A schema gap 段 + Type C operational redesign 段」混合形態、9-10 章節、260-300 行。

## 維度 1：Paradigm shift（主導）

CRDB 是 *distributed SQL DB*、不是「PostgreSQL 多節點版」。核心差異：

| 概念                | PostgreSQL                                  | CockroachDB                                                |
| ------------------- | ------------------------------------------- | ---------------------------------------------------------- |
| Transaction isolation | MVCC、Read Committed default               | Serializable Snapshot Isolation (SSI)、強一致               |
| Transaction conflict | First writer wins                          | Retry-on-conflict、application 必須處理 `40001` retry code |
| Replication         | Streaming replication + standby            | Raft consensus、每筆寫 quorum + 自動 rebalance             |
| Partition           | Declarative partitioning（手動）            | Automatic range-based + locality-aware                     |
| Latency p99         | 1-10ms（單 region）                         | 5-50ms（cross-AZ Raft quorum）                             |
| Throughput limit    | 單 primary 上限 ~10-50K TPS                 | Linear scale by adding node、~5K TPS / node                |

關鍵 paradigm 改變：*transaction 是 retry-able 操作、不是 atomic guaranteed*。所有 transaction code 需要包 retry loop（CRDB 提供 `cockroach_restart` savepoint）。

## 維度 2：Schema gap（PostgreSQL features CRDB 不支援）

CRDB 號稱 PostgreSQL-compatible、但 *covergence rate 80-90%*；常見 gap：

| PostgreSQL feature                           | CRDB 狀態                                            | 影響                                                  |
| -------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| Stored procedure / function (PL/pgSQL)       | Limited（CRDB 22.2+ 部分支援）                       | Migration scope 內必須 audit + 改寫                  |
| Common Table Expression (CTE) recursive      | Limited (depth + structure)                          | 複雜 CTE 可能跑不通、必須 query refactor             |
| Window function 全集                         | Partial                                              | 報表 query 需逐 case 驗證                            |
| Extensions (pg_repack / pgaudit / TimescaleDB)| **不支援**                                          | 用 CRDB 自家 alternative 或自管 application 層       |
| Triggers                                     | Limited                                              | Audit / data integrity 邏輯遷到 application 層       |
| Custom types / domain                        | Partial                                              | 用 CHECK constraint 替代                              |
| Geographic types (PostGIS)                   | CRDB native geo support（語法不同）                  | Spatial query 改寫                                    |
| `SELECT FOR UPDATE` semantics                | 對等但底層機制不同（distributed lock）               | 注意 deadlock pattern 差異                            |
| Advisory locks                               | **不支援**                                            | Application 端用其他 distributed lock（Redis / Consul）|

Migration 必須 *先 audit 完整 SQL feature 使用*、列出 gap、評估解法或退役。

## 維度 3：Operational redesign

CRDB operational model 完全不同：

| Operational concept | PostgreSQL self-managed                              | CRDB                                                |
| ------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| Cluster bootstrap   | Patroni / Stolon + manual                            | `cockroach init` + 自動 Raft formation             |
| HA                  | Patroni + DCS + watchdog                             | 內建 Raft、無 single primary                        |
| Failover            | Patroni-managed、15-60s                              | 透明 Raft re-election、< 5s                         |
| Backup              | pgBackRest + WAL archive                             | `BACKUP TO` (incremental + full)                    |
| Restore             | `pgBackRest restore` + PITR                          | `RESTORE FROM`                                      |
| Replication         | Streaming + logical                                  | Built-in、無 logical replication 對等概念           |
| Schema migration    | `pg_dump` / Flyway / Liquibase                       | `cockroach sql` + online schema change（無 lock）  |
| Monitoring          | pg_stat_* views + Prometheus exporter                | CRDB admin UI + Prometheus（schema 不同）          |
| Sizing              | Vertical scale（單 node big spec）                   | Horizontal scale（多 node 小 spec）                |

SRE 心智模型完全重訓：*無 primary 概念 / 無 streaming lag 概念 / 無 standby promote 概念*。

## Migration 流程（混合形態）

不是線性 phased、是 *phased + parallel + partial* 混合：

```text
Phase 0: scope 判讀
  - 列 application、區分「適合 CRDB」vs「保留 PostgreSQL」
  - SQL feature audit
  - Application transaction pattern audit

Phase 1: schema port + application 改寫
  - DDL 轉成 CRDB syntax
  - 不支援 extension 找 alternative
  - Application transaction code 加 retry loop

Phase 2: 雙寫期（部分 application 開始走 CRDB）
  - 新 application 走 CRDB
  - 舊 application 持續 PostgreSQL
  - CDC bridge（Debezium → Kafka → CRDB consumer）

Phase 3: cutover 適合的 application
  - 每個 application 獨立 cutover
  - 不是「全 DB 一次切」

Phase 4: 長期混合架構
  - 某些 workload 永遠保留 PostgreSQL（不適合分散式）
  - CRDB 跑 distributed 適配 workload
```

整體 3-6 個月、不收斂到全 CRDB。

## Production 故障演練

### Case 1：Transaction retry 沒處理、application 大量 `40001` error

**徵兆**：cutover 後 application 5-10% transaction 報 `restart transaction: TransactionRetryWithProtoRefreshError`、業務 fail。

**根因**：PostgreSQL Read Committed 不要求 application 處理 conflict、CRDB Serializable Isolation 必須 *retry-on-conflict*；application code 沒 retry loop。

**修法**：

```go
// CRDB transaction with retry
for retries := 0; retries < 10; retries++ {
    tx, _ := db.Begin()
    // ... transaction logic ...
    err := tx.Commit()
    if err != nil && strings.Contains(err.Error(), "40001") {
        time.Sleep(backoff(retries))
        continue
    }
    break
}
```

framework-level：用 CRDB-provided client lib（go-cockroachdb / crdb-jdbc）有 retry helper。

### Case 2：Extension 缺位、application feature 整段掉

**徵兆**：cutover 後 application 某個地理計算功能直接報錯、PostGIS 函數不存在；migrate 計畫漏看。

**根因**：CRDB native geo 不同 syntax / API、PostGIS extension 不能直接搬。

**修法**：

1. **Pre-migration 必跑 extension audit**：列所有 `pg_extension`、找對應 CRDB feature 或退役
2. **PostGIS 替代**：CRDB native ST_* functions、部分 syntax 對齊但 spatial index 不同
3. **退役不能換的 feature**：評估保留 PostgreSQL（混合架構）

### Case 3：Sequential PK 撞 Raft quorum 瓶頸

**徵兆**：cutover 後寫入吞吐量 / latency 不如預期、CRDB cluster CPU < 30% 但 write latency p99 high。

**根因**：application 用 `AUTO_INCREMENT` / `SERIAL` 連續 PK；CRDB 把連續 key 放 *同一 range* / 同一 Raft group、寫入串行化、無法平行 scale。

**修法**：

1. **改 UUID v7 / `unique_rowid()`**：時序排序但散佈跨 range、自動 partition by hash
2. **`PRIMARY KEY (region, id)`**：multi-region 場景 multi-tenancy 自然拆分
3. **不適合的 workload 留 PostgreSQL**：不是所有 schema 都適合 distributed

### Case 4：Long transaction 對 Raft 衝擊

**徵兆**：跨 1 分鐘+ 的 transaction（batch processing / 大 ETL）大量 retry、最後失敗；同期間其他短 transaction 也 retry rate 上升。

**根因**：CRDB long transaction holds intent on touched ranges、阻塞其他 transaction；SSI conflict 機率隨 transaction 時間平方增長。

**修法**：

1. **Long transaction 拆短**：batch 用多個 short transaction、checkpoint 在 application 層
2. **Heavy ETL 不跑 CRDB**：用 CRDB CDC export 到 OLAP（Snowflake / BigQuery）跑 batch
3. **Read-only long transaction 用 follower read**：`AS OF SYSTEM TIME` 不 hold intent、適合 reporting

### Case 5：Backup / restore 行為跟 PostgreSQL 不同、SRE runbook 失效

**徵兆**：DBA 嘗試 `pg_restore` 失敗、CRDB 端 backup format 完全不同；incident response 卡關 1-2 小時。

**根因**：CRDB backup 是 *cluster-internal format*、不能用 PostgreSQL tooling；SRE runbook 仍是 PostgreSQL world、應急時心智模型錯位。

**修法**：

1. **Runbook 重寫**：CRDB-specific backup / restore 流程、SRE training
2. **DR drill**：cutover 前跑完整 DR drill、用 CRDB tooling 完成、不依賴 PostgreSQL 經驗
3. **Multi-region backup**：CRDB 跨 region backup 配置、避免單 region 故障

## Capacity 規劃

| 維度                 | PostgreSQL self-managed                       | CockroachDB                                              |
| -------------------- | --------------------------------------------- | -------------------------------------------------------- |
| Single-node 上限     | ~10-50K TPS（vertical scale 到 32-128 vCPU）  | ~5K TPS / node（horizontal scale by adding node）       |
| 跨 region            | 高 latency 跨區 streaming                     | 設計 native、Locality-aware queries                      |
| Sharding             | 手動 partition / pg_partman                   | 自動 range-based                                          |
| Storage / TPS ratio  | 不變                                          | Storage 跨 node 3x（Raft quorum 3-replica default）     |
| Total cost (10TB)    | $2-4K USD / month（self-managed）             | $5-10K USD / month（CRDB Cloud + 3x storage）           |

**判讀**：CRDB cost 顯著高、選 CRDB 必須是 *paradigm 需求*（distributed transaction / multi-region / linear scale）；單純成本 / availability 改善走 [Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 更划算。

## 整合 / 下一步

### 跟 [PostgreSQL → Aurora migration](/backend/01-database/vendors/postgresql/migrate-to-aurora/) 對比

兩條 PostgreSQL 出路：

- **Aurora**：operational simplification、protocol drop-in、cost 中等漲；適合 *不需 distributed transaction* 的 production
- **CRDB**：distributed paradigm shift、application 必須改、cost 顯著漲；適合 *真的需要 distributed* 的 workload

多數 application 不需要 distributed transaction、Aurora 更合理；真正需要 cross-region 強一致 / linear scale by adding node 才走 CRDB。

### 跟 application transaction pattern 重設計

CRDB 強制 application 改 transaction code、retry loop 必加。團隊心智模型轉換是 migration 主要 effort、技術部分相對少。

### 下一步議題

- **CRDB → PostgreSQL reverse migration**：當業務 simplify 後 distributed 不必要、reverse migration cost 高、實務上 CRDB 是 *single-direction lock-in*
- **CRDB Serverless**：cost 起點低、burst workload 適合；steady workload 仍是 dedicated cluster
- **Multi-region active-active**：CRDB 真正強項、但網路成本爆、僅金融 / 政府客戶 ROI 合理

## 相關連結

- Source / target vendor：[PostgreSQL](/backend/01-database/vendors/postgresql/) / [CockroachDB](/backend/01-database/vendors/cockroachdb/)
- 對位 migration：[PostgreSQL → Aurora](/backend/01-database/vendors/postgresql/migrate-to-aurora/)（另一條 PostgreSQL 出路）
- 平行 deep article：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [#127 Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)（本文驗證 *多重歸類 multi-axis 處理*）
