---
title: "MySQL Hands-on 操作路線"
date: 2026-05-22
description: "MySQL local lab、ProxySQL routing、online schema change、replication failover、backup restore 與 Vitess sandbox 的操作型章節設計"
tags: ["backend", "database", "mysql", "hands-on"]
---

MySQL hands-on 操作路線的核心責任是把 MySQL deep article 的設定與 failure mode 轉成可演練流程。這一層對齊 LLM `hands-on/`：讀者能跑出 config、metric、validation query 與 rollback evidence。

## 章節列表

| 章節                                                  | 主題                                                           | 產出 artifact                                    |
| ----------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------ |
| [Local lab quickstart](local-lab-quickstart/)         | MySQL container、sample schema、baseline workload              | local DSN、schema log、basic metric snapshot     |
| [ProxySQL routing lab](proxysql-routing-lab/)         | read/write split、lag-aware routing、runtime / disk config     | ProxySQL config、routing evidence、drift note    |
| [Online schema change lab](online-schema-change-lab/) | gh-ost / pt-osc cutover、metadata lock、rollback               | OSC command、cutover note、lock evidence         |
| [Replication failover lab](replication-failover-lab/) | GTID replica、semi-sync、Orchestrator / manual failover        | topology map、lag evidence、failover timeline    |
| [Backup restore drill](backup-restore-drill/)         | logical / physical backup、binlog recovery、restore validation | restore record、RPO / RTO evidence               |
| [Vitess sandbox route](vitess-sandbox-route/)         | keyspace、VSchema、VTGate / VTTablet sandbox                   | sandbox topology、routing sample、shard key note |

## 設計原則

MySQL hands-on 章節要保留「高併發簡單 OLTP + 分片生態」的服務語言。操作章節不只給指令，也要說明 command 產出的 evidence 如何回到 replication、schema change、connection routing 或 sharding decision。

## 引用路徑

- 上游：[MySQL overview](/backend/01-database/vendors/mysql/)
- Deep article：[ProxySQL Config](/backend/01-database/vendors/mysql/proxysql-config/)、[Online Schema Change Tools](/backend/01-database/vendors/mysql/online-schema-change-tools/)、[Replication Topology](/backend/01-database/vendors/mysql/replication-topology/)、[Vitess Sharding](/backend/01-database/vendors/mysql/vitess-sharding/)
