---
title: "Repository Adapter"
date: 2026-04-23
description: "說明持久化層如何把資料模型轉成外部儲存介面"
weight: 0
---


Repository Adapter 的核心概念是「把 application 的 repository port 轉成資料庫或其他持久化存取方式」。 可先對照 [Request ID](/backend/knowledge-cards/request-id/)。

## 概念位置

Repository Adapter 位在 application 與 database 之間。它處理 row mapping、查詢組合與錯誤轉換。 可先對照 [Request ID](/backend/knowledge-cards/request-id/)。

## 可觀察訊號

系統需要 repository adapter 的訊號是 domain 模型不能直接依賴 SQL 細節，但 application 需要穩定地讀寫正式狀態。

## 接近真實網路服務的例子

訂單 repository、會員 repository、付款紀錄 repository 都是 repository adapter 的例子。

## 設計責任

Repository Adapter 要處理資料映射、一致性邊界、錯誤分類與 contract test，避免把 SQL 細節滲透到業務層。
