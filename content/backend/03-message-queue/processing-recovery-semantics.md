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

## Poison Message 的處理層次

Poison message 是無法被 consumer 正確處理、但會持續觸發 retry 的訊息。處理流程要從 *偵測 / 隔離 / 診斷 / 修復* 四個層次設計、不只是「丟進 DLQ」。

對應 [3.C9 反例：Queue Semantics Mismatch](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) — DLQ 激增且重播後仍回到相同錯誤、是 poison message 沒被正確處理的訊號。consumer lag 下降但業務結果沒收斂、表示 poison message 把 consumer 卡住。

**四個處理層次**：

- **偵測**：retry count 超過閾值（通常 3-5 次）後識別為 poison candidate。早期偵測訊號是 retry rate 升高但 success rate 沒同步上升、單一 consumer 反覆失敗
- **隔離**：把 poison message 移出主通道、進 DLQ 或 quarantine queue。隔離要 *即時*、不等批次、否則持續占用主通道吞吐
- **診斷**：DLQ 內 poison message 要分群分析、找出共同 failure pattern（payload schema 不符、外部 API 永久失敗、邏輯 bug）。對應 [3.C10 對照](/backend/03-message-queue/cases/contrast-queue-model-by-scale/) — 大型服務的 DLQ 是診斷入口
- **修復**：依據 root cause 修 consumer / contract / 邏輯後、定向回放 DLQ 內 poison message。沒修就重播會讓同一 message 再次進 DLQ、形成 zombie cycle

判讀重點：DLQ size 持續增加但沒有對應修復 commit、表示處理流程斷在「隔離」這層、沒進「診斷 / 修復」。release gate 要加「DLQ 排空速率 >= 流入速率」的條件、避免 DLQ 變長期倉庫。

## Replay 跟 Idempotency 的共設計

Replay safety 跟 idempotency 必須在同一個設計階段一起決定、無法事後補。replay window 設多大、idempotency key 怎麼定、checkpoint 何時提交、三者互相影響、任一改動都會破壞其他。

**共設計的判讀順序**：

1. **先定 idempotency key**：什麼欄位組合能唯一標記副作用（event_id、entity_id + version、business operation id）
2. **再定 idempotency 儲存策略**：去重紀錄存多久（決定 replay window 上限）、儲存在 cache / DB / 應用層 memory
3. **依儲存策略反推 replay window**：去重紀錄保留 7 天、replay window 上限就是 7 天、超過會出現重複副作用
4. **再依 replay window 反推 checkpoint 策略**：checkpoint 落地時機要保證 crash 後 replay window 內可恢復

對應 [9.C9 Spotify Kafka → Pub/Sub](/backend/09-performance-capacity/cases/spotify-kafka-to-pubsub-migration-gcp/) — broker 遷移要驗證業務語意跟新 broker 兼容、replay 模型在 Kafka（offset）跟 Pub/Sub（snapshot + seek）不同、idempotency 策略要重新校準。

判讀重點：replay window 是 idempotency 儲存策略反推出來的、不是 broker 設定值。先看 idempotency key 跟去重儲存、再決定 replay window 安全範圍。順序顛倒會踩到「replay 跨越去重紀錄到期」的事故、表現是 replay 後出現本來該被去重的重複副作用。

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
