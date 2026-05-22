---
title: "PostgreSQL pg_partman Advanced"
date: 2026-05-22
description: "PostgreSQL pg_partman 自動分區、premake、retention、maintenance job、partition migration 與 runbook"
tags: ["backend", "database", "postgresql", "partitioning", "pg-partman"]
---

PostgreSQL pg_partman advanced 的核心責任是把 declarative partitioning 的日常維護自動化。pg_partman 可以協助建立未來 partition、管理 retention、執行 maintenance job，讓 time-based 或 serial-based partition 不再依賴人工 DDL。

本文的判讀錨點是：pg_partman 解決的是 partition lifecycle operation，而非 partition strategy 本身。Partition key、query pattern、retention、index、foreign key 與 migration 仍要先在 [Declarative Partitioning](../declarative-partitioning/) 與 [Partition Redesign](../partition-redesign/) 做對。

## Responsibility Boundary

Responsibility boundary 的核心責任是區分 PostgreSQL 原生 partition 和 pg_partman。

| 層級                                | 責任                                             |
| ----------------------------------- | ------------------------------------------------ |
| PostgreSQL declarative partitioning | partition table、constraint、planner pruning     |
| pg_partman                          | future partition premake、retention、maintenance |
| Scheduler / job runner              | 定期執行 maintenance                             |
| DBA / platform                      | monitoring、backup、DDL review                   |
| Application                         | query pattern、partition key 使用                |

pg_partman 的價值在於減少重複 DDL。它不會替 application 選出正確 partition key，也不會自動修復跨 partition query 設計。

## Core Concepts

Core concepts 的核心責任是理解 pg_partman operation vocabulary。

| 概念         | 意義                                           |
| ------------ | ---------------------------------------------- |
| Parent table | partitioned table 的入口                       |
| Child table  | 實際存放資料的 partition                       |
| Premake      | 預先建立未來 partition                         |
| Retention    | 自動 detach / drop 舊 partition                |
| Maintenance  | 建立新 partition、處理 retention 的 job        |
| Template     | child partition 繼承 index / constraint 的模板 |

Premake 是防止 insert 打到不存在 partition 的保護。若 partition 建立落後於時間，application insert 會失敗或落到 default partition；production 要對 future partition count 設 alert。

Retention 是資料生命週期操作。Drop 舊 partition 速度快，但要先確認 legal retention、backup、analytics dependency 與 downstream CDC。

## Setup Pattern

Setup pattern 的核心責任是把 pg_partman 導入流程放進 migration gate。

```sql
CREATE EXTENSION IF NOT EXISTS pg_partman;

CREATE TABLE events (
  id bigserial,
  tenant_id uuid NOT NULL,
  created_at timestamptz NOT NULL,
  payload jsonb NOT NULL
) PARTITION BY RANGE (created_at);
```

實際建立 partman config 要依 pg_partman 版本與 provider 支援文件執行。Managed PostgreSQL 可能限制 extension version、background worker 或 scheduler，因此 setup 前要先確認 provider boundary。

最小 setup evidence：

1. Extension version。
2. Parent table DDL。
3. Partition key 與 interval。
4. Premake 數量。
5. Retention policy。
6. Maintenance job schedule。
7. Test insert 到 current / future partition。

## Maintenance Runbook

Maintenance runbook 的核心責任是讓 partition lifecycle 可觀測。

| Signal                 | 意義                          | 反應                                   |
| ---------------------- | ----------------------------- | -------------------------------------- |
| future partition count | premake 是否足夠              | 手動跑 maintenance、修 scheduler       |
| default partition rows | routing 失敗或 partition 缺漏 | 建 partition、搬資料、修 app timestamp |
| old partition count    | retention 是否執行            | 檢查 policy、legal hold、job error     |
| maintenance duration   | DDL / lock / catalog 壓力     | 調整 schedule、拆 table                |
| index build time       | child index 建立成本          | template / concurrent strategy review  |

Maintenance job 要有 owner。Cron、pg_cron、background worker、Kubernetes job 或 managed scheduler 都可以；重點是 job failure 會告警，並且有人處理。

## Migration and Backfill

Migration and backfill 的核心責任是把既有大表轉成 partman-managed partition。這通常比新表導入更高風險。

| Phase      | Evidence                              |
| ---------- | ------------------------------------- |
| Audit      | table size、query pattern、write rate |
| New schema | parent table、child partition、index  |
| Backfill   | batch size、lag、lock、checksum       |
| Dual write | app compatibility                     |
| Cutover    | rename / view / routing switch        |
| Cleanup    | old table retention、rollback         |

Backfill 要控制 WAL、replica lag、autovacuum、index bloat 與 lock。大型 table 應先用 shadow table 或 partition redesign playbook，避開 peak traffic 直接重建。

## Failure Modes

Failure modes 的核心責任是列出 pg_partman 常見事故。

| Failure mode            | 判讀訊號                             | 修正方向                                |
| ----------------------- | ------------------------------------ | --------------------------------------- |
| 未建立未來 partition    | insert 失敗或 default partition 增長 | 補 partition、修 maintenance schedule   |
| retention drop 過早     | 查詢缺歷史資料                       | restore backup、調 policy、legal review |
| managed provider 不支援 | extension / worker 限制              | 改 manual partition job 或 provider     |
| index / constraint 漂移 | child partition schema 不一致        | template review、schema diff            |
| planner pruning 失效    | query 未帶 partition key             | query rewrite、index review             |

pg_partman 事故通常是 lifecycle 事故。Runbook 要先看 maintenance job，再看 partition metadata 與 application query。

## 下一步路由

pg_partman advanced 完成後，partition 設計讀 [Declarative Partitioning](../declarative-partitioning/)；重排策略讀 [Partition Redesign](../partition-redesign/)；migration gate 讀 [Online Schema Change](../online-schema-change/)。
