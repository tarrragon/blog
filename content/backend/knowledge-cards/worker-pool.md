---
title: "Worker Pool"
date: 2026-04-23
description: "說明一組 worker 如何限制同時處理量並保護下游資源"
weight: 126
---

Worker pool 的核心概念是「用固定或可控數量的 worker 處理工作」。它讓系統限制同時執行量，避免每個 request 或 message 都直接建立無界工作。

## 概念位置

Worker pool 是 application 內部的容量控制工具。它常和 [in-process channel](../in-process-channel/)、[queue depth](../queue-depth/)、[backpressure](../backpressure/)、[bulkhead](../bulkhead/)、[dependency isolation](../dependency-isolation/) 與 [graceful shutdown](../graceful-shutdown/) 一起使用。

## 可觀察訊號與例子

系統需要 worker pool 的訊號是工作可以排隊，但同時執行量需要受控。圖片縮圖、匯出報表、外部 API 同步與 webhook retry 都可以用 worker pool 限制 CPU、連線或下游 API 壓力。

## 設計責任

Worker pool 要定義 worker 數量、queue 長度、等待期限、錯誤回報、shutdown、重試與觀測欄位。擴大 worker 數前要先確認瓶頸位置：可能在 [connection pool](../connection-pool/)、[HTTP client](../http-client/) pool 或外部 API quota。
