---
title: "Request Middleware"
date: 2026-04-23
description: "說明請求處理鏈中的共通攔截與前後置處理"
weight: 0
---

Request Middleware 的核心概念是「在 request 進入 handler 前後插入共通處理」。它承接多個 handler 共用的攔截層與前後置處理。

## 概念位置

Request Middleware 位在 transport layer 與業務 handler 之間。它處理多個 endpoint 共用的橫切關注，而不是單一業務規則本身。

## 可觀察訊號

系統需要 request middleware 的訊號包括：很多 handler 都在重複驗證、關聯 request id、補 log、做權限檢查或遮罩敏感資料。

## 接近真實網路服務的例子

[API Gateway](/backend/knowledge-cards/api-gateway/) middleware 可以先驗證 token；[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/) middleware 可以先做授權與 audit；webhook middleware 可以先驗證 signature 與來源限制。

## 設計責任

Request Middleware 要定義執行順序、短路條件、context 傳遞與副作用界線。安全、觀測與錯誤處理的 middleware 特別需要穩定，不應把業務流程藏在攔截層。
