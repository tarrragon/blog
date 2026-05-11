---
title: "3.6 Processing Semantics 與 Recovery Semantics"
date: 2026-05-11
description: "說明投遞成功、處理成功與恢復成功為何是三個不同判斷。"
weight: 6
tags: ["backend", "message-queue", "semantics", "recovery"]
---

Processing semantics 與 recovery semantics 的核心責任是把訊息送達、業務副作用完成、故障後可恢復三件事分開判斷。進入 Kafka、RabbitMQ、SQS、NATS 或 Redis Streams 前，讀者需要先知道 broker 保證主要落在傳遞語意的一部分。

## Delivery / Processing / Recovery

三層語意的責任不同：

| 語意層               | 負責問題                                      | 主要訊號                           |
| -------------------- | --------------------------------------------- | ---------------------------------- |
| Delivery semantics   | 訊息是否被 broker 投遞、確認、重送或隔離      | ack、nack、redelivery、DLQ         |
| Processing semantics | consumer 副作用是否能承受重複、亂序與部分失敗 | idempotency、side effect、ordering |
| Recovery semantics   | 故障後是否能重播、補償與恢復一致              | replay、checkpoint、reconciliation |

[delivery semantics](/backend/knowledge-cards/delivery-semantics/) 成立不代表 processing 成立。訊息被 ack 也不代表發票、email、search index 或 webhook 都已完成。

Delivery 層的判讀重點是 broker 是否還能掌握訊息位置。Processing 層的判讀重點是 consumer 是否已經完成業務副作用。Recovery 層的判讀重點是事故後能否用 replay、checkpoint 與 reconciliation 回到一致狀態。這三層拆開後，隊列工具選型才會對到真正問題。

## Processing Semantics

Processing semantics 的責任是讓 consumer 副作用在重複投遞與部分失敗下仍可控。常見副作用包含寫資料庫、呼叫外部 API、寄信、建立發票、更新 search index。

每個副作用都要先回答：

1. idempotency key 是什麼。
2. 副作用完成後如何記錄。
3. 重複執行時結果是否穩定。
4. 部分成功時如何補償。

缺少這些答案時，at-least-once delivery 會轉成多次業務結果。

## Recovery Semantics

Recovery semantics 的責任是讓系統在 consumer crash、DLQ 爆量、下游故障或資料修復後能恢復一致。它依賴 replay window、checkpoint、offset、去重紀錄與對帳查詢。

恢復流程要先分範圍。按時間、tenant、partition、schema version 或 event type 分段，能降低 replay 造成的下游壓力與重複副作用。

## Checkpoint 與 Side Effect

[checkpoint](/backend/knowledge-cards/checkpoint/) 的責任是標記處理進度，業務完成則要由副作用紀錄與對帳證據證明。若 checkpoint 早於副作用提交，consumer crash 後可能漏做副作用；若 checkpoint 太晚，重啟後會造成重複處理。

穩定設計通常讓副作用具備 idempotency，再把 checkpoint 放在可恢復的位置。checkpoint 與 idempotency 是一組設計，需要一起審查。

## 選型前判準

Queue 選型前要先回答：

1. 需要保證的是投遞、處理還是恢復。
2. 哪些副作用必須 idempotent。
3. 哪些事件需要順序，順序邊界是全域、tenant、entity 還是 partition。
4. Replay 時下游能承受多少吞吐。
5. DLQ 是診斷入口還是已經變成長期倉庫。

這些答案會決定後續比較 Kafka、RabbitMQ、SQS、NATS 或 Redis Streams 時該看哪些能力。

## 實體服務討論承接點

實體 queue/broker 文章要承接本篇的 processing 與 recovery semantics。Kafka、RabbitMQ、SQS、NATS 或 Redis Streams 的比較，應先問服務需要什麼投遞、處理與恢復責任，再比較 topic、queue、partition、consumer group、DLQ 或 retention。

若主問題是高吞吐事件流，後續文章要比較 partition、retention、consumer lag 與 replay 能力。若主問題是工作派發，後續文章要比較 ack/nack、routing、DLQ 與 retry。若主問題是受管服務操作成本，後續文章要比較可觀測性、IAM、區域能力與 failure mode。

## 下一步路由

要建立 broker 投遞模型，接著讀 [3.1 broker 基礎與投遞模型](/backend/03-message-queue/broker-basics/)。要把三層語意放進完整服務路徑，接著讀 [3.8 Queue Consumer Retry 與 Replay Handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/)。
