---
title: "Excessive Data Exposure"
date: 2026-04-23
description: "說明 API 回傳過多資料如何增加敏感資訊外洩風險"
weight: 115
---


Excessive data exposure 的核心概念是「API 回傳超出呼叫者需要的資料」。即使前端沒有顯示，資料仍然已經離開後端邊界。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 概念位置

資料暴露是輸出邊界問題。API response 應依用途設計 DTO、欄位遮罩與角色權限，內部資料模型應留在服務邊界內。 可先對照 [Expand / Contract](/backend/knowledge-cards/expand-contract/)。

## 可觀察訊號與例子

系統需要防 excessive data exposure 的訊號是 response 包含敏感欄位、內部狀態或其他角色才需要的資料。客服 API 可以看部分電話；一般使用者訂單 API 則應只回傳使用者完成操作所需欄位。

## 設計責任

防護要包含 response schema、欄位分級、data masking、contract test 與 log 檢查。資料一旦回傳給 client，就應視為已暴露。
