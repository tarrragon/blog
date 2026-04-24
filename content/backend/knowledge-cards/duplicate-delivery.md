---
title: "Duplicate Delivery"
tags: ["重複投遞", "Duplicate Delivery"]
date: 2026-04-23
description: "說明同一個訊息被處理多次時如何保持結果穩定"
weight: 5
---

重複投遞的核心概念是「同一個工作或事件可能被 consumer 看見多次」。在 at-least-once delivery 模型中，broker 會優先保證訊息有機會被處理；當 ack 遺失、consumer crash、網路中斷或 timeout 發生時，同一則訊息可能再次投遞。

## 概念位置

重複投遞是可靠訊息系統的正常設計條件。它要求 consumer 把「收到訊息」與「造成外部結果」分開思考，並用 idempotency key、dedup store、唯一約束、狀態機或業務檢查讓多次處理得到同一個結果。

## 可觀察訊號

系統需要處理重複投遞的訊號是訊息會造成金錢、庫存、通知、帳務、點數或外部 API 副作用。只更新可重建投影的事件，重複通常只增加成本；會寄信、扣款、出貨或新增記錄的事件，重複可能造成產品事故。

## 接近真實網路服務的例子

付款成功事件被投遞兩次。若出貨 consumer 只看「收到付款事件」就建立出貨單，可能造成重複出貨；若 consumer 以付款交易 ID 建立唯一處理紀錄，第二次投遞會命中已處理狀態，結果保持穩定。

## 設計責任

Consumer 設計要明確標出 idempotency 邊界。重要事件應有穩定事件 ID、業務鍵、處理紀錄與可觀測欄位；測試要包含同一訊息連續處理、處理中 crash 後重試、外部 API timeout 後重試等情境。
