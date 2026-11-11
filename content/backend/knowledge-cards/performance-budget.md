---
title: "Performance Budget"
date: 2026-05-12
description: "跟 error budget 同類概念、但用於 latency / throughput 退化的可控額度"
weight: 240
---

Performance budget 的核心概念是「每月有允許退化的額度、用完就 freeze new feature、focus on perf」。跟 [error budget](/backend/knowledge-cards/error-budget/) 並列、用同一套方法論處理可靠性 vs 效能。可先對照 [Error Budget](/backend/knowledge-cards/error-budget/)。

## 跟其他概念的關係

Performance budget 訂在 SLO baseline 之上、允許「p99 比 baseline 高 X ms 連續 Y 分鐘」這類退化額度。額度用完 → release freeze → 修完 perf 再放行。跟 error budget 互補：error budget 控制可靠性退化、performance budget 控制效能退化。可先對照 [Latency Budget](/backend/knowledge-cards/latency-budget/)。

## 可觀察訊號與例子

需要 performance budget 的訊號是「容量規劃太死板、新功能 release 太慢」或反之「release 太快、累積 perf 退化沒人管」。對應案例：[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 延遲就是收入、無 performance budget 等於無 release control；[FanDuel 多 SLO](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 直播 vs 投注不同 budget。

## 判斷條件與後果

Performance budget 的鬆緊決定 release 的節奏。額度訂得太緊時，正常的功能迭代也會用完額度，release freeze 頻繁觸發，新功能排不上 release；訂得太鬆時，效能退化逐次累積，沒有任何一次觸發 freeze。起點取 baseline 加 10% headroom，之後依 burn rate 調整。額度是一段時間內允許的退化量，所以告警看的是消耗速度：固定門檻的 alert 在短暫越線時就響、在長期低於門檻的緩慢退化時不響，用 burn rate alert（跟 [error budget](/backend/knowledge-cards/error-budget/) 同一套做法）才對得上額度的定義。跟 [latency budget](/backend/knowledge-cards/latency-budget/) 不同層：latency budget 是「每個 stage 多少 latency 配額」、performance budget 是「整體允許退化多少」。
