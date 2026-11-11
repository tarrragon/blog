---
title: "Canary Perf Check"
date: 2026-05-12
description: "canary release 中針對 latency / throughput 而非 error rate 的退化檢查"
weight: 236
---

Canary perf check 的核心概念是「canary 階段不只看 error rate、也看 latency / throughput / resource utilization 退化」。傳統 canary 看 error rate、但 perf 退化通常先於 error 出現、是更早的警訊。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 跟其他概念的關係

Canary 流量導 1% / 5% / 10% 到新版本、跟 control（舊版本）流量比較 p50 / p95 / p99 / p999 latency 分布、throughput rate、resource saturation。自動 rollback 條件：canary p99 比 control 退化 > X%。漸進放大：通過 1% → 5% → 25% → 50% → 100%。可先對照 [Profile Diff](/backend/knowledge-cards/profile-diff/)。

## 可觀察訊號與例子

需要 canary perf check 的訊號是「release 後 latency 飆但 error 沒事、用戶體驗悄悄變差」。對應案例：[Prime Day pre-event 驗證](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) / [FanDuel canary across 20 州](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/)。

## 判斷條件與後果

Canary 的效能數字拿去跟 baseline（上週或上一次上線時的數字）比時，兩邊的流量組成與時段不同，差距可能來自流量而不是版本；跟同時段、同流量的 control 比時，兩邊只差在版本，差距才歸因得到新版本。abort condition 在 canary 開始之後才訂時，門檻是看過這一版的數字才決定的，放行標準在每一次上線之間都不一致，所以 abort condition 在 canary 開始前寫定。Canary 的流量比例決定退化的 blast radius：1% 流量退化 30%，影響 0.3% 用戶；50% 流量退化 30%，影響 15% 用戶。
