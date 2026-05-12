---
title: "Universal Scalability Law (USL)"
date: 2026-05-12
description: "說明系統擴容到一定規模後吞吐反而下降的數學模型"
weight: 221
---

Universal Scalability Law 的核心概念是「擴容到某個臨界點之後、加機器反而讓吞吐下降」。Neil Gunther 的公式 throughput(N) = N / (1 + α(N-1) + βN(N-1))，其中 α = serialization（Amdahl 部分）、β = crosstalk（跨節點協調成本）。可先對照 [Little's Law](/backend/knowledge-cards/little-law/)。

## 概念位置

USL 解釋「加機器為什麼會失效」。線性擴容是理想、但實際系統有兩個拖累：α 是必須序列化的部分（如 lock、coordinator）、β 是節點間互相通訊的成本（如 cache invalidation、consensus quorum）。β 通常比 α 更危險、會讓 throughput 在 N 大到某點後反而下降。可先對照 [Little's Law](/backend/knowledge-cards/little-law/)。

## 可觀察訊號與例子

需要思考 USL 的訊號是「擴容到 N 個 instance 後、QPS 不再線性成長」。常見原因：共用 cache 變熱點、distributed lock 競爭、跨 region replication 變慢。對照案例：[Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) 用 TrueTime 降低 β 達成線性擴展；[Coinbase RAFT](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 因 consensus 限制了水平擴容。

## 設計責任

設計分散式系統時、要主動識別 α 跟 β 來源、想辦法降低。常見手段：partition 切分（降 β）、sharding（降 α 的範圍）、避免 distributed lock（降 β）、async vs sync（降 α 的關鍵路徑）。USL 是 *選型決策* 的工具、不是 production runtime 的訊號。
