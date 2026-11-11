---
title: "Tail Latency"
date: 2026-05-12
description: "說明 p99 / p999 等長尾延遲為何比平均延遲更能反映 saturation"
weight: 227
---

Tail latency 的核心概念是「p99 / p999 等高 percentile 的 latency 通常比 average 高一個量級、且 *是* 用戶體感的決定因素」。average 看不到的 saturation、p99 早就看到了。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 跟其他概念的關係

Tail latency 通常由以下因素貢獻：GC pause、connection pool 競爭、cache miss、cross-zone network、retry storm。average / p50 平滑掉這些 outlier、看不到 capacity 警訊；p99 / p999 直接反映「最不順的 1% / 0.1% 用戶看到什麼」。可先對照 [Saturation Point](/backend/knowledge-cards/saturation-point/)。

## 可觀察訊號與例子

tail latency 飆升的訊號是「average 還行、用戶卻在抱怨慢」。對應案例：[Tubi p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML inference 在 p99 才能控制體驗、p50 控制無意義；[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — RAFT 系統 p999 通常比 p99 高一個量級。

## 判斷條件與後果

SLO 訂在哪一個 percentile，決定了最慢的多少比例請求不受承諾保護：訂在 p99 時，最慢的 1% 不受承諾保護，所以對外 SLO 通常訂在 p99；內部服務被上游多次呼叫，一個上游請求的延遲取決於它呼叫的那幾次裡最慢的一次，所以內部可以訂到 p99.9。Percentile 從 histogram 算時，多個 instance 的 bucket 可以相加後再算出整體的 p99；每個 instance 自己算好 p99 再回報成 gauge 時，多台的 p99 無法合成整體的 p99，平均之後的值低估了尾端。Java GC pause、Go GC 與 Node event loop lag 只讓停頓期間的那幾個請求變慢，average 與 p50 幾乎不動，異常只出現在 p999，所以這幾種停頓單獨監控，才對得上 p999 的異常。tail latency 的改善方向對應它的成因：cross-zone hop 增加每個請求的網路延遲與變異，connection pool 沒有預熱時第一批請求要先等連線建立，stop-the-world 讓停頓期間的請求全部延後。
