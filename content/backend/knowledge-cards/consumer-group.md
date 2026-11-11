---
title: "Consumer Group"
date: 2026-06-22
description: "說明一組 consumer 如何共同分攤 stream 或 topic 的處理責任"
weight: 73
tags: ["backend", "message-queue"]
---

Consumer group 的核心概念是「一組 [consumer](/backend/knowledge-cards/consumer/) 共同承擔某個 stream 或 [topic](/backend/knowledge-cards/topic/) 的處理進度」。同一 group 內的 consumer 分攤工作（每筆訊息只被 group 內的一個 consumer 處理）；不同 group 可以各自獨立處理同一批事件，實現 [fan-out](/backend/knowledge-cards/fan-out/)。

## 跟其他概念的關係

Consumer group 是事件流跟多服務訂閱的協調模型。分析服務、搜尋索引服務、通知服務可以用不同 group 讀同一 topic — 每個 group 有自己的 [offset](/backend/knowledge-cards/offset/) 進度跟 [consumer lag](/backend/knowledge-cards/consumer-lag/)。

在 Kafka 中，consumer group 是一級概念、由 group coordinator 管理 [partition](/backend/knowledge-cards/partition/) 分配（rebalance）。在 Redis Streams 中對應 consumer group（XREADGROUP）。在 RabbitMQ 中沒有原生 consumer group — 多個 consumer 連到同一個 queue 就是 competing consumers、不同 queue 綁到同一個 exchange 就是 fan-out。

## 使用情境

系統需要 consumer group 的訊號是同一事件要被多個系統各自處理。訂單事件同時給出貨、通知與報表 — 三個 consumer group 各自有自己的處理速度、錯誤率跟重放流程。

Consumer group 的 rebalance（partition 重新分配）是 Kafka 生態的常見運維議題。Consumer 加入或離開 group 時觸發 rebalance、rebalance 期間 partition 暫時無人消費、造成短暫的處理停頓。Rebalance 時間跟 partition 數量、consumer 數量有關。

## 判斷條件與後果

Consumer group 的幾項設定各自決定一種失效的形態。group 名稱沒有跟服務名稱對齊時，告警出現時看不出是哪個服務落後。offset 用 auto-commit 時，offset 可能在 handler 處理完之前就提交，consumer 中斷後那幾筆不會再處理；用 manual commit 時，由程式在處理完成後提交，中斷的代價變成重複處理。rebalance 用 eager 時，每次 consumer 加入或離開，group 內全部 partition 都暫停消費；cooperative 只移動需要重新分配的 partition，停頓的範圍較小。每個 group 的延遲代價不同（通知晚到與出貨延誤），共用同一組 [consumer lag](/backend/knowledge-cards/consumer-lag/) 告警閾值與儀表板時，通知 group 的落後會混進出貨 group 的判讀；[replay runbook](/backend/knowledge-cards/replay-runbook/) 的權限依 group 分開時，重放一個 group 的進度不會動到其他 group。
