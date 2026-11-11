---
title: "Consumer"
date: 2026-06-22
description: "說明 consumer 如何取得等待處理的工作並產生業務結果"
weight: 134
tags: ["backend", "message-queue"]
---

Consumer 的核心概念是「從等待區取得工作、事件或資料並執行處理的角色」。這張卡講的是訊息佇列側的角色；對外 API 契約另一端的那種「消費者」是同名異義，見 [API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/)。它可以從 [queue](/backend/knowledge-cards/queue/)、[broker](/backend/knowledge-cards/broker/)、[stream pipeline](/backend/knowledge-cards/stream-pipeline/)、[database](/backend/knowledge-cards/database/) table 或 [in-process channel](/backend/knowledge-cards/in-process-channel/) 取得資料，再更新狀態、呼叫外部服務或產生衍生資料。

## 跟其他概念的關係

Consumer 位在資料流的下游。它跟 [producer](/backend/knowledge-cards/producer/) 構成 MQ 的基本角色對 — producer 負責把工作送進等待區，consumer 負責取出並處理。

多個 consumer 組成 [consumer group](/backend/knowledge-cards/consumer-group/) 來分攤處理負載。Consumer 的處理速度跟錯誤行為直接影響 [consumer lag](/backend/knowledge-cards/consumer-lag/)（積壓深度）跟 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)（無法處理的訊息去處）。

## 使用情境

系統需要辨識 consumer 的訊號是資料已經送入系統但產品結果還沒完成。付款事件送入後，入帳 consumer 要更新帳務狀態；通知事件送入後，寄信 consumer 要呼叫郵件服務。兩者都要清楚記錄處理成功、暫時失敗與永久拒絕。

Consumer 的處理模式影響系統的可靠性保證。[Ack / nack](/backend/knowledge-cards/ack-nack/) 的時機決定「訊息什麼時候算處理完成」；[idempotency](/backend/knowledge-cards/idempotency/) 決定「重複收到同一筆訊息時是否會產生副作用」。

## 判斷條件與後果

Consumer 的每一項處理設定缺席時，故障的形態不同：併發數沒有上限時，consumer 送往下游的請求超過下游容量；[ack / nack](/backend/knowledge-cards/ack-nack/) 在處理完成之前就 ack 時，處理失敗的訊息不會再投遞；錯誤不分暫時性與永久性時，永久失敗的訊息被反覆重試，佔住處理能力；沒有 [idempotency](/backend/knowledge-cards/idempotency/) 時，重複投遞產生重複的副作用；沒有 [retry policy](/backend/knowledge-cards/retry-policy/) 時，重試沒有次數上限與間隔；沒有隔離區時，處理不了的訊息擋住後面的訊息；沒有 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/) 時，部署時正在處理的訊息被中斷；沒有觀測欄位時，以上任何一種發生了都看不到。

操作面的觀測欄位各自對應上面的故障：處理速率（messages/sec）與 [consumer lag](/backend/knowledge-cards/consumer-lag/) 反映容量，失敗類型分布反映錯誤分類是否有效，oldest unprocessed message age 與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 累積量反映有沒有訊息卡住，下游 dependency latency 分辨慢在 consumer 還是下游。Consumer lag 持續增長時，代表處理能力低於進入速度，是容量不足的 leading indicator。
