---
title: "Trace Context"
date: 2026-06-22
description: "說明跨服務 request 如何用 trace context 串起路徑與耗時"
weight: 35
tags: ["backend", "observability"]
---

Trace context 的核心概念是「讓同一個 request 在跨服務呼叫中保持同一條追蹤線」。它包含 [trace id](/backend/knowledge-cards/trace-id/)（標識整條 trace）、span id（標識上游 span）與 trace flags（sampling 決策），讓下游服務建立的 [span](/backend/knowledge-cards/span/) 能歸屬同一條 [trace](/backend/knowledge-cards/trace/)。

## 概念位置

Trace context 是跨服務診斷的關聯層。它的傳遞機制決定 trace 能不能完整串起 — context 斷掉的地方，trace 就從「完整路徑」退化成需要人工拼接的局部紀錄。

W3C Trace Context 標準定義了 HTTP 的傳遞格式：`traceparent` header 帶 version + trace id + parent span id + trace flags，`tracestate` header 帶 vendor-specific 附加資訊。OpenTelemetry SDK 預設使用 W3C 格式。部分 vendor 有自己的 header（Datadog 用 `x-datadog-trace-id`、AWS X-Ray 用 `X-Amzn-Trace-Id`），跨 vendor 時需要在 collector 層轉換。

## 使用情境

系統需要 trace context 的訊號是延遲或錯誤跨越多個服務。Checkout 變慢時，trace context 讓 tracing 系統把 API gateway、order service、payment service、database query 的 span 串成一條路徑，在 waterfall view 中直接看到時間花在哪。

Context 在 HTTP call、gRPC metadata、[queue](/backend/knowledge-cards/queue/) message header 上傳遞。Queue 邊界的 propagation 比 HTTP 複雜 — consumer 可能在 producer 之後很久才消費，context 的時間跨度從毫秒擴大到分鐘。

## 設計責任

Trace context 設計要處理四個邊界的傳遞：HTTP / gRPC（SDK auto-instrumentation 自動處理）、queue（需要 instrumented client 注入 message header）、thread pool（需要語言級的 context 傳播機制）、background job（需要在 job 啟動時建立 root span）。

斷鏈的常見原因和修復策略見 [4.3 tracing 與 context link](/backend/04-observability/tracing-context/)。Sampling 決策跟 trace context 的關係見 [4.7 sampling 策略](/backend/04-observability/cardinality-cost-governance/#sampling-策略)。
