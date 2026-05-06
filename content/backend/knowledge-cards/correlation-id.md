---
title: "Correlation ID"
date: 2026-04-23
description: "說明跨事件或跨服務的關聯識別碼如何支援排障"
weight: 104
---


Correlation ID 的核心概念是「把同一個業務流程中的多筆紀錄關聯起來的識別碼」。它可以跨 request、queue message、background job、log、trace 與外部 API 呼叫。 可先對照 [Credential](/backend/knowledge-cards/credential/)。

## 概念位置

Correlation ID 是診斷關聯層。Trace ID 偏向一次技術呼叫路徑；correlation ID 可以代表更長的業務流程，例如一筆訂單或一次付款嘗試。 可先對照 [Credential](/backend/knowledge-cards/credential/)。

## 可觀察訊號與例子

系統需要 correlation ID 的訊號是事故排查需要跨同步與非同步邊界。訂單建立 request、付款事件、寄信 job 與出貨事件可以共享同一 correlation ID，讓客服與工程師追到完整流程。

## 設計責任

Correlation ID 要在入口建立或接收，並傳遞到 log、message、trace 與外部呼叫。欄位名稱要穩定，並避免把敏感資料當成 ID。
