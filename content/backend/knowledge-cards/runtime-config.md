---
title: "Runtime Config"
tags: ["執行期設定", "Runtime Config"]
date: 2026-04-24
description: "說明服務在啟動與執行時如何讀取與組合設定"
weight: 153
---


Runtime Config 的核心概念是「服務在執行時需要哪些設定，以及這些設定如何被讀取、預設與覆寫」。它處理的是設定來源與組合規則，不是設定發送流程本身。 可先對照 [Sampling](/backend/knowledge-cards/sampling/)。

## 概念位置

Runtime Config 位在 environment variable、config file、secret injection、feature flag 與 application startup 之間。它決定服務如何取得執行所需的參數與開關。 可先對照 [Sampling](/backend/knowledge-cards/sampling/)。

## 可觀察訊號

系統需要 runtime config 的訊號是：

- 不同環境要使用不同參數
- 某些值必須由部署平台或 secret management 注入
- 服務需要可預期的預設值與覆寫順序

## 接近真實網路服務的例子

資料庫連線字串、第三方 API base URL、限制值、路由開關與功能旗標，都屬於 runtime config 的一部分。

## 設計責任

設計時要定義設定來源優先序、缺值行為、型別驗證、啟動失敗條件與是否允許動態更新。Runtime Config 應該讓服務在不同環境中保持一致的配置語意。
