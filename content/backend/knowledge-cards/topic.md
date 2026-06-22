---
title: "Topic"
date: 2026-06-22
description: "說明 topic 如何把事件依主題分流給不同訂閱者"
weight: 134
tags: ["backend", "message-queue"]
---

Topic 的核心概念是「用主題名稱描述一類事件或訊息」。[Producer](/backend/knowledge-cards/producer/) 把事件發布到 topic，[broker](/backend/knowledge-cards/broker/) 再依照訂閱關係、[routing rule](/backend/knowledge-cards/routing-rule/) 或 stream 模型把事件交給對應 [consumer](/backend/knowledge-cards/consumer/)。

## 概念位置

Topic 是事件分流的命名邊界。它讓訂單、付款、會員、通知、庫存等事件可以被不同服務訂閱，也讓團隊用事件種類思考資料流與責任範圍。

Topic 跟 [partition](/backend/knowledge-cards/partition/) 的關係是：topic 是邏輯命名空間，partition 是 topic 內的物理分片。Topic 跟 [fan-out](/backend/knowledge-cards/fan-out/) 的關係是：多個 [consumer group](/backend/knowledge-cards/consumer-group/) 訂閱同一個 topic，每個 group 各自消費全量事件，實現 fan-out。

在 RabbitMQ 生態中，topic 對應 exchange + routing key 的組合；在 NATS 中 topic 對應 subject。概念相同但術語跟語意細節不同。

## 使用情境

系統需要 topic 設計的訊號是同一個事件來源會供多個 downstream 使用。付款完成事件可以給出貨、通知、報表與風控使用；所有事件都混在同一條 [queue](/backend/knowledge-cards/queue/) 時，consumer 會承擔更多過濾與相容性成本。

Topic 命名規則影響長期治理。`orders.payment.completed` 比 `event_1` 更容易被搜尋跟管理。命名規則要在團隊間統一、進 [queue contract](/backend/knowledge-cards/queue-contract/) 管理。

## 設計責任

Topic 設計要定義命名規則、事件 schema、相容性策略（schema evolution）、權限控制（誰能 publish / subscribe）、[retention](/backend/knowledge-cards/retention/) 期限、[replay runbook](/backend/knowledge-cards/replay-runbook/) 範圍與 ownership（哪個團隊負責這個 topic）。操作面要能依 topic 查看 publish rate、[consumer lag](/backend/knowledge-cards/consumer-lag/)、錯誤率與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 數量。
