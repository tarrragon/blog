---
title: "Tail Latency"
date: 2026-05-12
description: "說明 p99 / p999 等長尾延遲為何比平均延遲更能反映 saturation"
weight: 226
---

Tail latency 的核心概念是「p99 / p999 等高 percentile 的 latency 通常比 average 高一個量級、且 *是* 用戶體感的決定因素」。average 看不到的 saturation、p99 早就看到了。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 概念位置

Tail latency 通常由以下因素貢獻：GC pause、connection pool 競爭、cache miss、cross-zone network、retry storm。average / p50 平滑掉這些 outlier、看不到 capacity 警訊；p99 / p999 直接反映「最不順的 1% / 0.1% 用戶看到什麼」。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

tail latency 飆升的訊號是「average 還行、用戶卻在抱怨慢」。對應案例：[Tubi p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML inference 在 p99 才能控制體驗、p50 控制無意義；[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — RAFT 系統 p999 通常比 p99 高一個量級。

## 設計責任

SLO 通常訂在 p99、internal 可訂 p99.9。metrics 必須記 histogram、不是單一 percentile gauge。Java GC pause、Go GC、Node event loop lag 都可能造成 p999 異常、要單獨監控。tail latency 改善通常靠：減少 cross-zone hop、connection pool 預熱、避免 stop-the-world。
