---
title: "Broker"
date: 2026-04-23
description: "說明 broker 在訊息傳遞系統中負責保存、路由與交付訊息"
weight: 1
---


Broker 的核心概念是「位於 [producer](/backend/knowledge-cards/producer/) 與 [consumer](/backend/knowledge-cards/consumer/) 之間的訊息中介」。Producer 把工作或事件交給 broker，broker 依照 [topic](/backend/knowledge-cards/topic/)、[queue](/backend/knowledge-cards/queue/)、[routing rule](/backend/knowledge-cards/routing-rule/) 或 stream position 保存與分派訊息，consumer 再從 broker 取得訊息並處理。

## 概念位置

Broker 把「送出訊息」與「處理訊息」分開。這個分離讓 request 可以先完成，背景工作可以稍後處理，也讓多個服務用同一個事件來源協作。RabbitMQ、Kafka、NATS JetStream、Redis Streams 都可以扮演 broker，但它們對 routing、持久化、順序、[replay](/backend/knowledge-cards/replay-runbook/) 與 consumer 協調的模型不同。

## 可觀察訊號

系統需要 broker 的訊號是工作已經超出單一 request 或單一 process 的生命週期。常見訊號包括寄信、轉檔、通知、同步外部系統、資料匯入、事件審計與跨服務廣播。這些工作需要排隊、[retry policy](/backend/knowledge-cards/retry-policy/)、削峰或讓多個 consumer 分工處理。

## 接近真實網路服務的例子

電商付款完成後，訂單服務可以把 `OrderPaid` 事件交給 broker。寄信服務處理通知，倉儲服務處理出貨，分析服務處理報表。這些 consumer 的速度、失敗與部署週期彼此不同，broker 讓事件先被保存，再由各 consumer 依自己的節奏處理。

## 設計責任

Broker 導入後，系統要明確定義訊息格式、投遞保證、[retry policy](/backend/knowledge-cards/retry-policy/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)、[consumer lag](/backend/knowledge-cards/consumer-lag/) 告警、權限與 [replay runbook](/backend/knowledge-cards/replay-runbook/)。設計焦點是把「訊息送出去」升級成「訊息可追蹤、可恢復、可控制地被處理」。
