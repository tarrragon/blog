---
title: "Managed PostgreSQL Comparison"
date: 2026-05-22
weight: 48
description: "RDS PostgreSQL、Aurora PostgreSQL、Cloud SQL、Azure Database for PostgreSQL、Neon、Supabase、Crunchy Bridge 的責任邊界比較"
tags: ["backend", "database", "postgresql", "managed-service"]
---

Managed PostgreSQL comparison 的核心責任是把「都是 PostgreSQL」拆成不同的操作責任邊界。Managed service 可能代管 backup、patch、replica、minor upgrade、monitoring、connection proxy、serverless scaling 或 branch workflow；但 application schema、query、migration、role、cost 與 incident decision 仍需要 team 承擔。

本文的判讀錨點是：managed PostgreSQL 是 operation trade-off，而非 vendor-neutral checkbox。選型要看 workload、合規、extension、HA / DR、connection、cost visibility、exit route 與 team skill。

官方文件路由的核心責任是固定 provider claim。實作前分別查 [AlloyDB docs](https://docs.cloud.google.com/alloydb/docs)、[Cloud SQL for PostgreSQL](https://cloud.google.com/sql/postgresql)、[Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/overview) 與 [Supabase branching docs](https://supabase.com/docs/guides/deployment/branching)；本文最後檢查日是 2026-05-22。

## Provider Boundary

Provider boundary 的核心責任是定義 vendor 接手哪些資料庫操作。

| 類型                         | 代表選項                            | 適合情境                                     |
| ---------------------------- | ----------------------------------- | -------------------------------------------- |
| Cloud managed PostgreSQL     | RDS PostgreSQL、Cloud SQL、Azure PG | 標準 PostgreSQL、雲平台整合                  |
| Aurora PostgreSQL-compatible | Amazon Aurora PostgreSQL            | AWS 生態、高可用 storage layer、read scaling |
| Serverless / branching PG    | Neon、Supabase 部分能力             | dev preview、稀疏 workload、快速分支         |
| Specialist managed PG        | Crunchy Bridge 等                   | PostgreSQL 專業支援、extension 需求          |
| Self-managed                 | VM / K8s 上自管                     | 需要完整控制、具備 DBA 能力                  |

Provider boundary 要寫成 responsibility matrix。誰負責 backup restore、major upgrade、extension enable、failover、connection proxy、audit export、encryption key、support ticket 與 incident decision。

Serverless / branching PG 這一列的 Neon 與 Supabase 不在同一個 [外包深度](/backend/knowledge-cards/capability-outsourcing-depth/)。Neon 是純 serverless PostgreSQL（managed 基礎設施）；Supabase 是把 Postgres 當其中一塊的 [BaaS bundle](/backend/knowledge-cards/baas/)（同時含 Auth、Storage、Realtime）。只需要資料庫、兩者皆可比較且 Neon 更輕；要連認證、儲存一起到位、才是 Supabase 的賣點。這個外包深度差異與「該買整個 bundle 還是只用它的 Postgres」的判讀、見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

## Evaluation Dimensions

Evaluation dimensions 的核心責任是讓比較避免只看價格或品牌。

| 維度                | 審查問題                                               |
| ------------------- | ------------------------------------------------------ |
| PostgreSQL fidelity | engine version、extension、parameter、superuser 限制   |
| HA / DR             | AZ failover、cross-region replica、PITR、restore drill |
| Connection          | max connection、pooler、proxy、serverless cold start   |
| Migration           | import/export、logical replication、downtime window    |
| Observability       | logs、metrics、slow query、audit、SIEM export          |
| Security            | network、IAM、KMS、TLS、RLS / pgAudit support          |
| Cost                | instance、storage、I/O、backup、egress、support        |
| Exit                | dump、logical replication、snapshot portability        |

PostgreSQL fidelity 是第一關。若服務依賴 extension、logical decoding、superuser function、custom parameter 或 filesystem access，managed provider 的限制會直接影響可行性。

## Workload Fit

Workload fit 的核心責任是把 provider 能力和產品需求對齊。

| Workload             | 優先考量                                                 |
| -------------------- | -------------------------------------------------------- |
| SaaS OLTP            | HA、PITR、connection pool、online migration              |
| Analytics-heavy OLTP | read replica、I/O cost、work_mem、warehouse boundary     |
| Dev / preview env    | branching、fast restore、low idle cost                   |
| Regulated workload   | audit、KMS、network isolation、retention                 |
| Extension-heavy app  | PostGIS、pgvector、TimescaleDB、logical decoding support |

Serverless / branching PG 適合 preview 與稀疏 workload，但 sustained high-throughput production 要審查 cold start、connection、storage separation latency 與 cost curve。

Aurora PostgreSQL 適合 AWS-heavy 架構與高可用 storage layer，但要審查 PostgreSQL compatibility、parameter 限制、I/O cost 與 migration / exit。

## Migration and Exit

Migration and exit 的核心責任是避免 managed service 變成單向門。導入前要先知道如何進去、如何出來。

| 流程      | Evidence                                      |
| --------- | --------------------------------------------- |
| Import    | dump / restore、logical replication、DMS      |
| Cutover   | freeze window、replica catch-up、validation   |
| Rollback  | source snapshot、write replay、DNS switch     |
| Exit      | pg_dump、logical replication、snapshot export |
| Rehearsal | staging restore、row count、checksum          |

Exit route 要比口頭承諾更具體。至少要能在 staging 將資料匯出到 vanilla PostgreSQL 或下一個 managed provider，並跑 application smoke test。

## Cost Review

Cost review 的核心責任是把 managed convenience 轉成總成本。總成本包含 instance、storage、I/O、backup、replica、egress、support、observability、operation labor 與 incident cost。

| Cost driver          | 常見誤判                              |
| -------------------- | ------------------------------------- |
| I/O                  | 只看 instance price                   |
| Backup retention     | 長 retention 被忽略                   |
| Cross-region replica | data transfer / storage 增加          |
| Observability export | log volume 與 SIEM 成本               |
| Serverless idle      | idle 低但 sustained workload 成本不同 |

Cost review 要設 tripwire。當 I/O 成本占比提高、backup retention 變長、replica 增加或 serverless workload 變成常駐，重新評估方案。

## Decision Route

Decision route 的核心責任是把 provider 選型導向具體路線。

| 需求                        | 優先路由                        |
| --------------------------- | ------------------------------- |
| 標準雲平台 PostgreSQL       | RDS / Cloud SQL / Azure PG      |
| AWS 生態 + HA storage layer | Aurora PostgreSQL               |
| Preview branch / dev env    | Neon / Supabase branch workflow |
| Extension / PG 專業支援     | specialist managed PG           |
| 完整控制與特殊 extension    | self-managed PostgreSQL         |

Managed provider 的最終選擇要回到 team skill。少維護元件是價值；把尚未理解的限制外包給 vendor，會在 incident 和 migration 時回來。

## 下一步路由

Managed PostgreSQL comparison 完成後，Aurora 遷移讀 [PostgreSQL to Aurora Migration](../migrate-to-aurora/)；Aurora DSQL 讀 [PostgreSQL to Aurora DSQL](../migrate-to-aurora-dsql/)；serverless / specialized variant 讀 [Specialized PostgreSQL Variants](../specialized-pg-variants/)。
