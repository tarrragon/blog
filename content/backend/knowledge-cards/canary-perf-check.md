---
title: "Canary Perf Check"
date: 2026-05-12
description: "canary release 中針對 latency / throughput 而非 error rate 的退化檢查"
weight: 235
---

Canary perf check 的核心概念是「canary 階段不只看 error rate、也看 latency / throughput / resource utilization 退化」。傳統 canary 看 error rate、但 perf 退化通常先於 error 出現、是更早的警訊。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 概念位置

Canary 流量導 1% / 5% / 10% 到新版本、跟 control（舊版本）流量比較 p50 / p95 / p99 / p999 latency 分布、throughput rate、resource saturation。自動 rollback 條件：canary p99 比 control 退化 > X%。漸進放大：通過 1% → 5% → 25% → 50% → 100%。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 可觀察訊號與例子

需要 canary perf check 的訊號是「release 後 latency 飆但 error 沒事、用戶體驗悄悄變差」。對應案例：[Prime Day pre-event 驗證](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [FanDuel canary across 20 州](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)。

## 設計責任

Canary perf check 的關鍵是 *跟 control 比、不是跟 baseline 比*。同樣流量同樣時段、不同版本的差才有意義。abort condition 要事前訂、不要事中決定。Canary 流量比例要看 *退化 blast radius* — 1% 流量退化 30%、影響 0.3% 用戶；50% 流量退化 30%、影響 15% 用戶。
