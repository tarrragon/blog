---
title: "Unacked Message"
date: 2026-04-23
description: "說明 broker 已投遞但尚未收到 consumer 確認的訊息"
weight: 62
---

Unacked message 的核心概念是「broker 已投遞出去，但尚未收到 consumer ack 的訊息」。它通常代表訊息正在處理、consumer 卡住、ack 遺失或 handler 耗時過長。 可先對照 [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/)。

## 跟其他概念的關係

Unacked message 是 queue health 的重要訊號。Queue depth 告訴團隊有多少訊息等著處理；unacked 則告訴團隊有多少訊息卡在 consumer 手上。 可先對照 [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/)。

## 可觀察訊號與例子

系統需要追蹤 unacked 的訊號是 queue 看起來已分派，但產品結果仍然延遲。寄信 consumer 拿到大量訊息後卡在外部 SMTP API，queue ready 數不高，但 unacked 數會持續上升。

## 判斷條件與後果

Unacked 數上升有幾種成因，跟它一起變動的指標分得開這幾種。prefetch 設得大時，一個 consumer 一次拿走大量訊息，unacked 數高而其他 consumer 閒著，延遲來自分配不均；downstream latency 上升時，每筆訊息停在 handler 裡的時間拉長，unacked 跟著上升，重啟 consumer 只是把訊息交給下一個同樣會等下游的 handler；consumer health 異常或處理超過 handler timeout 時，訊息握在一個已經不再前進的程序手上。調小 prefetch、暫停投遞與重啟 consumer 各自對應其中一種成因，所以 runbook 照這幾個指標的組合寫出各個處置的時機。
