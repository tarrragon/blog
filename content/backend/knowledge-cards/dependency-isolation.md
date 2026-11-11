---
title: "Dependency Isolation"
date: 2026-04-23
description: "說明如何隔離下游依賴，避免單一依賴耗盡共享資源"
weight: 55
---

Dependency isolation 的核心概念是「讓不同下游依賴使用可分開限制的資源」。如果所有依賴共用同一個 worker pool、connection pool 或 queue，單一下游變慢可能耗盡整個服務的處理能力。 可先對照 [Deployment Contract](/backend/knowledge-cards/deployment-contract/)。

## 跟其他概念的關係

Dependency isolation 是防止 cascading failure 的結構性設計。它可以透過獨立 pool、獨立 queue、bulkhead、timeout、rate limit 與 circuit breaker 實作。 可先對照 [Deployment Contract](/backend/knowledge-cards/deployment-contract/)。

## 可觀察訊號與例子

系統需要 dependency isolation 的訊號是某個低優先下游變慢後，高優先流程也跟著變慢。報表服務查詢很慢時，應讓它只耗用報表專用資源，checkout 的 database pool 則保留給核心交易流程。

## 判斷條件與後果

依賴隔離的前提是分得出服務裡哪些路徑是核心、哪些是輔助，以及兩者共用了哪些資源。核心路徑與輔助路徑共用同一個 worker pool 或 connection pool 時，輔助路徑的下游變慢會佔住 pool 裡的連線，核心路徑拿不到連線而跟著變慢，代價是低優先的報表查詢拖慢了 checkout，原因是 pool 的上限由兩條路徑共用。資源分開之後，pool 使用量、queue depth、timeout 與錯誤率只按整個服務彙總時，看不出是哪一個依賴用完了自己那一份資源；所以這幾項指標按依賴分開記錄。
