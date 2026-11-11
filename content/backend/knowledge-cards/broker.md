---
title: "Broker"
date: 2026-04-23
description: "說明 broker 在訊息傳遞系統中負責保存、路由與交付訊息"
weight: 2
---

Broker 的核心概念是「位於 [producer](/backend/knowledge-cards/producer/) 與 [consumer](/backend/knowledge-cards/consumer/) 之間的訊息中介」。Producer 把工作或事件交給 broker，broker 依照 [topic](/backend/knowledge-cards/topic/)、[queue](/backend/knowledge-cards/queue/)、[routing rule](/backend/knowledge-cards/routing-rule/) 或 stream position 保存與分派訊息，consumer 再從 broker 取得訊息並處理。

## 跟其他概念的關係

Broker 把「送出訊息」與「處理訊息」分開。這個分離讓 request 可以先完成，背景工作可以稍後處理，也讓多個服務用同一個事件來源協作。RabbitMQ、Kafka、NATS JetStream、Redis Streams 都可以扮演 broker，但它們對 routing、持久化、順序、[replay](/backend/knowledge-cards/replay-runbook/) 與 consumer 協調的模型不同。

## 可觀察訊號

系統需要 broker 的訊號是工作已經超出單一 request 或單一 process 的生命週期。常見訊號包括寄信、轉檔、通知、同步外部系統、資料匯入、事件審計與跨服務廣播。這些工作需要排隊、[retry policy](/backend/knowledge-cards/retry-policy/)、削峰或讓多個 consumer 分工處理。

## 接近真實網路服務的例子

電商付款完成後，訂單服務可以把 `OrderPaid` 事件交給 broker。寄信服務處理通知，倉儲服務處理出貨，分析服務處理報表。這些 consumer 的速度、失敗與部署週期彼此不同，broker 讓事件先被保存，再由各 consumer 依自己的節奏處理。

## 判斷條件與後果

Broker 導入後，訊息送出去之後的處理過程能不能被追蹤、恢復與控制，取決於幾項定義是否齊全，每缺一項就有一種失敗沒有人接手。訊息格式沒有定義時，producer 改一個欄位，所有 consumer 在下一次解析時失敗；投遞保證沒有寫明時，consumer 判斷不了是否要處理重複送達的訊息；沒有 [retry policy](/backend/knowledge-cards/retry-policy/) 與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 時，處理失敗的訊息不是反覆重試佔住 consumer，就是被丟棄而沒有紀錄；沒有 [consumer lag](/backend/knowledge-cards/consumer-lag/) 告警時，consumer 落後要等使用者發現通知延遲才被看到；沒有權限控制時，任何服務都能往同一個 topic 寫入或讀出；沒有 [replay runbook](/backend/knowledge-cards/replay-runbook/) 時，consumer 修好之後，從哪個位置重放、重放哪些訊息只能在事故當下臨時決定。
