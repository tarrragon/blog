---
title: "Dependency Isolation"
date: 2026-04-23
description: "說明如何隔離下游依賴，避免單一依賴耗盡共享資源"
weight: 54
---

Dependency isolation 的核心概念是「讓不同下游依賴使用可分開限制的資源」。如果所有依賴共用同一個 worker pool、connection pool 或 queue，單一下游變慢可能耗盡整個服務的處理能力。

## 概念位置

Dependency isolation 是防止 cascading failure 的結構性設計。它可以透過獨立 pool、獨立 queue、bulkhead、timeout、rate limit 與 circuit breaker 實作。

## 可觀察訊號與例子

系統需要 dependency isolation 的訊號是某個低優先下游變慢後，高優先流程也跟著變慢。報表服務查詢很慢時，應讓它只耗用報表專用資源，checkout 的 database pool 則保留給核心交易流程。

## 設計責任

依賴隔離要先標出核心路徑、輔助路徑與共享資源。觀測上要能按依賴查看 pool 使用量、queue depth、timeout 與錯誤率。
