---
title: "PostgreSQL to YugabyteDB / TiDB Migration"
date: 2026-05-22
description: "PostgreSQL 轉向 YugabyteDB、TiDB 類 distributed SQL 的 compatibility audit、data topology、transaction、cutover 與 rollback"
tags: ["backend", "database", "postgresql", "migration", "distributed-sql"]
---

PostgreSQL to YugabyteDB / TiDB migration 的核心責任是處理從 single-primary PostgreSQL 走向 distributed SQL 的資料拓撲變更。這條路線通常由 multi-region write、horizontal scale、tenant sharding、availability 或 single-node capacity ceiling 觸發；其中 YugabyteDB 走 PostgreSQL-compatible YSQL 路線，TiDB 走 MySQL-compatible distributed SQL 路線，兩者的 application diff audit 不同。

本文的判讀錨點是：API compatibility 只解決入口語法的一部分。YugabyteDB 要審查 PostgreSQL 相容與 distributed operation 差異；TiDB 要額外處理 PostgreSQL → MySQL dialect / driver / tooling 轉換。Distributed SQL 會改變 transaction latency、placement、index cost、DDL、sequence、lock、backup、observability 與 incident route。

## Official Documentation Route

Official documentation route 的核心責任是把 compatibility claim 固定到可回查來源。YugabyteDB compatibility 先查 [YugabyteDB PostgreSQL compatibility](https://docs.yugabyte.com/stable/reference/configuration/postgresql-compatibility/)；TiDB compatibility 先查 [TiDB MySQL compatibility](https://docs.pingcap.com/tidb/stable/mysql-compatibility/)；本文最後檢查日是 2026-05-22。

## Driver Check

Driver check 的核心責任是確認 distributed SQL 解決的是核心問題。

| Driver                    | 代表需求                       | 審查問題                            |
| ------------------------- | ------------------------------ | ----------------------------------- |
| Multi-region write        | 多地使用者都要低延遲寫入       | consistency level、latency budget   |
| Horizontal write scaling  | 單 primary CPU / I/O 到頂      | shard key、hot key、cross-shard txn |
| Tenant distribution       | tenant 可依 region / size 分布 | tenant placement、rebalance         |
| Availability              | 節點 / zone failure 容忍       | quorum、failover、RPO / RTO         |
| Operational consolidation | 多 PG shard 想收斂             | migration complexity、cost          |

若主要問題是 read scaling、connection 數或 query index，先評估 read replica、pooler、partition、Citus 或 Aurora；distributed SQL 適合資料拓撲問題。

## Compatibility Audit

Compatibility audit 的核心責任是把 PostgreSQL behavior 逐項對照 target。

| 面向           | 審查問題                                                   |
| -------------- | ---------------------------------------------------------- |
| Protocol / API | YugabyteDB YSQL vs TiDB MySQL protocol                     |
| SQL dialect    | function、extension、type、DDL support                     |
| Transaction    | isolation、lock、deadlock、retry                           |
| Sequence / ID  | global sequence latency、UUID policy                       |
| Index          | secondary index placement、write cost                      |
| Foreign key    | distributed FK cost / support                              |
| Extension      | PostGIS、pgvector、custom extension；TiDB 路線需改寫或拆出 |
| Tooling        | migration tool、CDC、backup、monitoring                    |

Compatibility audit 要用 application query suite。只看 schema import 會漏掉 transaction retry、query planner、distributed index、dialect rewrite 與 latency。TiDB 路線還要加 PostgreSQL driver / SQL / type / migration tool 轉 MySQL ecosystem 的審查。

## Data Topology

Data topology 的核心責任是決定資料如何分布。Distributed SQL 的成敗常取決於 primary key、tenant key、region placement 與 hot key 控制。

| 拓撲決策         | 判讀問題                             |
| ---------------- | ------------------------------------ |
| Distribution key | query 是否能 co-locate data          |
| Region placement | 資料是否需要 residency / low latency |
| Hot key          | high-write tenant / account 是否集中 |
| Secondary index  | index write 是否跨 shard / region    |
| Transaction span | 交易是否常跨 tenant / region         |

Topology 設計要從最高頻 workflow 開始。若核心交易每次都跨 shard，distributed SQL 的 latency 與 conflict cost 會很高。

## Migration Phases

Migration phases 的核心責任是降低跨拓撲遷移風險。

| Phase           | Evidence                                |
| --------------- | --------------------------------------- |
| Lab import      | schema import、query suite、driver test |
| Topology design | key、placement、region、index review    |
| Backfill        | snapshot、batch、checksum               |
| CDC catch-up    | LSN / change stream、lag、idempotency   |
| Shadow read     | result diff、latency profile            |
| Cutover         | freeze、final sync、traffic switch      |
| Rollback        | source PG snapshot、write replay plan   |

CDC catch-up 要有 clear cutover LSN。Distributed SQL migration 最怕 source / target 同時有寫入後，缺少 reconciliation plan。

## Application Changes

Application changes 的核心責任是讓程式接受 distributed system 的錯誤模式。

1. Transaction retry：serialization / conflict error 要可重試。
2. Idempotency：critical write 要有 natural key 或 idempotency key。
3. Latency budget：跨 region transaction 要進 SLO。
4. Pagination / ordering：distributed query 的排序成本要審查。
5. Connection / driver：target driver、TLS、pooling、load balancing 要測。

Application 若假設 single-node low-latency transaction，遷移後會在 tail latency 與 retry 行為上出現落差。TiDB 路線還會出現 driver、placeholder、SQL function、type mapping 與 error code 的轉換成本；這些要在 staging failure injection 先看到。

## No-Go Conditions

No-go conditions 的核心責任是阻止把 distributed SQL 當成萬用擴容。

| No-go 訊號                             | 替代路由                                   |
| -------------------------------------- | ------------------------------------------ |
| 主要瓶頸是少數 slow query              | query optimization / index                 |
| 多數交易跨全局資料                     | 重設 bounded context 或保持 single primary |
| Team 缺少 distributed operation 能力   | managed provider / simpler topology        |
| PostgreSQL extension 依賴重            | 保留 PG 或拆出 specialized service         |
| RPO / rollback 沒有演練                | 先完成 migration playbook                  |
| 想保留 PostgreSQL driver / SQL surface | 優先評估 YugabyteDB / CockroachDB / Citus  |

Distributed SQL 的價值來自拓撲匹配。若 workload 缺少自然分布邊界，導入後只是把單點瓶頸換成分散式複雜度。

## 下一步路由

PostgreSQL to YugabyteDB / TiDB migration 完成後，先讀 [Global Distributed OLTP](/backend/01-database/global-distributed-oltp/)；若需求是 PostgreSQL 內分散式 table，讀 [Citus Distributed](../citus-distributed/)；跨 vendor 流程讀 [Database Migration Playbook](/backend/01-database/database-migration-playbook/)。
