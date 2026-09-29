---
title: "PostgreSQL → CockroachDB Migration：分散式 transaction、SQL 相容缺口與 operational 重設計"
date: 2026-05-19
description: "PostgreSQL → CockroachDB 要同時處理 paradigm（分散式 Serializable transaction 與 retry）、SQL feature 相容缺口與 operational 模型的替換；本文涵蓋 transaction model 重設計、SQL dialect gap、operational 對位、分階段並保留混合架構的遷移流程，以及 production 踩雷"
weight: 43
tags: ["backend", "database", "postgresql", "cockroachdb", "migration", "multi-axis", "paradigm-shift"]
---

> 本文是跨 vendor [migration](/backend/knowledge-cards/migration/) playbook、cross-link 到 [PostgreSQL](/backend/01-database/vendors/postgresql/) 跟 [CockroachDB](/backend/01-database/vendors/cockroachdb/)，整理 paradigm、SQL feature 與 operational model 三個面向同時改變時的遷移做法。每階段切換用 [migration gate](/backend/knowledge-cards/migration-gate/) 把關。

## PostgreSQL 與 CockroachDB 差在哪些面向

| 維度                   | 評估                                                                                                                     | 等級     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------- |
| Schema / API           | PostgreSQL wire protocol 兼容、但 SQL feature set 部分缺（CTE recursive 部分 / window function 部分 / extension 完全缺） | **High** |
| Operational model      | Single-node + Patroni → distributed Raft + 自動 rebalance；HA / backup / topology 全換                                   | **High** |
| Abstraction / paradigm | Single-node MVCC + transaction → distributed Serializable Snapshot Isolation (SSI)                                       | **High** |
| Number of components   | 同 1 個 DB cluster                                                                                                       | Low      |
| Application change     | Transaction retry pattern 必須改、ORM 可能需 patch                                                                       | Medium   |

schema、operational 與 paradigm 三個面向的差異都大。其中 paradigm 從單機 transaction 換成分散式 Serializable Snapshot Isolation 是根本的轉變；operational 的差異多半是它的下游：Raft consensus、自動 rebalance、沒有 single primary，都來自分散式架構。

## Paradigm shift（主導）

CRDB 是 *distributed SQL DB*、不是「PostgreSQL 多節點版」。核心差異：

| 概念                  | PostgreSQL                                                                                                                  | CockroachDB                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Transaction isolation | MVCC、Read Committed default                                                                                                | Serializable Snapshot Isolation (SSI)、強一致              |
| Transaction conflict  | Read Committed：後到的 writer 等 row lock，前一筆 commit 後在新版本上套用；Repeatable Read 以上：後到的 writer 收到 `40001` | Retry-on-conflict、application 必須處理 `40001` retry code |
| Replication           | Streaming replication + standby                                                                                             | Raft consensus、每筆寫 quorum + 自動 rebalance             |
| Partition             | Declarative partitioning（手動）                                                                                            | Automatic range-based + locality-aware                     |
| Latency p99           | 1-10ms（單 region）                                                                                                         | 5-50ms（cross-AZ Raft quorum）                             |
| Throughput limit      | 單 primary 上限 ~10-50K TPS                                                                                                 | Linear scale by adding node、~5K TPS / node                |

關鍵 paradigm 改變：*transaction 可能在 commit 前因衝突被 abort、要由 application 重試*，atomicity 不變。所有 transaction code 需要包 retry loop（CRDB 提供 `cockroach_restart` savepoint）。

## Schema gap（PostgreSQL features CRDB 不支援）

CRDB 號稱 PostgreSQL-compatible、但 PostgreSQL 的 SQL feature 並未全數支援；常見 gap：

| PostgreSQL feature                             | CRDB 狀態                              | 影響                                                    |
| ---------------------------------------------- | -------------------------------------- | ------------------------------------------------------- |
| Stored procedure / function (PL/pgSQL)         | Limited（CRDB 22.2+ 部分支援）         | Migration scope 內必須 audit + 改寫                     |
| Common Table Expression (CTE) recursive        | Limited (depth + structure)            | 複雜 CTE 可能跑不通、必須 query refactor                |
| Window function 全集                           | Partial                                | 報表 query 需逐 case 驗證                               |
| Extensions (pg_repack / pgaudit / TimescaleDB) | **不支援**                             | 用 CRDB 自家 alternative 或自管 application 層          |
| Triggers                                       | Limited                                | Audit / data integrity 邏輯遷到 application 層          |
| Custom types / domain                          | Partial                                | 用 CHECK constraint 替代                                |
| Geographic types (PostGIS)                     | CRDB native geo support（語法不同）    | Spatial query 改寫                                      |
| `SELECT FOR UPDATE` semantics                  | 對等但底層機制不同（distributed lock） | 注意 deadlock pattern 差異                              |
| Advisory locks                                 | **不支援**                             | Application 端用其他 distributed lock（Redis / Consul） |

Migration 必須 *先 audit 完整 SQL feature 使用*、列出 gap、評估解法或退役。

## Operational redesign

CRDB operational model 完全不同：

