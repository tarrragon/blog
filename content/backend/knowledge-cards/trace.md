---
title: "Trace"
date: 2026-06-22
description: "說明 trace 如何重建跨服務請求的路徑、耗時與依賴關係"
weight: 140
tags: ["backend", "observability"]
---

Trace 的核心概念是「把一次 request 或工作流程拆成可關聯的多段執行紀錄」。[Trace context](/backend/knowledge-cards/trace-context/) 串起整條路徑，[span](/backend/knowledge-cards/span/) 記錄每一段工作，[trace id](/backend/knowledge-cards/trace-id/) 讓 [log](/backend/knowledge-cards/log/) 與 [dashboard](/backend/knowledge-cards/dashboard/) 能回到同一條流程。

## 概念位置

Trace 是跨服務診斷的路徑層，跟 [log](/backend/knowledge-cards/log/)（事件層）和 [metrics](/backend/knowledge-cards/metrics/)（趨勢層）互補。Log 回答「某個服務發生了什麼」；metrics 回答「服務的健康趨勢」；trace 回答「一次 request 跨服務時，時間花在哪、錯誤發生在哪一段」。

Trace 在 waterfall view 中呈現為時間軸上的巢狀條狀圖，root span 在最上面、child span 依序往下。診斷價值是一眼看出延遲瓶頸 — checkout 總延遲 800ms 中 payment span 佔 600ms，問題定位立刻縮小範圍。

## 使用情境

系統需要 trace 的訊號是單一服務的 log 只呈現局部。Checkout 變慢時，trace 可以顯示時間主要花在庫存查詢、付款 API、database lock 或通知 worker。跨服務錯誤（upstream 回 500 但不知道是哪個 downstream 引起的）也依賴 trace 定位。

Trace 聚合後可以自動生成 [service topology](/backend/04-observability/service-topology/) — 哪些服務在呼叫哪些服務、call 頻率、延遲分布、錯誤率。這個 graph 反映實際流量而非設計文件。

## 設計責任

Trace 設計要處理 [trace context](/backend/knowledge-cards/trace-context/) 傳遞（HTTP header、queue message header、thread context）、[sampling](/backend/knowledge-cards/sampling/) 策略（head / tail / adaptive）、span 命名慣例、敏感資料 redaction、跨語言 SDK 相容性與 log correlation（trace id 寫進 log 欄位）。

高流量服務需要控制採樣成本，同時保留錯誤與高延遲樣本。Sampling 策略的完整討論見 [4.7](/backend/04-observability/cardinality-cost-governance/#sampling-策略)。Context propagation 在不同邊界（HTTP / queue / thread pool / background job）的斷鏈風險與修復見 [4.3](/backend/04-observability/tracing-context/)。
