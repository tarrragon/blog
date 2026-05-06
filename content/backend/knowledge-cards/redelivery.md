---
title: "Redelivery"
date: 2026-04-23
description: "說明 broker 重新投遞訊息時 consumer 需要承擔的重入責任"
weight: 62
---


Redelivery 的核心概念是「broker 把先前投遞過的訊息再次交給 consumer」。常見原因包含 consumer crash、ack timeout、nack requeue、連線中斷或 broker failover。 可先對照 [Release Freeze](/backend/knowledge-cards/release-freeze/)。

## 概念位置

Redelivery 是 at-least-once delivery 的正常結果。它要求 consumer 具備 idempotency、處理紀錄、狀態檢查與可觀測欄位，讓重複進入的訊息維持同一個業務結果。 可先對照 [Release Freeze](/backend/knowledge-cards/release-freeze/)。

## 可觀察訊號與例子

系統需要關注 redelivery 的訊號是同一事件被處理多次、retry count 上升或 dead-letter 增加。付款成功事件 redelivery 時，出貨 consumer 要能辨識該付款已處理。

## 設計責任

Redelivery 指標要記錄原因、次數與事件 ID。Consumer 測試應覆蓋首次處理、處理中 crash、redelivery 後命中已處理紀錄與永久失敗進 dead-letter。
