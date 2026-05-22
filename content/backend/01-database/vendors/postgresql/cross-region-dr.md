---
title: "PostgreSQL Cross-region DR"
date: 2026-05-22
description: "PostgreSQL 跨區災難復原、physical replica、logical replication、backup restore、RPO / RTO 與 failover runbook"
tags: ["backend", "database", "postgresql", "dr", "replication"]
---

PostgreSQL cross-region DR 的核心責任是把區域性事故下的資料恢復、服務切換與資料一致性風險寫成可演練流程。跨區 DR 通常由法規、業務連續性、雲區故障、區域隔離或高可用承諾觸發。

本文的判讀錨點是：cross-region DR 是恢復策略，而非自動等同 multi-region active-active。PostgreSQL 可以透過 backup / WAL archive、physical standby、logical replication、managed service replica 或 application-level replication 支援不同 RPO / RTO；每種路線都有資料延遲、切換與回切成本。

## DR Strategy

DR strategy 的核心責任是把恢復目標和技術路線對齊。

| 策略                 | RPO / RTO 型態                     | 適合情境                          |
| -------------------- | ---------------------------------- | --------------------------------- |
| Backup + WAL archive | RPO 依 WAL archive，RTO 依 restore | 成本敏感、低頻災難復原            |
| Cross-region standby | RPO 接近 replication lag，RTO 較短 | 需要較快啟動 read / promote       |
| Logical replication  | table-level / selective DR         | 跨版本、跨 schema、局部資料同步   |
| Managed global DB    | 雲平台提供跨區 replica             | 希望降低自管複製與 promote 維運   |
| Application replay   | event / queue 重建狀態             | domain event 已是 source of truth |

RPO 要由業務定義。若付款、訂單、庫存只允許秒級遺失，backup-only 路線通常成本不足；若是內部報表或可重建資料，backup + WAL archive 可能足夠。

## Physical vs Logical

Physical vs logical 的核心責任是區分 byte-level recovery 與 row-level replication。Physical replica 保留 PostgreSQL cluster 層級狀態；[logical replication](/backend/knowledge-cards/logical-replication/) 提供 table / publication 層級彈性。

| 面向     | Physical standby          | Logical replication                 |
| -------- | ------------------------- | ----------------------------------- |
| 粒度     | cluster / database        | table / publication                 |
| 版本彈性 | 通常要求版本與系統相容    | 可支援跨版本 / selective migration  |
| DDL      | 跟隨 WAL / 需相容         | 需要 schema coordination            |
| Failover | promote standby           | application / target DB 切換        |
| 風險     | replication lag、timeline | slot lag、schema drift、missing key |

Physical standby 適合整體 DR。它的 runbook 要處理 WAL archive、replication lag、promotion、timeline、DNS / connection string 切換與回切。

Logical replication 適合局部資料或跨版本轉換。它的 runbook 要處理 publication、subscription、replication slot、schema migration ordering 與資料 diff。

## Failover Runbook

Failover runbook 的核心責任是把災難切換變成可演練步驟。最小流程包含 incident declare、source freeze、replica health check、promote、traffic switch、data validation 與 rollback / rebuild。

| Step             | 操作                           | Evidence                   |
| ---------------- | ------------------------------ | -------------------------- |
| Declare incident | 確認 primary region 事故範圍   | incident decision log      |
| Freeze source    | 停止寫入或確認 source 已不可用 | last known LSN / timestamp |
| Check replica    | lag、WAL received、read health | replica status snapshot    |
| Promote          | promote standby 或啟用 target  | new timeline / role        |
| Switch traffic   | DNS、secret、connection string | app smoke test             |
| Validate         | row count、critical invariant  | validation report          |
| Rebuild          | 重建舊 primary 或新 standby    | follow-up runbook          |

Failover 決策要有 owner。自動化可以執行步驟，但是否接受資料遺失、是否凍結寫入、是否 promote，仍需要明確責任人與 tripwire。

## Data Reconciliation

Data reconciliation 的核心責任是處理 cross-region 切換後的資料差異。只要 replication lag 存在，failover 後就可能有未套用交易。

| 差異類型              | 處理方式                                |
| --------------------- | --------------------------------------- |
| 已提交但未複製        | 從 source WAL / app log / event 補償    |
| client retry 重複寫入 | idempotency key / natural key 去重      |
| sequence / identity   | target sequence reset / collision check |
| external side effect  | payment、email、queue 需對帳            |

Reconciliation 要先定義 critical table。所有表都做 full diff 成本高；付款、訂單、權限、ledger、mutation log 等高風險資料要有專用 validation query。

## Drill Design

Drill design 的核心責任是定期驗證 RPO / RTO。DR 文件只有在演練後才可信。

演練至少包含：

1. 從 backup + WAL 還原到指定時間。
2. Promote standby 到 isolated environment。
3. Application 使用 DR endpoint 跑 smoke test。
4. 計算實際 RPO / RTO。
5. 記錄失敗點、人工步驟與下一次修正。

演練應避開 production destructive action。使用 isolated VPC、staging app、read-only validation 與 mock external side effect。

## No-Go Conditions

No-go conditions 的核心責任是指出 PostgreSQL cross-region DR 的邊界。

| 訊號                        | 建議路由                                              |
| --------------------------- | ----------------------------------------------------- |
| 多區同時交易寫入是核心需求  | CockroachDB / Spanner / YugabyteDB 類 distributed SQL |
| RPO 接近零且跨區距離大      | synchronous replication latency 成本評估              |
| Team 缺少 DR 演練能力       | managed service + vendor runbook                      |
| 數據 residency 限制跨區複製 | regional shard / policy-driven replication            |

Cross-region DR 要誠實面對延遲。把每個 region 都變成 writer 需要 distributed transaction 模型；PostgreSQL DR 路線主要提供恢復與切換。

## 下一步路由

Cross-region DR 完成後，恢復實作讀 [PITR / WAL Archiving](../pitr-wal-archiving/)；replication 架構讀 [Replication Topology](../replication-topology/)；跨區 rollout 的資料政策讀 [Multi-region GDPR Rollout](../multi-region-gdpr-rollout/)。
