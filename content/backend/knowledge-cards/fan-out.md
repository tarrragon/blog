---
title: "Fan-out"
date: 2026-06-22
description: "說明單一事件同時分發給多個下游的訊息拓撲"
weight: 141
tags: ["backend", "message-queue"]
---

Fan-out 的核心概念是「一個事件被多個訂閱者各自獨立處理」。它讓單一 [producer](/backend/knowledge-cards/producer/) 發布一次事件，多個下游各自消費、各自處理、各自管理進度跟錯誤。

## 概念位置

Fan-out 常搭配 [pub/sub](/backend/knowledge-cards/pub-sub/) 模型、[topic](/backend/knowledge-cards/topic/) 跟 [consumer group](/backend/knowledge-cards/consumer-group/) 實作。在 Kafka 中，多個 consumer group 訂閱同一個 topic 就是 fan-out — 每個 group 各自從 [offset](/backend/knowledge-cards/offset/) 0 開始消費。在 RabbitMQ 中，fanout exchange 把訊息複製到所有綁定的 queue。在 GCP Pub/Sub 中，多個 subscription 訂閱同一個 topic。

Fan-out 跟 fan-in（多個來源合併成一個流）是相反的拓撲。兩者可以組合成事件處理管線。

## 使用情境

`order.paid` 事件同時觸發出貨準備（物流服務）、交易通知（通知服務）、營收紀錄（報表服務）與風控評估（風控服務）。Producer 不需要知道有哪些 consumer — 加減 consumer 不影響 producer 的程式碼。

Fan-out 降低了 producer 跟 consumer 之間的耦合，但擴大了排障範圍 — 一筆事件的處理結果散落在多個 consumer，需要用 [trace context](/backend/knowledge-cards/trace-context/) 或 correlation id 串連。

## 設計責任

設計 fan-out 時要為每個訂閱者定義可靠性等級跟回復策略。通知服務短暫失敗可以 retry；報表服務落後可以批次追補；但出貨服務的失敗可能需要人工介入。把所有下游綁成同一個失敗域（一個 consumer 卡住就全部暫停）會讓 fan-out 的解耦價值消失。每個 consumer group 應該獨立管理 [consumer lag](/backend/knowledge-cards/consumer-lag/)、[dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 跟 [replay runbook](/backend/knowledge-cards/replay-runbook/)。
