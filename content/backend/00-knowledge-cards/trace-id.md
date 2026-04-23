---
title: "Trace ID"
date: 2026-04-23
description: "說明分散式追蹤中同一條呼叫路徑的識別碼"
weight: 106
---

Trace ID 的核心概念是「分散式追蹤中同一條呼叫路徑的識別碼」。一個 trace 由多個 span 組成，trace ID 讓 tracing 系統把它們聚合成同一次操作。

## 概念位置

Trace ID 是 tracing 的頂層關聯欄位。它適合追蹤一次 request 經過多個服務、queue、database 與外部 API 的時間分布。

## 可觀察訊號與例子

系統需要 trace ID 的訊號是延遲或錯誤跨越多個服務。Checkout 變慢時，trace ID 可以串起 cart、inventory、payment、database query 與第三方 API。

## 設計責任

Trace ID 要透過標準 trace context 傳遞，並和 log correlation 對齊。採樣策略要確保錯誤與高延遲 trace 有足夠保留率。
