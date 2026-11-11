---
title: "Rate Limit"
tags: ["速率限制", "Rate Limit"]
date: 2026-04-23
description: "說明限流如何保護服務入口、下游依賴與租戶公平性"
weight: 29
---

Rate limit 的核心概念是「限制某個主體在一段時間內可以使用的資源量」。主體可以是 user、API key、IP、tenant、endpoint、worker、[producer](/backend/knowledge-cards/producer/) 或內部服務。

## 跟其他概念的關係

Rate limit 是容量保護與公平性工具。它可以保護登入、搜尋、匯出、第三方 API、webhook endpoint 與下游服務，降低單一來源耗盡共享資源的風險；被擋下之後對消費者承諾什麼邊界（429 / Retry-After 的契約語意）、由 [Rate Limit Contract](/backend/knowledge-cards/rate-limit-contract/) 卡承擔。 可先對照 [Producer](/backend/knowledge-cards/producer/)。

## 可觀察訊號與例子

系統需要 rate limit 的訊號是少數使用者或客戶端造成大量 request。匯出報表 API 缺少 rate limit 時，單一 tenant 的批次工作可能佔滿 [database](/backend/knowledge-cards/database/) [connection pool](/backend/knowledge-cards/connection-pool/)，影響其他 tenant 的正常查詢。

## 判斷條件與後果

限流設計的每一項沒有定義時各有後果。主體（user、API key、tenant 這類）沒有定義時，限流算不出是誰用了多少，單一 tenant 的批次工作照樣佔滿 connection pool；窗口與配額沒有定義時，沒有可以比較的門檻。超限回應沒有給 retry-after 或配額資訊時，對外的 client 不知道多久之後可以重試，立刻重送的 client 讓被擋的請求量增加。例外權限沒有明確列出時，被放行的流量不受配額限制，也查不到是誰放行的；沒有觀測欄位時，看不出誰被擋、擋了多少。內部服務的限流搭配 [alert](/backend/knowledge-cards/alert/)、[token bucket](/backend/knowledge-cards/token-bucket/) 與容量規劃，被擋的量持續上升時，容量不足才會被看見。完整的實作指南（單機 middleware、Redis 分散式限速、配額設計）見 [Rate Limit 實作](/backend/09-performance-capacity/rate-limit-implementation/)。

監控系統中 per-SDK rate limiting 和偽造流量防護的具體實作見 [監控知識卡：Rate Limiting](/devops/monitoring/knowledge-cards/rate-limiting/)。
