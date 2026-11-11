---
title: "Message Protocol"
date: 2026-04-23
description: "說明 queue 或 stream message 如何對齊格式與處理語意"
weight: 1
---

Message Protocol 的核心概念是「producer 與 consumer 對訊息格式、處理順序與失敗結果達成一致」。 可先對照 [Metric Cardinality](/backend/knowledge-cards/metric-cardinality/)。

## 跟其他概念的關係

Message Protocol 位在 producer、broker 與 consumer 之間。它適用於 queue、stream 與事件傳遞。 可先對照 [Metric Cardinality](/backend/knowledge-cards/metric-cardinality/)。

## 可觀察訊號

系統需要 message protocol 的訊號是工作離開 request 後仍要被處理，而且需要明確的 schema、重試語意與去重責任。

## 接近真實網路服務的例子

訂單事件、付款事件、通知事件與分析事件都需要 message protocol。消息格式變更時，producer 與 consumer 都要能解讀版本演進。

## 判斷條件與後果

Message Protocol 的四項約定各自對應 producer 與 consumer 之間的一種失效。欄位結構沒有定義時，consumer 依自己的假設解析，producer 改了一個欄位名稱，consumer 可能讀到空值而不報錯。版本相容沒有定義時，producer 先上線新格式，還沒更新的 consumer 解析失敗或誤讀，原因是兩端各自部署，新舊格式會並存一段時間。錯誤處理沒有定義時，解析失敗的訊息被丟棄、反覆重試而卡住後面的訊息，或送進 dead letter，三種結果由各個 consumer 各自決定。重播安全沒有定義時，同一則訊息被重送或重放，consumer 重複執行副作用（重複扣款、重複寄信）。交付保證（至少一次、至多一次）由 queue contract 規定，message protocol 規定的是訊息內容在兩端怎麼被解讀。
