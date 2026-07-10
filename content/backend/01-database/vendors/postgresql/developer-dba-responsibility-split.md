---
title: "PostgreSQL Developer / DBA Responsibility Split"
date: 2026-05-22
weight: 39
description: "PostgreSQL application developer、DBA、platform team 在 schema、query、migration、backup、incident 與 capacity 的責任分工"
tags: ["backend", "database", "postgresql", "operations", "ownership"]
---

PostgreSQL developer / DBA responsibility split 的核心責任是把資料庫決策拆成 application ownership、database operation 與 platform governance。PostgreSQL 功能深，事故常跨 query、schema、connection、backup、replication 與 capacity；若責任分工模糊，問題會在 release 與 incident 時放大。

本文的判讀錨點是：developer 和 DBA 分工要讓每個決策有清楚 owner、evidence、review gate 與 rollback，而非把資料庫丟給某一方。

## Ownership Map

Ownership map 的核心責任是定義誰能改什麼、誰要驗證什麼。

| 面向              | Developer owner                 | DBA / platform owner                  | Shared gate      |
| ----------------- | ------------------------------- | ------------------------------------- | ---------------- |
| Schema design     | domain model、constraint、query | naming、storage、partition、extension | migration review |
| Query performance | repository SQL、query shape     | index、planner、statistics、capacity  | explain evidence |
| Migration         | app compatibility、rollback     | lock impact、DDL strategy、PITR       | release gate     |
| Connection        | pool usage、transaction length  | pooler、max connection、proxy         | load test        |
| Backup / DR       | restore smoke test              | WAL archive、PITR、replica            | restore drill    |
| Security          | tenant / workflow intent        | role、RLS、audit、grant               | access review    |

這張表的重點是 shared gate。Developer 最懂產品語意，DBA / platform 最懂資料庫風險；正式變更需要兩邊的 evidence 合併。

## Schema and Migration

Schema and migration 的核心責任是讓 application release 與 database change 同步。Developer 應提供 business invariant、compatibility window、read/write path；DBA / platform 應審查 lock、index build、table rewrite、replica lag 與 rollback。

| Migration 類型      | Developer evidence                   | DBA / platform evidence             |
| ------------------- | ------------------------------------ | ----------------------------------- |
| Add nullable column | app read/write compatibility         | DDL lock time、replica impact       |
| Add NOT NULL        | backfill plan、default behavior      | table rewrite / validation strategy |
| Index build         | query contract、expected selectivity | concurrent build、disk、bloat       |
| Partition change    | routing logic、retention behavior    | detach / attach、maintenance window |
| Type change         | serialization、API compatibility     | cast risk、rewrite duration         |

Migration review 要從 failure mode 開始。若 migration 卡住，誰停止 rollout；若 backfill 造成 lag，誰降速；若 app 新舊版本同時存在，哪個 schema 能兼容兩者。

## Query and Capacity

Query and capacity 的核心責任是把 query shape 和 database resource 對齊。Developer 負責避免 N+1、長交易、無界查詢與錯誤 pagination；DBA / platform 負責 index、statistics、vacuum、work_mem、connection 與 storage。

Query review 的最小 evidence：

1. SQL text 或 repository method。
2. Expected cardinality 與資料量。
3. `EXPLAIN` / `EXPLAIN ANALYZE` 結果。
4. Index 依賴與 fallback plan。
5. Timeout、pagination、transaction boundary。

Capacity review 要把 query 放進 workload。單一 query 快不代表整體穩定；高頻 query、batch job、migration backfill、CDC consumer 都會共享 I/O、CPU、lock 與 WAL。

## Incident Roles

Incident roles 的核心責任是讓資料庫事故有分工。Incident 發生時，developer 看 workflow、feature flag、traffic 與 recent deploy；DBA / platform 看 lock、replica、WAL、disk、pooler 與 backup。

| Incident              | Developer 第一反應                   | DBA / platform 第一反應                    |
| --------------------- | ------------------------------------ | ------------------------------------------ |
| Lock storm            | 暫停相關 workflow、停 rollout        | 查 blocking PID、DDL、transaction          |
| Connection exhaustion | 降低 app concurrency、停 retry storm | pooler queue、max connection、admin access |
| Replica lag           | 暫停 heavy write / backfill          | WAL sender、slot、standby apply            |
| Bad migration         | block release、保留 failed state     | restore point、rollback / PITR             |
| Slow query spike      | feature flag、query owner            | plan regression、statistics、index         |

Incident command 要保留決策紀錄。資料庫事故常有高壓操作，例如 kill session、promote replica、drop slot、restore backup；每個操作都要記錄原因與回復路線。

## Review Cadence

Review cadence 的核心責任是把資料庫品質納入日常。建議節奏如下：

| 節奏         | Review 內容                                    |
| ------------ | ---------------------------------------------- |
| 每個 release | migration diff、new query、role / grant        |
| 每週         | slow query、lock wait、replica lag、pool       |
| 每月         | backup restore drill、index bloat、vacuum      |
| 每季         | DR drill、major version plan、extension review |

Review cadence 要跟服務風險對齊。高交易量或合規服務需要更短週期；內部工具可以更輕量，但仍要保留 backup / restore evidence。

## Handoff Artifact

Handoff artifact 的核心責任是讓下一位維護者能接手。

最小內容：

1. Database owner、application owner、platform owner。
2. Schema migration process 與 rollback route。
3. Query review checklist。
4. Connection / pooler policy。
5. Backup / PITR / DR evidence。
6. Security / role / audit owner。
7. Incident escalation route。

這份 artifact 應連回 [PostgreSQL overview](../)、[Schema Migration Evidence Lab](../hands-on/schema-migration-evidence-lab/) 與 [PITR Restore Drill](../hands-on/pitr-restore-drill/)。

## 下一步路由

責任分工建立後，migration gate 讀 [Online Schema Change](../online-schema-change/)；連線責任讀 [Connection Pooler Comparison](../connection-pooler-comparison/)；安全責任讀 [Security / RLS / Audit Logging](../security-rls-audit-logging/)。
