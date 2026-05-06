---
title: "Trace Context"
date: 2026-04-23
description: "說明跨服務 request 如何用 trace context 串起路徑與耗時"
weight: 35
---


Trace context 的核心概念是「讓同一個 request 在跨服務呼叫中保持同一條追蹤線」。它通常包含 [trace id](/backend/knowledge-cards/trace-id/)、span id、parent [span](/backend/knowledge-cards/span/) 與 baggage，讓 [trace](/backend/knowledge-cards/trace/) 系統能重建呼叫路徑。

## 概念位置

Trace context 是跨服務診斷的關聯層。單一服務 [log](/backend/knowledge-cards/log/) 只呈現局部；trace 可以看到 request 經過 API、worker、[database](/backend/knowledge-cards/database/)、cache 與下游服務的時間分布。

## 可觀察訊號與例子

系統需要 trace context 的訊號是延遲或錯誤跨越多個服務。Checkout 變慢時，trace 可以顯示時間花在庫存服務、付款服務、資料庫查詢或外部 API。

## 設計責任

Trace context 要在 HTTP、[queue](/backend/knowledge-cards/queue/)、worker 與 background job 中傳遞。設計時要控制 [sampling](/backend/knowledge-cards/sampling/)、敏感資料、跨語言 SDK 相容性與 log correlation。
