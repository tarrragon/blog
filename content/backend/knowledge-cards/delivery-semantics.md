---
title: "Delivery Semantics"
date: 2026-04-23
description: "說明事件投遞語意如何定義遺失、重複、順序與補償策略"
weight: 150
---

Delivery semantics 的核心概念是「系統對事件投遞結果的承諾」。它回答訊息可否遺失、可否重複、是否要求順序，以及失敗後如何補償。 可先對照 [Retry Policy](/backend/knowledge-cards/retry-policy/)。

## 跟其他概念的關係

Delivery semantics 直接影響 [retry policy](/backend/knowledge-cards/retry-policy/)、[idempotency](/backend/knowledge-cards/idempotency/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 設計。

## 可觀察訊號與例子

例如支付事件通常需要高可靠與去重；typing indicator 通常可接受遺失。兩者應使用不同的 delivery semantics。

## 判斷條件與後果

選哪一種投遞語意，看一個事件遺失或重複時業務承受的是哪一種結果。支付事件重複會扣款兩次、遺失會漏帳，所以它要求不遺失也不重複處理，代價是生產端要 [retry](/backend/knowledge-cards/retry-policy/)、消費端要做 [idempotency](/backend/knowledge-cards/idempotency/)；typing indicator 遺失一筆只是畫面上少顯示一次，重送的那一筆到達時狀態已經過時，所以它接受遺失。生產者與消費者對同一個事件的語意預設不一致時（生產者會重送，消費者假設不會重複而沒有去重），正常流量下兩者的行為看不出差異，重送發生時事件才被處理兩次，原因是語意只寫在各服務各自的程式碼裡。所以語意寫進事件合約與操作流程，兩端照同一份實作。
