---
title: "Database Sharding"
date: 2026-05-20
description: "說明資料庫如何依 shard key 分散資料、路由請求與承擔跨 shard 查詢成本"
weight: 244
---

Database sharding 的核心概念是把同一個 logical database 或 table 依 shard key 分散到多個獨立 storage 節點，讓寫入、儲存與故障範圍水平分散。它和 [Partition](/backend/knowledge-cards/partition/) 相鄰，但資料庫 sharding 的主要責任是 data placement、request routing、cross-shard query 與 resharding；容量失衡時要接回 [Hot Partition](/backend/knowledge-cards/hot-partition/)，一致性需求升高時要對照 [Distributed SQL](/backend/knowledge-cards/distributed-sql/)。

## 跟其他概念的關係

Database sharding 位在單一 primary database 與 distributed SQL 之間。MySQL + Vitess、PostgreSQL + Citus、MongoDB sharded cluster 或 application-layer sharding 都會把 shard key 變成資料路由契約；[Distributed SQL](/backend/knowledge-cards/distributed-sql/) 則把更多 routing、一致性與 failover 責任放回 database layer。

## 可觀察訊號與例子

需要 database sharding 的訊號是單一 primary 的 write throughput、storage、maintenance window 或 tenant isolation 已成瓶頸，且 workload 可以用 tenant_id、user_id、region 或 business key 切成相對獨立的資料集合。MySQL 進入 Vitess / PlanetScale 討論時，核心問題通常是 shard key、VSchema、resharding workflow 與跨 shard transaction；PostgreSQL 進入 Citus 討論時，核心問題通常是 tenant co-location、distributed table 與 coordinator / worker topology。

Hot shard 的訊號是整體資源還有餘裕，但少數 shard 的 write、lock、CPU 或 storage 先到上限。這時要同時看 [Hot Partition](/backend/knowledge-cards/hot-partition/)、[Saturation Point](/backend/knowledge-cards/saturation-point/) 與 [Replication Lag](/backend/knowledge-cards/replication-lag/)，避免只增加節點數卻沒有修正 key distribution。

## 判斷條件與後果

Shard key 一旦上線就是長期的資料路由契約，改動它常牽涉 backfill、dual-write、shadow read、cutover window 與 data reconciliation，所以 sharding 的各項政策在切分之前定義，代價遠低於切分之後補。沒有指定 routing owner 時，路由邏輯散在各個 application 裡，resharding 要同步改每一處。沒有估過 single-shard query 的比例、也沒有 cross-shard query 與 cross-shard transaction 的政策時，跨 shard 的查詢與交易到上線後才出現，延遲與失敗模式都跟單一 shard 不同。沒有 resharding path 時，hot shard 出現只能加節點，而 key distribution 沒變，熱點仍在同一個 shard。backup／restore 的單位與 incident owner 沒有對應到 shard 時，單一 shard 出事時要還原多大範圍、由誰負責，都要在事故中決定。改 shard key 的流程見 [Online Migration](/backend/knowledge-cards/online-migration/)、[Cutover Window](/backend/knowledge-cards/cutover-window/) 與 [Data Reconciliation](/backend/knowledge-cards/data-reconciliation/)。
