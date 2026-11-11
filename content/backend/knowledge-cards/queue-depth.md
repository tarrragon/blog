---
title: "Queue Depth"
date: 2026-04-23
description: "說明 queue 中等待處理的訊息數如何反映 backlog 與容量壓力"
weight: 67
---

Queue depth 的核心概念是「queue 中等待處理的訊息數量」。它是 backlog 的直覺訊號，反映進入速度和處理速度的差距。 可先對照 [Queue](/backend/knowledge-cards/queue/)。

## 跟其他概念的關係

Queue depth 是 queue health 的入口指標。Depth 上升可能代表 producer 變快、consumer 變慢、下游變慢、重試增加或 consumer 數量不足。 可先對照 [Queue](/backend/knowledge-cards/queue/)。

## 可觀察訊號與例子

系統需要 queue depth 告警的訊號是工作延遲會影響產品結果。通知 queue depth 持續上升時，使用者可能延遲收到信件；付款入帳 queue depth 上升時，帳務狀態可能延後更新。

## 判斷條件與後果

Queue depth 上升時，單看數量分不出成因是 producer 變快、consumer 變慢、下游變慢、重試增加還是 consumer 數量不足。和 consumer lag、oldest message age、processing rate、error rate 與 unacked messages 一起看時，成因分得開：processing rate 下降代表 consumer 端變慢，error rate 與重試一起上升代表積壓來自重送。數量也不反映訊息的重要性與處理時間，同樣的 depth 在通知 queue 是信件晚到，在付款入帳 queue 是帳務狀態延後更新，所以告警門檻依各個 queue 延遲的代價分開設定。
