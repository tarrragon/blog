---
title: "Consumer"
date: 2026-06-22
description: "說明 consumer 如何取得等待處理的工作並產生業務結果"
weight: 133
tags: ["backend", "message-queue"]
---

Consumer 的核心概念是「從等待區取得工作、事件或資料並執行處理的角色」。它可以從 [queue](/backend/knowledge-cards/queue/)、[broker](/backend/knowledge-cards/broker/)、[stream pipeline](/backend/knowledge-cards/stream-pipeline/)、[database](/backend/knowledge-cards/database/) table 或 [in-process channel](/backend/knowledge-cards/in-process-channel/) 取得資料，再更新狀態、呼叫外部服務或產生衍生資料。

## 概念位置

Consumer 位在資料流的下游。它跟 [producer](/backend/knowledge-cards/producer/) 構成 MQ 的基本角色對 — producer 負責把工作送進等待區，consumer 負責取出並處理。

多個 consumer 組成 [consumer group](/backend/knowledge-cards/consumer-group/) 來分攤處理負載。Consumer 的處理速度跟錯誤行為直接影響 [consumer lag](/backend/knowledge-cards/consumer-lag/)（積壓深度）跟 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)（無法處理的訊息去處）。

## 使用情境

系統需要辨識 consumer 的訊號是資料已經送入系統但產品結果還沒完成。付款事件送入後，入帳 consumer 要更新帳務狀態；通知事件送入後，寄信 consumer 要呼叫郵件服務。兩者都要清楚記錄處理成功、暫時失敗與永久拒絕。

Consumer 的處理模式影響系統的可靠性保證。[Ack / nack](/backend/knowledge-cards/ack-nack/) 的時機決定「訊息什麼時候算處理完成」；[idempotency](/backend/knowledge-cards/idempotency/) 決定「重複收到同一筆訊息時是否會產生副作用」。

## 設計責任

Consumer 要定義併發數、[ack / nack](/backend/knowledge-cards/ack-nack/) 條件、錯誤分類（暫時性 vs 永久性）、[idempotency](/backend/knowledge-cards/idempotency/)、[retry policy](/backend/knowledge-cards/retry-policy/)、隔離區、[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 與觀測欄位。

操作面要能觀測：處理速率（messages/sec）、失敗類型分布、oldest unprocessed message age、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 累積量與下游 dependency latency。Consumer lag 持續增長是容量不足的 leading indicator。
