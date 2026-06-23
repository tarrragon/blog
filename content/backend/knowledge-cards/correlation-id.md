---
title: "Correlation ID"
date: 2026-06-22
description: "說明跨事件或跨服務的關聯識別碼如何支援排障"
weight: 104
tags: ["backend", "observability"]
---

Correlation ID 的核心概念是「把同一個業務流程中的多筆紀錄關聯起來的識別碼」。它是 [log schema](/backend/knowledge-cards/log-schema/) 的核心欄位，可以跨 request、queue message、background job、log、trace 與外部 API 呼叫。

## 概念位置

Correlation ID 跟 [trace id](/backend/knowledge-cards/trace-id/) 的定位不同。Trace id 偏向一次技術呼叫路徑（一個 HTTP request 經過多個服務）；correlation ID 可以代表更長的業務流程（一筆訂單從建立到付款到出貨，跨越多個獨立 request）。

Correlation ID 是 [log schema](/backend/knowledge-cards/log-schema/) 的核心欄位。Log 帶 correlation ID 時，跨服務跟跨 async 邊界的事件可以用同一個 ID 查出完整業務流程。見 [4.1 log schema](/backend/04-observability/log-schema/)。

## 使用情境

系統需要 correlation ID 的訊號是事故排查需要跨同步與非同步邊界。訂單建立 request、付款事件、寄信 job 與出貨事件共享同一 correlation ID，讓客服跟工程師追到完整流程。

## 設計責任

Correlation ID 要在入口（API gateway 或 first service）建立或從 upstream 接收，並傳遞到 log、message header、trace context 與外部呼叫。欄位名稱要穩定（跨服務一致，避免 `request_id` vs `req_id` vs `requestId` 的漂移），避免把敏感資料當成 ID。
