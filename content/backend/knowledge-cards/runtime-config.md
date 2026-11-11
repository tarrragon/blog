---
title: "Runtime Config"
tags: ["執行期設定", "Runtime Config"]
date: 2026-04-24
description: "說明服務在啟動與執行時如何讀取與組合設定"
weight: 154
---

Runtime Config 的核心概念是「服務在執行時需要哪些設定，以及這些設定如何被讀取、預設與覆寫」。它處理的是設定來源與組合規則，不是設定發送流程本身。 可先對照 [Sampling](/backend/knowledge-cards/sampling/)。

## 跟其他概念的關係

Runtime Config 位在 environment variable、config file、secret injection、feature flag 與 application startup 之間。它決定服務如何取得執行所需的參數與開關。 可先對照 [Sampling](/backend/knowledge-cards/sampling/)。

## 可觀察訊號

系統需要 runtime config 的訊號是：

- 不同環境要使用不同參數
- 某些值必須由部署平台或 secret management 注入
- 服務需要可預期的預設值與覆寫順序

## 接近真實網路服務的例子

資料庫連線字串、第三方 API base URL、限制值、路由開關與功能旗標，都屬於 runtime config 的一部分。

## 判斷條件與後果

服務在每個環境啟動時拿到的設定值是否可預期，取決於下面幾條規則是否都有定義。來源優先序沒有定義時，同一個 key 在環境變數與 config file 都有值，服務用哪一個取決於實作細節，換一個環境就換了行為；缺值時用預設值還是拒絕啟動沒有定義時，漏設資料庫連線字串的服務可能帶著空值啟動，到第一個請求才失敗。值沒有型別驗證時，字串形式的數字或布林值在不同語言裡被解讀成不同的值，錯誤到使用時才出現。允許動態更新的設定會讓執行中的服務在不重啟的情況下改變行為，它們跟只在啟動時讀取的設定沒有分開標示時，排查無法從部署紀錄判斷當下生效的是哪個值。
