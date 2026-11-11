---
title: "Latency Budget"
date: 2026-05-12
description: "把 user-perceived latency 拆到每個 stage 的配額、反推架構選擇"
weight: 241
---

Latency budget 的核心概念是「給定 SLO end-to-end latency 上限、拆到每個 stage（網路 / CDN / app / cache / DB / 第三方）的配額、總和不得超過 SLO」。讓 latency 從口號變成可分解的工程目標。可先對照 [Performance Budget](/backend/knowledge-cards/performance-budget/)。

## 跟其他概念的關係

Latency budget 是 [Little's Law](/backend/knowledge-cards/little-law/) 的應用 — 給定吞吐目標 + latency 目標、反推每個 stage 的可承受 latency。常見分解：DNS 5ms + TLS 50ms + CDN 20ms + app 100ms + DB 30ms + serialization 10ms = 215ms。任何 stage 超 budget → 該 stage 必須改善。可先對照 [Performance Budget](/backend/knowledge-cards/performance-budget/)。

## 可觀察訊號與例子

需要 latency budget 的訊號是「p99 latency 飆但不知道誰拖累」。對應案例：[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — 從 sub-ms 反推、每個 stage 都被擠到極限（Cluster Placement Group、z1d 等）；[Tubi ML p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — feature lookup 10ms 內、model inference 才有預算。

## 判斷條件與後果

各 stage 的 budget 憑感覺訂、沒有從 SLO 的 end-to-end 上限分下來時，總和可能超過 SLO，每個 stage 都在自己的 budget 內，使用者看到的延遲仍然違反 SLO。某個 stage 的 budget 沒有對應的 current measurement 時，超支的 stage 認不出來，p99 上升時不知道是哪一段用掉了預算。Cross-region call 帶著數十 ms 優化不掉的網路延遲，這段延遲沒有預先算進 budget 時，路徑上其他 stage 的配額實際上已經被它用掉。新增任何 stage（middleware、sidecar、interceptor）都佔用一段延遲，加進去之前沒有從 budget 裡分配時，原本合乎預算的路徑就超支了。
