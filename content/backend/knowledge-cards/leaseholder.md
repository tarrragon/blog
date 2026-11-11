---
title: "Leaseholder"
date: 2026-05-27
description: "分散式 SQL 每個 range 在任一時間點的 read / write entry point、通常等於 Raft leader、承擔該 range 的 coordination"
weight: 362
---

Leaseholder 的核心概念是「distributed SQL 把 key space 切成多個 range、每個 range 在任一時間點有唯一一個 leaseholder 節點、承擔該 range 所有 read / write 的 coordination」。它的責任是把「誰來決定這個 range 的順序」這件事從 cluster-level 推到 per-range level、讓寫入吞吐可以線性分散。可先對照 [Consensus Protocol](/backend/knowledge-cards/consensus-protocol/)。

## 跟其他概念的關係

Leaseholder 出現在 CockroachDB / Spanner 等 distributed SQL 架構、跟 [Consensus Protocol](/backend/knowledge-cards/consensus-protocol/) 是抽象與落地的對應 — Raft / Paxos 是通用 consensus 機制、leaseholder 是 distributed SQL 把它落地成 per-range 的 entry point。跟 [Hot Partition](/backend/knowledge-cards/hot-partition/) 對照：KV 系統的 hot partition 是物理 partition 流量集中、distributed SQL 是 leaseholder 集中在某節點、機制不同但容量影響類似。跟 [Single Writer Model](/backend/knowledge-cards/single-writer-model/) 區分：後者是 cluster-level 只有單一 primary 寫入、leaseholder 是 range-level 的 single writer、cluster 內每個 range 可以分散到不同節點。

## 可觀察訊號與例子

需要 leaseholder 判讀的訊號是「整體 cluster CPU 不高、但某節點 p99 latency 飆 + 寫入 throughput 卡住」。[DoorDash CockroachDB](/backend/09-performance-capacity/cases/doordash-cockroachdb-orders-platform/) 揭露 Aurora Postgres 撞牆後遷到 CockroachDB、寫入分散到 leaseholder 跟 Raft replica；[Netflix CockroachDB](/backend/09-performance-capacity/cases/netflix-cockroachdb-multi-region-fleet/) 揭露 380+ cluster / 最大單區 60 nodes 規模、leaseholder placement 跟 locality config 直接決定 cross-region latency。

## 判斷條件與後果

Leaseholder 集中在少數節點時，整體 cluster CPU 不高，那幾個節點卻出現 p99 latency 上升與寫入 throughput 停滯，原因是每個 range 的 read 與 write coordination 都經過它的 leaseholder；cluster 總 CPU 看不出這種集中，所以 capacity planning 看的是每個節點承擔多少 leaseholder。lease transfer（rebalance、節點 drain、failover）期間，被轉移的 range 出現短期的 p99 spike；這段 spike 沒有寫進變更窗口與 rollback 觀測點時，執行變更的人分不出它是 lease transfer 的正常代價，還是變更本身出了錯。region survival 配置下 voting replica 跨 region，write latency 固定被拉高；leaseholder 的 placement 跟 locality tag 一致時讀取在本地完成，不一致時每次讀取多一趟跨 region 的 RTT。
