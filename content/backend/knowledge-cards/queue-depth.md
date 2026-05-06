---
title: "Queue Depth"
date: 2026-04-23
description: "說明 queue 中等待處理的訊息數如何反映 backlog 與容量壓力"
weight: 66
---


Queue depth 的核心概念是「queue 中等待處理的訊息數量」。它是 backlog 的直覺訊號，反映進入速度和處理速度的差距。 可先對照 [Queue](/backend/knowledge-cards/queue/)。

## 概念位置

Queue depth 是 queue health 的入口指標。Depth 上升可能代表 producer 變快、consumer 變慢、下游變慢、重試增加或 consumer 數量不足。 可先對照 [Queue](/backend/knowledge-cards/queue/)。

## 可觀察訊號與例子

系統需要 queue depth 告警的訊號是工作延遲會影響產品結果。通知 queue depth 持續上升時，使用者可能延遲收到信件；付款入帳 queue depth 上升時，帳務狀態可能延後更新。

## 設計責任

Queue depth 要和 consumer lag、oldest message age、processing rate、error rate 與 unacked messages 一起看。只看數量容易忽略訊息重要性與處理時間差異。
