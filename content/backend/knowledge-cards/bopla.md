---
title: "BOPLA"
date: 2026-04-23
description: "說明屬性層授權缺失如何讓使用者讀寫不該暴露的欄位"
weight: 114
---

BOPLA 的核心概念是「物件屬性層級的授權缺失」。即使使用者可以存取某個物件，也不代表可以讀取或修改該物件的所有欄位。 可先對照 [Broker](/backend/knowledge-cards/broker/)。

## 跟其他概念的關係

BOPLA 是 field-level policy 的安全問題。訂單物件可以讓使用者查看商品與金額，但內部風控欄位、成本、客服註記或權限欄位需要更高權限。 可先對照 [Broker](/backend/knowledge-cards/broker/)。

## 可觀察訊號與例子

系統需要 BOPLA 防護的訊號是 API 回傳完整資料模型，或允許 client 送入任意欄位。使用者更新個人資料時，外部輸入欄位應排除 `role`、`is_admin` 或 `credit_limit`。

## 判斷條件與後果

公開 API 的欄位集合直接等於內部資料模型時，BOPLA 隨每一次模型變更擴大：新增的內部欄位（風控欄位、成本、客服註記）沒有經過任何決定就出現在回應裡，client 多送一個 `role` 或 `credit_limit` 就寫進模型。沒有欄位分級時，判斷不了哪些欄位要更高權限或遮罩；輸入用白名單、輸出用固定 schema 時，沒列出的欄位既不進也不出，新增欄位要有人明確加入才會暴露。所以公開 API 的 DTO 和內部資料模型分開定義，並用測試確認未授權的欄位讀不到也寫不進。
