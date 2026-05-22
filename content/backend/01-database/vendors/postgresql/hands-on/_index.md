---
title: "PostgreSQL Hands-on 操作路線"
date: 2026-05-22
description: "PostgreSQL local lab、connection pool、PITR restore drill、schema migration evidence 與 HA failover 的操作型章節設計"
tags: ["backend", "database", "postgresql", "hands-on"]
---

PostgreSQL hands-on 操作路線的核心責任是把 overview 與 deep article 的判讀轉成可演練的操作流程。這一層對齊 LLM `hands-on/` 的功能：讀者不只知道 PostgreSQL 的機制，也能在 local lab 或 staging 產出可驗證 artifact。

## 章節列表

| 章節                                                            | 主題                                                              | 產出 artifact                                          |
| --------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------ |
| [Local lab quickstart](local-lab-quickstart/)                   | Docker Compose 啟動 PostgreSQL、建立 schema、跑 sample workload   | local DSN、schema migration log、basic metric snapshot |
| [Connection pool lab](connection-pool-lab/)                     | application pool → pgBouncer → PostgreSQL 的連線壓力演練          | pool config、connection count evidence、failure note   |
| [PITR restore drill](pitr-restore-drill/)                       | base backup + WAL archive + restore target time 的恢復演練        | restore record、RPO / RTO evidence、validation query   |
| [Schema migration evidence lab](schema-migration-evidence-lab/) | expand / contract migration、validation query、rollback condition | migration plan、row count、rollback note               |
| [HA failover drill](ha-failover-drill/)                         | Patroni / managed failover 的 application impact 演練             | failover timeline、client error sample、decision log   |

## 設計原則

PostgreSQL hands-on 章節只收錄能產出 evidence 的操作。純安裝指令留給官方文件；本路線要教讀者如何知道設定生效、失敗時看到什麼、以及 evidence 要交給 04 / 06 / 08 的哪個 artifact。

## 引用路徑

- 上游：[PostgreSQL overview](/backend/01-database/vendors/postgresql/)
- Deep article：[pgBouncer Config](/backend/01-database/vendors/postgresql/pgbouncer-config/)、[PITR + WAL Archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)、[Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)
- 跨模組：[Observability Evidence Package](/backend/04-observability/observability-evidence-package/)、[Migration Safety](/backend/06-reliability/migration-safety/)、[Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
