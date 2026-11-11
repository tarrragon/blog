---
title: "Function-Level Authorization"
date: 2026-04-23
description: "說明功能操作本身也需要授權，不只資源 ID 需要授權"
weight: 118
---

Function-level authorization 的核心概念是「某個功能或操作本身需要權限」。使用者即使能讀取某個資源，也不一定能匯出、刪除、退款、停用或調整權限。它是 [Authorization](/backend/knowledge-cards/authorization/) 裡以操作為單位的那一種判斷。

## 跟其他概念的關係

Function-level authorization 和 object-level authorization 互補。Object-level 檢查資源歸屬；function-level 檢查操作能力與角色責任。Object-level 缺檢查時的漏洞是 [BOLA / IDOR](/backend/knowledge-cards/bola-idor/)。

## 可觀察訊號與例子

系統需要 function-level authorization 的訊號是同一資源上有高風險操作。客服可以查看訂單，但退款、補發點數、修改收件資訊需要額外權限與 audit。

## 判斷條件與後果

Function-level authorization 的判斷條件是 policy 是否以 action 為單位。policy 只記錄使用者能存取哪個資源時，能讀訂單的客服也能對同一筆訂單退款，原因是 object-level 檢查只確認資源歸屬，不區分操作；action 寫進 policy 時（`order.read`、`order.refund`、`user.export`），退款與匯出各自需要對應的權限。介面隱藏了高風險操作的按鈕，而後端 endpoint 沒有檢查 action 時，低權限使用者直接呼叫那個 endpoint 仍會成功，所以測試覆蓋的是低權限使用者直接呼叫高風險 endpoint 的情境。
