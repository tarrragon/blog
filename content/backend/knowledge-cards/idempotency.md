---
title: "Idempotency"
date: 2026-04-23
description: "說明同一操作執行多次時如何保持結果一致"
weight: 25
---

Idempotency 的核心概念是「同一操作執行一次或多次，最終業務結果相同」。後端系統用 idempotency 保護重試、重複投遞、使用者重送 request 與外部 API timeout。

## 概念位置

Idempotency 是副作用邊界的穩定性設計。查詢通常天然接近 idempotent；建立訂單、扣款、出貨、寄送通知與發放點數都需要額外設計 idempotency key 或狀態檢查。

## 可觀察訊號與例子

系統需要 idempotency 的訊號是同一 intent 可能重送。使用者按兩次付款、broker 重複投遞付款成功事件、HTTP client timeout 後重試，都可能讓同一業務意圖進入系統多次。

## 設計責任

Idempotency 設計要有穩定 key、唯一約束、處理紀錄、結果查詢與過期策略。測試要覆蓋連續重送、處理中 crash、外部 API timeout 與 replay。
