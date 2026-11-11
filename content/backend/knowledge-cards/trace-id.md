---
title: "Trace ID"
date: 2026-06-22
description: "說明分散式追蹤中同一條呼叫路徑的識別碼"
weight: 107
tags: ["backend", "observability"]
---

Trace ID 的核心概念是「分散式追蹤中同一條呼叫路徑的全域識別碼」。一個 [trace](/backend/knowledge-cards/trace/) 由多個 [span](/backend/knowledge-cards/span/) 組成，trace ID 讓 tracing 系統把散落在不同服務的 span 聚合成同一次操作的完整路徑。

## 跟其他概念的關係

Trace ID 是 tracing 的頂層關聯欄位。W3C Trace Context 標準使用 128-bit 隨機值（32 hex chars）；部分 vendor 使用 64-bit（Datadog 舊版、Zipkin v1）。混用不同長度時需要在 collector 層做 ID 轉換或 padding。

Trace ID 跟 [request id](/backend/knowledge-cards/request-id/) 的定位不同：request id 是單一服務內的請求識別碼（通常由 API gateway 或 load balancer 產生），trace id 是跨服務的追蹤識別碼（由第一個 instrumented service 產生）。兩者可以共存在同一筆 log 的不同欄位，各自服務不同的查詢需求。

## 使用情境

Trace ID 的診斷價值是「拿到一個 ID 就能看到整條 request 路徑」。事故中從 error log 拿到 trace ID，貼進 tracing UI（Jaeger、Grafana Tempo、Datadog APM），直接看 waterfall view 定位瓶頸。

Trace ID 也是 log / metric / trace 三者的關聯樞紐。Log 的結構化欄位帶 trace ID 時，debug 工作流可以從 log → trace 或 trace → log 雙向跳轉。Metric 的 exemplar 帶 trace ID 時，可以從 dashboard 的 latency spike 跳到具體的高延遲 trace。

## 判斷條件與後果

Trace ID 在 HTTP header、queue message header 與 thread context 每一處都經由 [trace context](/backend/knowledge-cards/trace-context/) 傳下去時，散落在各服務的 span 才聚合得成同一條路徑；任一處沒傳，那一處之後的 span 拿到新的 trace ID。Structured log 沒有 trace ID 欄位時，從 error log 跳到 trace、或從 trace 回到 log 的查詢都做不到（欄位定義見 [4.1 log schema](/backend/04-observability/log-schema/)）。Sampling 只依固定比例丟棄 trace 時，錯誤與高延遲的 trace 也按同樣比例被丟掉，事故時 log 裡有 trace ID，tracing 系統裡卻查不到對應的 trace；所以 sampling 策略給錯誤與高延遲 trace 較高的保留率。
