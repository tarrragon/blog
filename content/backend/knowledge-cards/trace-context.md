---
title: "Trace Context"
date: 2026-06-22
description: "說明跨服務 request 如何用 trace context 串起路徑與耗時"
weight: 36
tags: ["backend", "observability"]
---

Trace context 的核心概念是「讓同一個 request 在跨服務呼叫中保持同一條追蹤線」。它包含 [trace id](/backend/knowledge-cards/trace-id/)（標識整條 trace）、span id（標識上游 span）與 trace flags（sampling 決策），讓下游服務建立的 [span](/backend/knowledge-cards/span/) 能歸屬同一條 [trace](/backend/knowledge-cards/trace/)。

## 跟其他概念的關係

Trace context 是跨服務診斷的關聯層，跟 [correlation id](/backend/knowledge-cards/correlation-id/) 互補 — correlation id 關聯業務流程、trace context 關聯技術呼叫路徑。它的傳遞機制決定 [trace](/backend/knowledge-cards/trace/) 能不能完整串起 — context 斷掉的地方，trace 就從「完整路徑」退化成需要人工拼接的局部紀錄。

W3C Trace Context 標準定義了 HTTP 的傳遞格式：`traceparent` header 帶 version + trace id + parent span id + trace flags，`tracestate` header 帶 vendor-specific 附加資訊。OpenTelemetry SDK 預設使用 W3C 格式。部分 vendor 有自己的 header（Datadog 用 `x-datadog-trace-id`、AWS X-Ray 用 `X-Amzn-Trace-Id`），跨 vendor 時需要在 collector 層轉換。

## 使用情境

系統需要 trace context 的訊號是延遲或錯誤跨越多個服務。Checkout 變慢時，trace context 讓 tracing 系統把 API gateway、order service、payment service、database query 的 span 串成一條路徑，在 waterfall view 中直接看到時間花在哪。

Context 在 HTTP call、gRPC metadata、[queue](/backend/knowledge-cards/queue/) message header 上傳遞。Queue 邊界的 propagation 比 HTTP 複雜 — consumer 可能在 producer 之後很久才消費，context 的時間跨度從毫秒擴大到分鐘。

## 判斷條件與後果

Trace context 在 HTTP / gRPC、queue、thread pool 與 background job 這幾種邊界上傳遞的方式不同，哪一種沒有接上，trace 就在那裡斷成兩段。HTTP / gRPC 由 SDK auto-instrumentation 自動注入與讀取 header。Queue 的 message header 由 instrumented client 注入，client 沒有 instrumentation 時，consumer 讀不到 context，它建立的 span 開始一條新的 trace。Thread pool 把工作交給另一個執行緒時，語言級的 context 傳播機制沒有接上，工作執行緒上的 span 找不到 parent。Background job 不是由請求觸發，job 啟動時沒有建立 root span 時，它做的工作不屬於任何 trace。

斷鏈的常見原因和修復策略見 [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)。Sampling 決策跟 trace context 的關係見 [4.7 sampling 策略](/backend/04-observability/cardinality-cost-governance/#sampling-策略)。
