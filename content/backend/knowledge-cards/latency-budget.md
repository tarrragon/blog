---
title: "Latency Budget"
date: 2026-05-12
description: "把 user-perceived latency 拆到每個 stage 的配額、反推架構選擇"
weight: 240
---

Latency budget 的核心概念是「給定 SLO end-to-end latency 上限、拆到每個 stage（網路 / CDN / app / cache / DB / 第三方）的配額、總和不得超過 SLO」。讓 latency 從口號變成可分解的工程目標。可先對照 [Performance Budget](/backend/knowledge-cards/performance-budget/)。

## 概念位置

Latency budget 是 [Little's Law](/backend/knowledge-cards/little-law/) 的應用 — 給定吞吐目標 + latency 目標、反推每個 stage 的可承受 latency。常見分解：DNS 5ms + TLS 50ms + CDN 20ms + app 100ms + DB 30ms + serialization 10ms = 215ms。任何 stage 超 budget → 該 stage 必須改善。可先對照 [Performance Budget](/backend/knowledge-cards/performance-budget/)。

## 可觀察訊號與例子

需要 latency budget 的訊號是「p99 latency 飆但不知道誰拖累」。對應案例：[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — 從 sub-ms 反推、每個 stage 都被擠到極限（Cluster Placement Group、z1d 等）；[Tubi ML p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — feature lookup 10ms 內、model inference 才有預算。

## 設計責任

Latency budget 必須 *跟 SLO 對齊*、不是工程師憑感覺訂。每個 stage 的 budget 必須有 *current measurement* — 不能訂了沒量。Cross-region call 自帶數十 ms 不可壓縮 latency、設計時要明確認知。任何新增 stage（middleware / sidecar / interceptor）都會吃 budget、必須評估。
