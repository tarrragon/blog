---
title: "Consumer Group"
date: 2026-06-22
description: "說明一組 consumer 如何共同分攤 stream 或 topic 的處理責任"
weight: 72
tags: ["backend", "message-queue"]
---

Consumer group 的核心概念是「一組 [consumer](/backend/knowledge-cards/consumer/) 共同承擔某個 stream 或 [topic](/backend/knowledge-cards/topic/) 的處理進度」。同一 group 內的 consumer 分攤工作（每筆訊息只被 group 內的一個 consumer 處理）；不同 group 可以各自獨立處理同一批事件，實現 [fan-out](/backend/knowledge-cards/fan-out/)。

## 概念位置

Consumer group 是事件流跟多服務訂閱的協調模型。分析服務、搜尋索引服務、通知服務可以用不同 group 讀同一 topic — 每個 group 有自己的 [offset](/backend/knowledge-cards/offset/) 進度跟 [consumer lag](/backend/knowledge-cards/consumer-lag/)。

在 Kafka 中，consumer group 是一級概念、由 group coordinator 管理 [partition](/backend/knowledge-cards/partition/) 分配（rebalance）。在 Redis Streams 中對應 consumer group（XREADGROUP）。在 RabbitMQ 中沒有原生 consumer group — 多個 consumer 連到同一個 queue 就是 competing consumers、不同 queue 綁到同一個 exchange 就是 fan-out。

## 使用情境

系統需要 consumer group 的訊號是同一事件要被多個系統各自處理。訂單事件同時給出貨、通知與報表 — 三個 consumer group 各自有自己的處理速度、錯誤率跟重放流程。

Consumer group 的 rebalance（partition 重新分配）是 Kafka 生態的常見運維議題。Consumer 加入或離開 group 時觸發 rebalance、rebalance 期間 partition 暫時無人消費、造成短暫的處理停頓。Rebalance 時間跟 partition 數量、consumer 數量有關。

## 設計責任

Consumer group 要設計 group 名稱（跟服務名稱對齊、方便辨識）、offset / checkpoint 策略（auto-commit vs manual commit）、rebalance 行為（cooperative vs eager）、[consumer lag](/backend/knowledge-cards/consumer-lag/) 告警閾值與 [replay runbook](/backend/knowledge-cards/replay-runbook/) 權限。不同 group 的失敗應分開觀測跟處理 — 通知 group 落後不應影響出貨 group 的監控判讀。
