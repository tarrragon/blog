---
title: "Ack / Nack"
date: 2026-04-23
description: "說明 consumer 如何向 broker 回報訊息處理結果"
weight: 23
---

Ack / nack 的核心概念是「[consumer](/backend/knowledge-cards/consumer/) 對 [broker](/backend/knowledge-cards/broker/) 回報訊息處理結果」。Ack 表示訊息已完成處理，可以從待處理集合移除；nack 或 reject 表示處理未完成，需要 [retry policy](/backend/knowledge-cards/retry-policy/)、[requeue](/backend/knowledge-cards/requeue/) 或送進 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)。

## 概念位置

Ack / nack 是投遞保證的關鍵協議。Consumer crash、網路中斷或 ack timeout 都可能讓 broker 判斷訊息尚未完成，進而 [redelivery](/backend/knowledge-cards/redelivery/)。

## 可觀察訊號與例子

系統需要理解 ack / nack 的訊號是訊息重複、[queue depth](/backend/knowledge-cards/queue-depth/) 上升或 [unacked message](/backend/knowledge-cards/unacked-message/) 累積。影片轉檔 worker 若在完成前 crash，訊息應重新投遞；若已產生外部副作用，consumer 需要 [idempotency](/backend/knowledge-cards/idempotency/) 保護。

## 設計責任

Consumer 要明確決定何時 ack。通常應在業務處理與必要狀態保存完成後 ack；永久性錯誤要分類送往 dead-letter queue；暫時性錯誤要搭配 retry policy、[exponential backoff](/backend/knowledge-cards/exponential-backoff/) 與 [jitter](/backend/knowledge-cards/jitter/)。
