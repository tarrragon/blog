---
title: "Request ID"
date: 2026-04-23
description: "說明單次 request 的識別碼如何支援 log 搜尋與問題定位"
weight: 105
---

Request ID 的核心概念是「識別單次 request 的 ID」。它讓同一個 request 在 [API Gateway](api-gateway/)、application、database log 與 error response 之間可以被追蹤。

## 概念位置

Request ID 是同步 request 診斷的基本欄位。它通常比 trace 簡單，適合放在 log、response header 與客服查詢流程中。

## 可觀察訊號與例子

系統需要 request ID 的訊號是使用者回報錯誤時，工程師需要快速找到對應 log。錯誤頁顯示 request ID，客服可以把 ID 交給工程師查完整處理路徑。

## 設計責任

Request ID 要在入口統一產生或接受可信上游傳入，並在 response、log、trace 與下游呼叫中保留。安全設計要避免讓外部可控 ID 汙染內部查詢或造成 spoofing。
