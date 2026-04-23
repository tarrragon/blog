---
title: "Observability Middleware"
date: 2026-04-23
description: "說明請求進入 handler 前後如何補上觀測欄位"
weight: 0
---

Observability Middleware 的核心概念是「在 request 進入與離開 handler 的過程中，補上可觀測欄位與上下文」。

## 概念位置

Observability Middleware 位在 transport layer 與業務 handler 之間。它通常負責 request id、trace context、log context 與 timing。

## 可觀察訊號

系統需要 observability middleware 的訊號是很多 handler 都需要相同的追蹤欄位與可查詢上下文。

## 接近真實網路服務的例子

request id 注入、trace context 傳遞、latency 記錄與結束時的操作 log，都屬於 observability middleware 的責任。

## 設計責任

Observability Middleware 要穩定傳遞 context、避免打斷 error chain，並讓後續 log、metric、trace 可以共用欄位。
