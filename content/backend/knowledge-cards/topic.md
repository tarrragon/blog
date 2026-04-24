---
title: "Topic"
date: 2026-04-23
description: "說明 topic 如何把事件依主題分流給不同訂閱者"
weight: 134
---

Topic 的核心概念是「用主題名稱描述一類事件或訊息」。[Producer](/backend/knowledge-cards/producer/) 把事件發布到 topic，[broker](/backend/knowledge-cards/broker/) 再依照訂閱關係、[routing rule](/backend/knowledge-cards/routing-rule/) 或 stream 模型把事件交給對應 [consumer](/backend/knowledge-cards/consumer/)。

## 概念位置

Topic 是事件分流的命名邊界。它讓訂單、付款、會員、通知、庫存等事件可以被不同服務訂閱，也讓團隊用事件種類思考資料流與責任範圍。

## 可觀察訊號與例子

系統需要 topic 設計的訊號是同一個事件來源會供多個 downstream 使用。付款完成事件可以給出貨、通知、報表與風控使用；所有事件都混在同一條 [queue](/backend/knowledge-cards/queue/) 時，consumer 會承擔更多過濾與相容性成本。

## 設計責任

Topic 設計要定義命名規則、事件 schema、相容性、權限、[retention](/backend/knowledge-cards/retention/)、[replay runbook](/backend/knowledge-cards/replay-runbook/) 範圍與擁有者。操作上要能依 topic 查看 publish rate、[consumer lag](/backend/knowledge-cards/consumer-lag/)、錯誤率與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 數量。
