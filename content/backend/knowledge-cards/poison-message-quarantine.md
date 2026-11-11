---
title: "Poison-Message Quarantine"
date: 2026-06-16
description: "說明把毒訊息從主處理路徑隔離出來的機制，讓正常訊息繼續前進"
weight: 383
---

Poison-message quarantine 的核心概念是「把穩定造成失敗的訊息從主處理路徑移開」。它是對 [poison message](/backend/knowledge-cards/poison-message/) 這個現象的處置：用投遞次數上限把壞訊息送進隔離區，讓正常訊息繼續前進。 可先對照 [Poison Message](/backend/knowledge-cards/poison-message/)。

## 跟其他概念的關係

Poison-message quarantine 是 [poison message](/backend/knowledge-cards/poison-message/)（現象）與 [dead-letter queue](/backend/knowledge-cards/dead-letter-queue/)（隔離區）之間的機制層。它靠 max delivery / maxReceiveCount 計數，超過門檻就把訊息移出主 queue，後續走 [DLQ drain](/backend/knowledge-cards/dlq-drain/) 修復或歸檔。

## 可觀察訊號與例子

同一訊息 redelivery 次數持續累加而從不成功，就是隔離訊號。SQS 用 redrive policy 的 maxReceiveCount、RabbitMQ 用 DLX + 投遞計數、Kafka 多半在 consumer 端自行計數後送隔離 topic。沒有隔離機制時，一則毒訊息會卡住整個 partition 或 queue。

## 判斷條件與後果

投遞次數上限決定一則訊息失敗幾次之後被移出主處理路徑。上限太低時，遇到暫時性失敗（下游短暫逾時）的訊息還沒等到重試成功就被隔離，本來能處理的訊息進了隔離區，要靠 drain 送回；上限太高或沒有上限時，一則毒訊息反覆重投，卡住整個 partition 或 queue。隔離時只移走訊息、沒有保留原始 payload 與失敗原因時，[DLQ drain](/backend/knowledge-cards/dlq-drain/) 拿不到判斷這則訊息該修復重送還是歸檔的證據。
