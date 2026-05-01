---
title: "AWS Aurora"
date: 2026-05-01
description: "AWS managed PostgreSQL / MySQL、storage layer 重寫"
weight: 7
---

Aurora 是 AWS managed PostgreSQL / MySQL、保留 protocol 相容、storage layer 重寫成跨 AZ 分散式。適合既有 PostgreSQL / MySQL 應用想換 managed 與更好 scaling、不想離開 SQL 模型。

## 適用場景

- 既有 PostgreSQL / MySQL 應用、想要 managed
- 需要 fast storage scaling（TB 級）
- 多 read replica（最多 15 個 reader）
- AWS 生態深度整合

## 不適用場景

- 跨雲需求
- 需要 PostgreSQL / MySQL 最新版的進階特性（Aurora 落後 upstream）
- 極端寫入吞吐（受 storage 設計限制）

## 跟其他 vendor 的取捨

- vs `postgresql` / `mysql`（自管）：Aurora 託管成本 vs 自管彈性
- vs `cockroachdb`：Aurora 是 single-region scaling；CockroachDB 是 multi-region
- vs Aurora Serverless v2：on-demand 變體、scale-to-zero

## 預計實作話題

- Aurora storage architecture
- Cross-AZ failover
- Read replica scaling
- Aurora Global Database（跨區）
- Aurora Serverless v2 適用判斷
