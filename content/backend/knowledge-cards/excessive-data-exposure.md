---
title: "Excessive Data Exposure"
date: 2026-04-23
description: "說明 API 回傳過多資料如何增加敏感資訊外洩風險"
weight: 116
---

Excessive data exposure 的核心概念是「API 回傳超出呼叫者需要的資料」。即使前端沒有顯示，資料仍然已經離開後端邊界。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 跟其他概念的關係

資料暴露是輸出邊界問題。API response 應依用途設計 DTO、欄位遮罩與角色權限，內部資料模型應留在服務邊界內。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 可觀察訊號與例子

系統需要防 excessive data exposure 的訊號是 response 包含敏感欄位、內部狀態或其他角色才需要的資料。客服 API 可以看部分電話；一般使用者訂單 API 則應只回傳使用者完成操作所需欄位。

## 判斷條件與後果

資料一旦回傳給 client 就已經離開後端邊界，不論前端是否顯示，所以判斷的位置在回傳之前。Response 直接序列化內部資料模型時，模型新增的每一個欄位都自動出現在 API 回應裡，原因是回應的形狀跟著模型變，沒有一份 response schema 限定輸出哪些欄位。欄位沒有分級時，分不出哪些欄位只有客服這類角色才能看，一般使用者的訂單 API 就回傳了同樣的內容；沒有 data masking 時，需要部分顯示的欄位（客服看到的部分電話）只能全給或全不給。沒有 contract test 時，回應多出一個敏感欄位不會讓任何測試失敗；沒有 log 檢查時，同樣的欄位也可能經由日誌外流。
