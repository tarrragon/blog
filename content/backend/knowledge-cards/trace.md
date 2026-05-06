---
title: "Trace"
date: 2026-04-23
description: "說明 trace 如何重建跨服務請求的路徑、耗時與依賴關係"
weight: 140
---


Trace 的核心概念是「把一次 request 或工作流程拆成可關聯的多段執行紀錄」。[Trace context](/backend/knowledge-cards/trace-context/) 串起整條路徑，[span](/backend/knowledge-cards/span/) 記錄每一段工作，[trace id](/backend/knowledge-cards/trace-id/) 讓 [log](/backend/knowledge-cards/log/) 與 [dashboard](/backend/knowledge-cards/dashboard/) 能回到同一條流程。

## 概念位置

Trace 是跨服務診斷的路徑層。它幫團隊看見 API、worker、[database](/backend/knowledge-cards/database/)、cache、[broker](/backend/knowledge-cards/broker/) 與外部服務之間的耗時分布，特別適合排查長尾延遲與跨服務錯誤。

## 可觀察訊號與例子

系統需要 trace 的訊號是單一服務 log 只呈現局部。Checkout 變慢時，trace 可以顯示時間主要花在庫存查詢、付款 API、database lock 或通知 worker。

## 設計責任

Trace 設計要處理 trace context 傳遞、[sampling](/backend/knowledge-cards/sampling/)、span 命名、敏感資料、跨語言 SDK 與 log correlation。高流量服務需要控制採樣成本，同時保留錯誤與高延遲樣本。
