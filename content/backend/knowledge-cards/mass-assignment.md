---
title: "Mass Assignment"
date: 2026-04-23
description: "說明自動綁定 request 欄位如何造成未授權欄位被修改"
weight: 115
---

Mass assignment 的核心概念是「框架或程式把 request 欄位自動寫入資料模型」。若沒有輸入白名單，client 可能送入不該由外部控制的欄位。 可先對照 [Message Persistence](/backend/knowledge-cards/message-persistence/)。

## 跟其他概念的關係

Mass assignment 是 API 輸入邊界問題。它常出現在直接把 JSON body bind 到 ORM model、domain model 或 persistence model 的程式碼中。 可先對照 [Message Persistence](/backend/knowledge-cards/message-persistence/)。

## 可觀察訊號與例子

系統需要防 mass assignment 的訊號是 request body 可以包含內部欄位。註冊 API 若直接綁定 `User` model，攻擊者可能加入 `role: admin` 或 `email_verified: true`。

## 判斷條件與後果

Mass assignment 成立的條件是外部 request 寫得到的欄位多於這個操作允許修改的欄位。request body 直接綁定到 ORM 或 domain model 時，模型上每一個欄位都能從外部寫入，包括 `role`、`email_verified` 這類只該由系統內部設定的欄位，攻擊者在註冊請求裡多帶一個欄位就能提升權限。輸入 DTO 或欄位白名單把外部 request schema 限制在這個操作允許修改的欄位，多出來的欄位在綁定時被丟掉或拒絕；同一個欄位依呼叫者身分有不同權限時（一般使用者與管理員能改的欄位不同），白名單分不出身分，要由 policy validation 判斷。這幾層防護只有在測試送入不允許的欄位、確認它沒有被寫入時才驗證得到，原因是正常請求不帶這些欄位，功能測試走不到這條路徑。
