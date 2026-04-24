---
title: "Consumer"
date: 2026-04-23
description: "說明 consumer 如何取得等待處理的工作並產生業務結果"
weight: 133
---

Consumer 的核心概念是「從等待區取得工作、事件或資料並執行處理的角色」。它可以從 [queue](/backend/knowledge-cards/queue/)、[broker](/backend/knowledge-cards/broker/)、[stream pipeline](/backend/knowledge-cards/stream-pipeline/)、[database](/backend/knowledge-cards/database/) table 或 [in-process channel](/backend/knowledge-cards/in-process-channel/) 取得資料，再更新狀態、呼叫外部服務或產生衍生資料。

## 概念位置

Consumer 位在資料流的下游。它的處理速度、錯誤分類與副作用控制會影響 [consumer lag](/backend/knowledge-cards/consumer-lag/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)、[retry policy](/backend/knowledge-cards/retry-policy/) 與 [replay runbook](/backend/knowledge-cards/replay-runbook/)。

## 可觀察訊號與例子

系統需要辨識 consumer 的訊號是資料已經送入系統，但產品結果還沒有完成。付款事件送入後，入帳 consumer 要更新帳務狀態；通知事件送入後，寄信 consumer 要呼叫郵件服務。兩者都要清楚記錄處理成功、暫時失敗與永久拒絕。

## 設計責任

Consumer 要定義併發數、[ack / nack](/backend/knowledge-cards/ack-nack/) 條件、錯誤分類、[idempotency](/backend/knowledge-cards/idempotency/)、[retry policy](/backend/knowledge-cards/retry-policy/)、隔離區、[graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 與觀測欄位。操作上要能看到處理速率、失敗類型、oldest item age、[consumer lag](/backend/knowledge-cards/consumer-lag/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 數量與下游 latency。
