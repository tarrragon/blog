---
title: "Poison-Message Quarantine"
date: 2026-06-16
description: "說明把毒訊息從主處理路徑隔離出來的機制，讓正常訊息繼續前進"
weight: 382
---

Poison-message quarantine 的核心概念是「把穩定造成失敗的訊息從主處理路徑移開」。它是對 [poison message](/backend/knowledge-cards/poison-message/) 這個現象的處置：用投遞次數上限把壞訊息送進隔離區，讓正常訊息繼續前進。 可先對照 [Poison Message](/backend/knowledge-cards/poison-message/)。

## 概念位置

Poison-message quarantine 是 [poison message](/backend/knowledge-cards/poison-message/)（現象）與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)（隔離區）之間的機制層。它靠 max delivery / maxReceiveCount 計數，超過門檻就把訊息移出主 queue，後續走 [DLQ drain](/backend/knowledge-cards/dlq-drain/) 修復或歸檔。

## 可觀察訊號與例子

同一訊息 redelivery 次數持續累加而從不成功，就是隔離訊號。SQS 用 redrive policy 的 maxReceiveCount、RabbitMQ 用 DLX + 投遞計數、Kafka 多半在 consumer 端自行計數後送隔離 topic。沒有隔離機制時，一則毒訊息會卡住整個 partition 或 queue。

## 設計責任

設計時把投遞次數上限設在「足夠容忍暫時性失敗、又不會無限重試」之間，並在隔離時保留原始 payload 與失敗原因，讓後續診斷與 drain 有足夠證據。
