---
title: "Repository Adapter"
date: 2026-04-23
description: "說明持久化層如何把資料模型轉成外部儲存介面"
weight: 1
---

Repository Adapter 的核心概念是「把 application 的 repository port 轉成資料庫或其他持久化存取方式」。 可先對照 [Request ID](/backend/knowledge-cards/request-id/)。

## 跟其他概念的關係

Repository Adapter 位在 application 與 database 之間。它處理 row mapping、查詢組合與錯誤轉換。 可先對照 [Request ID](/backend/knowledge-cards/request-id/)。

## 可觀察訊號

系統需要 repository adapter 的訊號是 domain 模型不能直接依賴 SQL 細節，但 application 需要穩定地讀寫正式狀態。

## 接近真實網路服務的例子

訂單 repository、會員 repository、付款紀錄 repository 都是 repository adapter 的例子。

## 判斷條件與後果

Repository Adapter 的判斷對象是 SQL 與資料庫細節是否停在 adapter 裡。row mapping 寫在業務層時，資料表欄位改名就要改 domain 程式，原因是 domain 模型直接依賴了表的形狀；資料庫錯誤沒有在 adapter 轉成 application 認得的分類（找不到、衝突、暫時失敗）時，業務層要辨識特定資料庫的錯誤碼才能決定重試或回報，換資料庫就要改業務程式。一個 repository 方法寫入多張表時，哪些寫入一起成功或一起失敗由 adapter 的交易範圍決定，這個一致性邊界沒有寫在 port 上時，業務層看不到它。adapter 對真實資料庫跑 contract test，port 回傳的錯誤分類與空結果的形態才有證據跟 domain 的預期一致。
