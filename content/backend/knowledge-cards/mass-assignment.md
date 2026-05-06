---
title: "Mass Assignment"
date: 2026-04-23
description: "說明自動綁定 request 欄位如何造成未授權欄位被修改"
weight: 114
---


Mass assignment 的核心概念是「框架或程式把 request 欄位自動寫入資料模型」。若沒有輸入白名單，client 可能送入不該由外部控制的欄位。 可先對照 [Message Persistence](/backend/knowledge-cards/message-persistence/)。

## 概念位置

Mass assignment 是 API 輸入邊界問題。它常出現在直接把 JSON body bind 到 ORM model、domain model 或 persistence model 的程式碼中。 可先對照 [Message Persistence](/backend/knowledge-cards/message-persistence/)。

## 可觀察訊號與例子

系統需要防 mass assignment 的訊號是 request body 可以包含內部欄位。註冊 API 若直接綁定 `User` model，攻擊者可能加入 `role: admin` 或 `email_verified: true`。

## 設計責任

防護要使用輸入 DTO、欄位白名單、policy validation 與測試。外部 request schema 應只包含該操作允許修改的欄位。
