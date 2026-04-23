---
title: "Function-Level Authorization"
date: 2026-04-23
description: "說明功能操作本身也需要授權，不只資源 ID 需要授權"
weight: 117
---

Function-level authorization 的核心概念是「某個功能或操作本身需要權限」。使用者即使能讀取某個資源，也不一定能匯出、刪除、退款、停用或調整權限。

## 概念位置

Function-level authorization 和 object-level authorization 互補。Object-level 檢查資源歸屬；function-level 檢查操作能力與角色責任。

## 可觀察訊號與例子

系統需要 function-level authorization 的訊號是同一資源上有高風險操作。客服可以查看訂單，但退款、補發點數、修改收件資訊需要額外權限與 audit。

## 設計責任

授權設計要把 action 納入 policy，例如 `order.read`、`order.refund`、`user.export`。測試要覆蓋低權限使用者直接呼叫高風險 endpoint 的情境。