| Operational concept | PostgreSQL self-managed               | CRDB                                              |
| ------------------- | ------------------------------------- | ------------------------------------------------- |
| Cluster bootstrap   | Patroni / Stolon + manual             | `cockroach init` + 自動 Raft formation            |
| HA                  | Patroni + DCS + watchdog              | 內建 Raft、無 single primary                      |
| Failover            | Patroni-managed、15-60s               | 透明 Raft re-election、< 5s                       |
| Backup              | pgBackRest + WAL archive              | `BACKUP TO` (incremental + full)                  |
| Restore             | `pgBackRest restore` + PITR           | `RESTORE FROM`                                    |
| Replication         | Streaming + logical                   | Built-in、無 logical replication 對等概念         |
| Schema migration    | `pg_dump` / Flyway / Liquibase        | `cockroach sql` + online schema change（無 lock） |
| Monitoring          | pg_stat_* views + Prometheus exporter | CRDB admin UI + Prometheus（schema 不同）         |
| Sizing              | Vertical scale（單 node big spec）    | Horizontal scale（多 node 小 spec）               |

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

### Transaction retry 沒處理、application 大量 `40001` error

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

### Extension 缺位、application feature 整段掉

**徵兆**：cutover 後 application 某個地理計算功能直接報錯、PostGIS 函數不存在；migrate 計畫漏看。

**根因**：CRDB native geo 不同 syntax / API、PostGIS extension 不能直接搬。

**修法**：

1. **Pre-migration 必跑 extension audit**：列所有 `pg_extension`、找對應 CRDB feature 或退役
2. **PostGIS 替代**：CRDB native ST_* functions、部分 syntax 對齊但 spatial index 不同
3. **退役不能換的 feature**：評估保留 PostgreSQL（混合架構）

### Sequential PK 撞 Raft quorum 瓶頸

**徵兆**：cutover 後寫入吞吐量 / latency 不如預期、CRDB cluster CPU < 30% 但 write latency p99 high。

**根因**：application 用 `SERIAL` / `IDENTITY` 產生連續 PK；CRDB 把連續 key 放 *同一 range* / 同一 Raft group、寫入串行化、無法平行 scale。

**修法**：

1. **改 UUID v4（`gen_random_uuid()`）或 hash-sharded index**：CockroachDB 的 `SERIAL` 預設（`serial_normalization = rowid`）就是 `DEFAULT unique_rowid()`，值由時間戳與 node ID 組成、隨時間遞增，UUID v7 同樣隨時間遞增，`unique_rowid()` 與 UUID v7 的寫入都集中在 key 範圍尾端的 range；UUID v4 把 key 散到各 range，必須保留時序 key 時改用 hash-sharded index 把連續寫入分到多個 range
2. **`PRIMARY KEY (region, id)`**：multi-region 場景 multi-tenancy 自然拆分
3. **不適合的 workload 留 PostgreSQL**：不是所有 schema 都適合 distributed

### Long transaction 對 Raft 衝擊

**徵兆**：跨 1 分鐘+ 的 transaction（batch processing / 大 ETL）大量 retry、最後失敗；同期間其他短 transaction 也 retry rate 上升。

**根因**：CRDB long transaction holds intent on touched ranges、阻塞其他 transaction；SSI conflict 機率隨 transaction 時間平方增長。

**修法**：

1. **Long transaction 拆短**：batch 用多個 short transaction、checkpoint 在 application 層
2. **Heavy ETL 不跑 CRDB**：用 CRDB CDC export 到 OLAP（Snowflake / BigQuery）跑 batch
3. **Read-only long transaction 用 follower read**：`AS OF SYSTEM TIME` 不 hold intent、適合 reporting

### Backup / restore 行為跟 PostgreSQL 不同、SRE runbook 失效

**徵兆**：DBA 嘗試 `pg_restore` 失敗、CRDB 端 backup format 完全不同；incident response 卡關 1-2 小時。

**根因**：CRDB backup 是 *cluster-internal format*、不能用 PostgreSQL tooling；SRE runbook 仍是 PostgreSQL world、應急時心智模型錯位。

**修法**：

1. **Runbook 重寫**：CRDB-specific backup / restore 流程、SRE training
2. **DR drill**：cutover 前跑完整 DR drill、用 CRDB tooling 完成、不依賴 PostgreSQL 經驗
3. **Multi-region backup**：CRDB 跨 region backup 配置、避免單 region 故障

## Capacity 規劃

| 維度                | PostgreSQL self-managed                      | CockroachDB                                         |
| ------------------- | -------------------------------------------- | --------------------------------------------------- |
| Single-node 上限    | ~10-50K TPS（vertical scale 到 32-128 vCPU） | ~5K TPS / node（horizontal scale by adding node）   |
| 跨 region           | 高 latency 跨區 streaming                    | 設計 native、Locality-aware queries                 |
| Sharding            | 手動 partition / pg_partman                  | 自動 range-based                                    |
| Storage / TPS ratio | 不變                                         | Storage 跨 node 3x（Raft quorum 3-replica default） |
| Total cost (10TB)   | $2-4K USD / month（self-managed）            | $5-10K USD / month（CRDB Cloud + 3x storage）       |

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
- PostgreSQL 的其他主題：[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/) / [Logical Replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/) / [Process content 結構由最大差異維度決定](/report/content-structure-by-max-diff-dimension/)
