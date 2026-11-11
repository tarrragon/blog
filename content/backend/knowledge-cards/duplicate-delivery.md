---
title: "Duplicate Delivery"
tags: ["重複投遞", "Duplicate Delivery"]
date: 2026-04-23
description: "說明同一個訊息被處理多次時如何保持結果穩定"
weight: 6
---

重複投遞的核心概念是「同一個工作或事件可能被 consumer 看見多次」。在 at-least-once delivery 模型中，broker 會優先保證訊息有機會被處理；當 ack 遺失、consumer crash、網路中斷或 timeout 發生時，同一則訊息可能再次投遞。 可先對照 [Durable Queue](/backend/knowledge-cards/durable-queue/)。

## 跟其他概念的關係

重複投遞是可靠訊息系統的正常設計條件。它要求 consumer 把「收到訊息」與「造成外部結果」分開思考，並用 idempotency key、dedup store、唯一約束、狀態機或業務檢查讓多次處理得到同一個結果。 可先對照 [Durable Queue](/backend/knowledge-cards/durable-queue/)。

## 可觀察訊號

系統需要處理重複投遞的訊號是訊息會造成金錢、庫存、通知、帳務、點數或外部 API 副作用。只更新可重建投影的事件，重複通常只增加成本；會寄信、扣款、出貨或新增記錄的事件，重複可能造成產品事故。

## 接近真實網路服務的例子

付款成功事件被投遞兩次。若出貨 consumer 只看「收到付款事件」就建立出貨單，可能造成重複出貨；若 consumer 以付款交易 ID 建立唯一處理紀錄，第二次投遞會命中已處理狀態，結果保持穩定。

## 判斷條件與後果

Consumer 處理會造成外部結果的訊息時（扣款、出貨、寄信），重複投遞直接變成重複的外部結果，原因是 at-least-once 模型下 ack 遺失的訊息會被再投遞一次。Consumer 沒有標出 idempotency 邊界時，分不出處理流程裡哪一步重做是安全的、哪一步重做會產生第二筆外部結果。事件沒有穩定的事件 ID 或業務鍵時，第二次投遞無從認出是重複，處理紀錄也沒有可以比對的鍵；沒有可觀測欄位時，重複發生過幾次查不出來。測試只跑一次正常處理時，同一訊息連續處理、處理中 crash 後重試、外部 API timeout 後重試這幾條會產生重複的路徑都沒有執行過，重複出貨這類事故要到正式環境才出現。
