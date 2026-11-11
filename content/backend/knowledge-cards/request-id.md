---
title: "Request ID"
date: 2026-04-23
description: "說明單次 request 的識別碼如何支援 log 搜尋與問題定位"
weight: 106
---

Request ID 的核心概念是「識別單次 request 的 ID」。它讓同一個 request 在 [API Gateway](/backend/knowledge-cards/api-gateway/)、application、database log 與 error response 之間可以被追蹤。

## 跟其他概念的關係

Request ID 是同步 request 診斷的基本欄位。它通常比 trace 簡單，適合放在 log、response header 與客服查詢流程中。 可先對照 [API Gateway](/backend/knowledge-cards/api-gateway/)。

## 可觀察訊號與例子

系統需要 request ID 的訊號是使用者回報錯誤時，工程師需要快速找到對應 log。錯誤頁顯示 request ID，客服可以把 ID 交給工程師查完整處理路徑。 錯誤畫面上怎麼顯示、入口怎麼產生並傳給後端與 log，見 [11.16 面向終端使用者的錯誤碼與請求編號](/backend/11-api-design/end-user-error-code-and-reference-id/)。

## 判斷條件與後果

Request ID 的判斷看兩件事：ID 從哪裡來，以及它是否一路帶到每一個紀錄點。各服務各自產生 ID 時，同一個 request 在 gateway、application 與 database log 裡是幾個不同的值，客服拿到錯誤頁上的 ID 也串不起完整的處理路徑；ID 沒有寫進 response、trace 與下游呼叫時，路徑在那一跳斷開。直接採用外部 client 傳入的 ID 時，呼叫方可以送出跟別人相同的值（spoofing）或格式異常的字串，查詢時撈到不屬於這個 request 的 log，或把異常字串帶進內部查詢；所以只沿用可信上游傳入的 ID，其餘在入口重新產生。
