---
title: "Fan-out"
date: 2026-04-23
description: "說明單一事件同時分發給多個下游的訊息拓撲"
weight: 141
---


Fan-out 的核心概念是「一個事件被多個訂閱者各自處理」。它常用在通知、分析、稽核與衍生資料同步，讓單一 producer 不需知道每個下游的執行細節。 可先對照 [Pub/Sub](/backend/knowledge-cards/pub-sub/)。

## 概念位置

Fan-out 常搭配 [pub/sub](/backend/knowledge-cards/pub-sub/)、[topic](/backend/knowledge-cards/topic/) 或 stream consumer group。若每個下游都需要可靠處理，通常還要搭配 [durable queue](/backend/knowledge-cards/durable-queue/) 與 [idempotency](/backend/knowledge-cards/idempotency/)。

## 可觀察訊號與例子

例如 `order.paid` 同時觸發通知、出貨、報表與風控。Fan-out 能降低耦合，但也會擴大排障範圍，因此需要明確的 trace 與事件識別欄位。

## 設計責任

設計時要定義每個訂閱者的可靠性等級與回復策略，避免把所有下游都綁成同一個失敗域。
