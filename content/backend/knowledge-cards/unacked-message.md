---
title: "Unacked Message"
date: 2026-04-23
description: "說明 broker 已投遞但尚未收到 consumer 確認的訊息"
weight: 61
---


Unacked message 的核心概念是「broker 已投遞出去，但尚未收到 consumer ack 的訊息」。它通常代表訊息正在處理、consumer 卡住、ack 遺失或 handler 耗時過長。 可先對照 [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/)。

## 概念位置

Unacked message 是 queue health 的重要訊號。Queue depth 告訴團隊有多少訊息等著處理；unacked 則告訴團隊有多少訊息卡在 consumer 手上。 可先對照 [Unrestricted Resource Consumption](/backend/knowledge-cards/unrestricted-resource-consumption/)。

## 可觀察訊號與例子

系統需要追蹤 unacked 的訊號是 queue 看起來已分派，但產品結果仍然延遲。寄信 consumer 拿到大量訊息後卡在外部 SMTP API，queue ready 數不高，但 unacked 數會持續上升。

## 設計責任

Unacked 告警要和 prefetch、handler timeout、consumer health 與 downstream latency 一起看。Runbook 應說明何時重啟 consumer、何時調整 prefetch、何時暫停投遞。
