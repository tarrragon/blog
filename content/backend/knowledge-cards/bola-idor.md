---
title: "BOLA / IDOR"
date: 2026-04-23
description: "說明物件層授權缺失如何讓使用者存取不屬於自己的資料"
weight: 113
---

BOLA / IDOR 的核心概念是「使用者透過修改物件 ID 存取未授權資源」。BOLA 是 Broken Object Level Authorization；IDOR 是 Insecure Direct Object Reference。 可先對照 [BOPLA](/backend/knowledge-cards/bopla/)。

## 跟其他概念的關係

BOLA 是 API 安全中常見的授權問題。Authentication 只能確認呼叫者身份；每次讀寫訂單、檔案、帳戶、發票或 tenant 資源時，仍要檢查該身份是否能操作該物件。 可先對照 [BOPLA](/backend/knowledge-cards/bopla/)。

## 可觀察訊號與例子

系統需要 BOLA 防護的訊號是 API path 或 body 中包含資源 ID。使用者把 `/orders/1001` 改成 `/orders/1002` 時，系統必須確認 1002 是否屬於該使用者或其 tenant。

## 判斷條件與後果

BOLA 檢查寫在哪一層，決定它涵蓋多少條路徑：寫在 usecase 或 policy 層時，每一條讀寫該物件的路徑都經過它；只寫在個別 handler 時，新增的 endpoint 漏寫一次，就多一個改 ID 就能讀別人資料的入口。檢查只比對 tenant boundary 時，同一個 tenant 裡的使用者讀得到彼此的物件；只比對 resource ownership 而沒比對角色權限時，低權限帳號能對自己名下的物件做高權限操作。測試只用合法的 ID 時，上述漏洞在功能測試裡全部通過，所以測試涵蓋跨使用者、跨 tenant、低權限操作與猜測 ID 這幾種請求。
