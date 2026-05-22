---
title: "MySQL Metadata Lock Deep Dive"
date: 2026-05-22
description: "MySQL metadata lock、DDL blocking、long transaction、online schema change、MDL observability 與 incident runbook"
tags: ["backend", "database", "mysql", "metadata-lock", "ddl"]
---

MySQL metadata lock deep dive 的核心責任是說明 DDL、transaction 與 table metadata 之間的阻塞關係。MySQL 在查詢 table 時會取得 [metadata lock](/backend/knowledge-cards/metadata-lock/)；DDL 需要等待既有 metadata lock 釋放，等待中的 DDL 又會阻塞後續查詢，形成 production 常見雪崩。

本文的判讀錨點是：MDL 事故通常來自 DDL 排隊在長交易後面，並把後續 query 一起擋住。解法要同時處理 long transaction、DDL window、OSC 工具與 observability。

## Lock Lifecycle

Lock lifecycle 的核心責任是建立 MDL 心智模型。

| 行為                 | MDL 影響                               |
| -------------------- | -------------------------------------- |
| `SELECT` / DML       | 取得 table metadata lock，交易結束釋放 |
| Long transaction     | 延長 metadata lock 持有時間            |
| `ALTER TABLE`        | 等待相容鎖，期間可能阻塞後續 query     |
| Online schema change | 仍需 metadata lock 進行切換 / rename   |
| Idle transaction     | 看似無操作，仍可能持有 metadata lock   |

MDL 的風險在於排隊。當 `ALTER TABLE` 等待 long transaction 時，後續新的 query 可能排在 DDL 後面，讓原本小變更變成服務不可用。

## Detection

Detection 的核心責任是快速找出誰持鎖、誰等待。

```sql
SELECT *
FROM performance_schema.metadata_locks
WHERE OBJECT_SCHEMA = 'appdb'
ORDER BY OBJECT_NAME, LOCK_STATUS;
```

搭配 processlist：

```sql
SHOW FULL PROCESSLIST;
```

Production dashboard 應監控 running DDL、metadata lock wait、long transaction age、threads running、blocked query count 與 replication lag。

## DDL Risk Review

DDL risk review 的核心責任是在變更前預測 MDL 風險。

| DDL 類型            | 風險                        | 控制方式                              |
| ------------------- | --------------------------- | ------------------------------------- |
| Add nullable column | 依版本 / algorithm 可能較低 | staging dry run、algorithm check      |
| Add index           | 可能長時間操作與切換 lock   | online DDL / OSC、低峰窗口            |
| Change column type  | table rebuild 風險高        | ghost table / phased migration        |
| Rename / swap table | 短暫但關鍵 MDL              | kill blocker、短窗口                  |
| Drop column / table | destructive 且需鎖          | backup、approval、blocked query watch |

DDL review 要列出 algorithm、lock mode、預估時間、rollback、kill blocker policy 與 replication impact。

## Incident Runbook

Incident runbook 的核心責任是把 MDL 事故分流。

| Step             | 操作                                 |
| ---------------- | ------------------------------------ |
| Identify blocker | 查 long transaction / metadata_locks |
| Stop new DDL     | 暫停 migration pipeline              |
| Decide kill      | 依 owner / transaction age / impact  |
| Protect app      | 降低 traffic、停 heavy endpoint      |
| Validate         | 查 query 恢復、replication lag       |
| Retrospective    | 補 DDL gate、long transaction alert  |

Kill session 是高風險操作。決策要記錄 transaction owner、已執行時間、可能 rollback 成本與業務影響。

## OSC Interaction

OSC interaction 的核心責任是說明 gh-ost / pt-online-schema-change 仍需要 MDL 管理。Ghost table 工具把大部分 copy 與 backfill 移到旁路，但最後 cutover / rename 仍需要短暫 metadata lock。

| 工具階段           | MDL 風險                      |
| ------------------ | ----------------------------- |
| Create ghost table | 低                            |
| Copy / backfill    | 主要是 load / replication lag |
| Trigger / binlog   | 依工具模式不同                |
| Cutover / rename   | 關鍵 MDL window               |

OSC runbook 要在 cutover 前檢查 long transaction。若 blocker 存在，先延後 cutover，而非硬切。

## Prevention

Prevention 的核心責任是讓 MDL 事故在 release 前被擋下。

1. Long transaction alert。
2. DDL dry run 與 algorithm / lock mode 記錄。
3. Migration window 與 kill blocker policy。
4. OSC cutover pre-check。
5. Application transaction timeout。
6. Read-only replica 上先測 schema change。

MDL 是 MySQL schema governance 的核心議題。每個 production DDL 都要有 metadata lock plan。

## 下一步路由

Metadata lock deep dive 完成後，schema change 工具讀 [Online Schema Change Tools](../online-schema-change-tools/)；lock 行為讀 [Lock Contention](../lock-contention/)；操作演練讀 [Online Schema Change Lab](../hands-on/online-schema-change-lab/)。
