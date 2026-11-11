---
title: "Request Middleware"
date: 2026-04-23
description: "說明請求處理鏈中的共通攔截與前後置處理"
weight: 1
---

Request Middleware 的核心概念是「在 request 進入 handler 前後插入共通處理」。它承接多個 handler 共用的攔截層與前後置處理。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 跟其他概念的關係

Request Middleware 位在 transport layer 與業務 handler 之間。它處理多個 endpoint 共用的橫切關注，而不是單一業務規則本身。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 可觀察訊號

系統需要 request middleware 的訊號包括：很多 handler 都在重複驗證、關聯 request id、補 log、做權限檢查或遮罩敏感資料。

## 接近真實網路服務的例子

[API Gateway](/backend/knowledge-cards/api-gateway/) middleware 可以先驗證 token；[Admin Endpoint](/backend/knowledge-cards/admin-endpoint/) middleware 可以先做授權與 audit；webhook middleware 可以先驗證 signature 與來源限制。

## 判斷條件與後果

Request Middleware 作用在通過它的每一個 request 上，所以它的每一項約定沒定好，影響的都是全部 endpoint。執行順序沒有定義時，觀測 middleware 若排在驗證之後，被驗證擋下的 request 不留下 log 與 metric；短路條件沒有定義時，某一層提前回應之後，後面的 audit 或清理是否還執行，各層各自假設。context 傳遞沒有定義時，request id 與身分資訊在某一層被丟掉，之後的 handler 與 log 拿不到。副作用界線沒有定義、業務流程寫進攔截層時，讀 handler 的人看不到這段邏輯，而修改它會同時改變所有 endpoint 的行為；安全、觀測與錯誤處理的 middleware 被這類修改波及時，受影響的是全部 request 的驗證與紀錄。
