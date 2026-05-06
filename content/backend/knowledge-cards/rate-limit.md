---
title: "Rate Limit"
tags: ["速率限制", "Rate Limit"]
date: 2026-04-23
description: "說明限流如何保護服務入口、下游依賴與租戶公平性"
weight: 28
---


Rate limit 的核心概念是「限制某個主體在一段時間內可以使用的資源量」。主體可以是 user、API key、IP、tenant、endpoint、worker、[producer](/backend/knowledge-cards/producer/) 或內部服務。

## 概念位置

Rate limit 是容量保護與公平性工具。它可以保護登入、搜尋、匯出、第三方 API、webhook endpoint 與下游服務，降低單一來源耗盡共享資源的風險。 可先對照 [Producer](/backend/knowledge-cards/producer/)。

## 可觀察訊號與例子

系統需要 rate limit 的訊號是少數使用者或客戶端造成大量 request。匯出報表 API 缺少 rate limit 時，單一 tenant 的批次工作可能佔滿 [database](/backend/knowledge-cards/database/) [connection pool](/backend/knowledge-cards/connection-pool/)，影響其他 tenant 的正常查詢。

## 設計責任

限流設計要定義主體、窗口、配額、超限回應、例外權限與觀測欄位。對外 API 要提供清楚的 retry-after 或配額資訊；內部服務要搭配 [alert](/backend/knowledge-cards/alert/)、[token bucket](/backend/knowledge-cards/token-bucket/) 與容量規劃。
