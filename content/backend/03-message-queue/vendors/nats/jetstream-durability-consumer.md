---
title: "NATS core 到 JetStream：fire-and-forget 在哪裡不夠、跨過去要付什麼"
date: 2026-06-16
description: "Core NATS 的 fire-and-forget 在 consumer 重啟或 rolling deploy 時掉訊息——這不是 bug、是設計。需要訊息不丟就跨進 JetStream（persistence + at-least-once + redelivery）。本文展開 core 與 JetStream 的邊界、stream 與 consumer 的求值模型、實機驗證的 durable pull consumer、5 個把 JetStream consumer 寫成丟訊息與重投風暴的 production 踩坑"
weight: 11
tags: ["backend", "message-queue", "nats", "jetstream", "consumer", "deep-article"]
---

<!-- TODO(merge): feat/backend_03 worktree 同時在深化 03 vendor overview。本檔是 main 上新增的 deep article、未動 nats/_index.md。合併後須檢查：(1) 與對方主題重複 (2) nats/_index.md 是否加 deep-article 指標 (3) vendors/_index.md 覆蓋表合併。 -->

> 本文是 [NATS](/backend/03-message-queue/vendors/nats/) overview 的 implementation-layer deep article。選型層（NATS vs Kafka / RabbitMQ）見 overview；本文只處理「決定用 NATS 後，core 跟 JetStream 的邊界與 consumer 怎麼設」。JetStream 實機驗證於 nats:latest（-js）、最後檢查日 2026-06-16；機制以 [NATS JetStream 官方文件](https://docs.nats.io/nats-concepts/jetstream) 為準。

## fire-and-forget 在 rolling deploy 那一刻掉訊息

Core NATS 快得驚人，因為它什麼都不記——一則訊息發布出去，當下有訂閱者就送達、沒有就丟棄。沒有儲存、沒有 ack、沒有重送。這對「即時但可丟」的場景（metrics、presence、即時通知）完美：訂閱者暫時離線錯過幾則無所謂，下一則馬上來。

但這個設計有一條清楚的邊界。[Clarifai 用 NATS 跑 ML 模型訓練的非同步任務](/backend/03-message-queue/cases/nats-clarifai-async-task-queue/)，任務從幾秒到幾分鐘，原本同步呼叫——結果每次 rolling deployment（pod 輪流重啟）就掉訊息：訊息發布的瞬間目標 worker 正在重啟，core NATS 找不到訂閱者就丟了。他們的解法是改用 NATS（Streaming / JetStream）的 **at-least-once delivery + redelivery + queue group**，每日 100k+ 訊息做到 100% 不丟。這個案例揭露的邊界是——**ML 長尾任務不能容忍 rolling deploy 掉訊息，core NATS 的 fire-and-forget 到此為止，要跨進 JetStream。**

JetStream 在 core NATS 之上加了一層持久化的 stream + 可重送的 consumer。本文處理這條邊界：什麼時候 core 夠用、什麼時候要 JetStream、跨過去的 consumer 模型怎麼設才不會丟訊息或重投風暴。

## 核心概念：stream 與 consumer 的求值模型

JetStream 把「訊息儲存」跟「消費進度」拆成兩個獨立物件——stream（存什麼、留多久）跟 consumer（誰讀、怎麼 ack）。理解 JetStream 就是理解這兩者。

**stream 決定訊息怎麼被儲存與保留**。一個 stream 綁定一組 subject、把符合的訊息持久化。三個關鍵維度：storage（`file` 持久 / `memory` 重啟即失）、retention（`limits` 依大小/時間/數量保留、`workqueue` 消費後即刪、`interest` 有訂閱者才留）、limits（max-msgs / max-bytes / max-age）。retention 選錯是常見陷阱——`workqueue` 是「每則訊息只被一個 consumer 消費一次就刪」，`limits` 是「保留著、多個 consumer 各自讀」。

**consumer 是 stream 上的一個可重播視圖**。同一個 stream 可以有多個 consumer，各自維護自己的消費位置。consumer 的關鍵屬性：

- push vs pull：push 由 server 主動推給訂閱者；pull 由 client 主動拉（`consumer next`），pull 對流量控制與 worker pool 更可控
- durable vs ephemeral：durable consumer 的進度持久（重啟後從上次位置續讀），ephemeral 在 client 斷線後消失（進度丟失）
- ack policy：`explicit`（每則都要 ack、at-least-once 的基礎）/ `all`（ack 一則等於 ack 之前所有）/ `none`（不需 ack、近似 fire-and-forget）
- max_deliver + ack_wait：沒 ack 的訊息在 `ack_wait` 後重送，最多 `max_deliver` 次

**at-least-once 來自「explicit ack + redelivery」**。consumer 取出訊息、處理、明確 ack；沒 ack（處理失敗或 crash）的訊息在 ack_wait 逾時後重送。這就是 Clarifai 要的「rolling deploy 不丟訊息」——worker 重啟時沒 ack 的任務會被重送給其他 worker。

## 配置：durable pull consumer（實機驗證）

```bash
# 啟動 JetStream（server 加 -js）
# docker run -d --name nats nats:latest -js

# 1. 建 stream：file storage、limits retention
nats stream add ORDERS --subjects "orders.>" --storage file --defaults
#   Subjects: orders.>   Storage: File   Retention: Limits   Replicas: 1

# 2. publish
nats pub orders.new "order-1"   # Published 7 bytes to "orders.new"

# 3. stream info 確認持久化
nats stream info ORDERS
#   Storage: File   Messages: 3   Bytes: 141 B   ← 訊息已落盤、consumer 重啟不丟

# 4. durable pull consumer（explicit ack、可重送）
nats consumer add ORDERS workers --pull --ack explicit --deliver all --defaults
#   Pull Mode: true   Ack Policy: Explicit

# 5. 拉取消費（worker pool 多個實例共用同一 durable consumer = queue group 語意）
nats consumer next ORDERS workers --count 3
#   order-1  order-2  order-3
```

實機驗證於 nats:latest（最後檢查日 2026-06-16）：file storage 的 stream 把訊息落盤（Messages: 3）、durable pull consumer 用 explicit ack 消費。多個 worker 連到同一個 durable pull consumer 形成 worker pool（訊息分給其中一個），這正是 Clarifai 的 queue group 模式。

判讀：

- worker pool 用同一個 durable pull consumer（共享進度、訊息分流），不是每個 worker 一個 consumer
- `--ack explicit` 是 at-least-once 的前提；處理成功才 ack
- pull 模式比 push 對 worker pool 更可控（worker 按自己能力拉、不會被 push 淹）

## Production 故障演練

### Case 1：用 core NATS 跑該持久的任務、rolling deploy 掉訊息

**徵兆**：平時正常，但每次部署（pod 輪流重啟）就有一批任務消失、沒有錯誤。

**根因**：用 core NATS（fire-and-forget）跑需要可靠處理的任務。發布瞬間目標訂閱者正在重啟，core NATS 找不到訂閱者就丟棄——這是 core 的設計，不是故障。正是 [Clarifai 的原始問題](/backend/03-message-queue/cases/nats-clarifai-async-task-queue/)。

**修法**：

1. 需要不丟的任務用 JetStream（持久 stream + durable consumer + explicit ack）
2. 訊息落盤後 consumer 重啟從上次位置續讀，rolling deploy 不丟
3. 釐清邊界：可丟的即時資料（metrics / presence）留 core NATS、不可丟的跨 JetStream
4. 不要用 core NATS 當任務隊列——它沒有持久化與重送

### Case 2：ephemeral consumer 斷線、消費進度全丟

**徵兆**：consumer 重連後從頭重讀整個 stream、或漏掉斷線期間的訊息，進度不連續。

**根因**：用了 ephemeral consumer——它的進度不持久，client 斷線後 consumer 本身消失。重連是建一個全新 consumer，從 `deliver` policy 的起點開始（all 從頭、new 只看新的），不接續之前的進度。

**修法**：

1. 需要跨重啟接續的用 durable consumer（具名、進度持久）
2. ephemeral 只適合臨時、一次性的讀取（debug、一次性掃描）
3. worker pool 一定用 durable（多 worker 共享持久進度）
4. 確認 `deliver` policy（all / new / last）符合預期的起讀位置

### Case 3：ack_wait 太短、處理還沒完就重送風暴

**徵兆**：長任務還在處理中就被重送給另一個 worker，同一任務被多個 worker 重複執行，負載放大。

**根因**：`ack_wait`（等 ack 的逾時）設得比任務處理時間短。JetStream 以為訊息處理失敗（沒在 ack_wait 內 ack），重送給別人——但其實第一個 worker 還在跑。ML 長尾任務（幾秒到幾分鐘）特別容易踩。

**修法**：

1. `ack_wait` 設成大於任務的 p99 處理時間，留足處理窗口
2. 長任務用 `in-progress ack`（處理中定期發 working ack 延長 deadline），不必一開始就設超長 ack_wait
3. 消費端冪等——at-least-once 本來就可能重送，重複執行不該產生重複副作用（見 [6.12 idempotency](/backend/06-reliability/idempotency-replay/)）
4. 監控 redelivery 次數，異常高代表 ack_wait 太短或處理卡住

### Case 4：retention 選 workqueue 但想多 consumer fanout

**徵兆**：想讓多個獨立服務各自消費同一 stream，但發現訊息被一個消費掉就消失、其他服務讀不到。

**根因**：stream retention 設成 `workqueue`——每則訊息只被消費一次就從 stream 刪除（隊列語意）。它不適合 fanout（多個 consumer 各自要完整一份）。fanout 要 `limits` 或 `interest` retention。

**修法**：

1. fanout（多服務各讀一份）用 `limits` retention（訊息保留、多 consumer 各自 offset）
2. 單一 worker pool 競爭消費用 `workqueue`（消費即刪、省空間）
3. 釐清需求：競爭消費（worker pool）vs 廣播消費（fanout）對應不同 retention
4. Clarifai 用「3 個獨立 NATS 實例做 fanout 隔離」是另一種 fanout 做法，按隔離需求選

### Case 5：memory storage 的 stream 重啟全失

**徵兆**：broker 重啟後 stream 裡的訊息全沒了，consumer 從空的開始。

**根因**：stream storage 設成 `memory`——快但不持久，broker 重啟即失。誤把它當持久 stream 用。

**修法**：

1. 需要持久的 stream 用 `file` storage（落盤、重啟不丟，實機驗證過）
2. `memory` 只適合「快取式、可重建」的 stream（如即時聚合的中間狀態）
3. 要更高可靠性加 `replicas`（JetStream 用 Raft 跨節點複製 stream）
4. 容量規劃時 file storage 的磁碟與 memory 的 RAM 是不同維度

## Capacity / cost 邊界

JetStream 的容量判讀：

| 訊號                 | 健康區間                  | 警戒與動作                                    |
| -------------------- | ------------------------- | --------------------------------------------- |
| stream storage 用量  | 在 max-bytes / max-age 內 | 接近上限 → 訊息被 discard、調 limits 或加容量 |
| redelivery 次數      | 低（多數一次 ack 成功）   | 高 → ack_wait 太短或處理卡住                  |
| consumer pending     | 可消化                    | 持續堆高 → consumer 跟不上 producer           |
| ack_wait vs 處理時間 | ack_wait > p99 處理時間   | 反了 → 重送風暴                               |
| storage 型別         | 持久需求用 file           | 誤用 memory → 重啟丟訊息                      |

撞牆後的路由判斷：

- **可丟的即時資料**：不需要 JetStream 的持久化開銷，用 core NATS（更快更輕）。
- **超大吞吐 + 長期保留 + 複雜 replay**：JetStream 適合中等規模可靠 messaging；超大規模 event streaming + 長期保留走 [Kafka](/backend/03-message-queue/vendors/kafka/)（log-based、生態成熟）。
- **複雜 routing / 任務隊列語意**：JetStream 的 subject 是樹狀，複雜 routing + DLQ 拓樸用 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) 更直接。
- **不想自管**：NATS 的 managed 選項（Synadia Cloud）或其他 managed broker。

## 整合 / 下一步

JetStream 的邊界判斷是 NATS 使用的核心，它跟其他議題交織：

- **跟 [3.4 consumer design](/backend/03-message-queue/consumer-design/)**：push/pull、durable/ephemeral、ack policy 是 consumer 設計的具體選項。
- **跟 [3.2 durable queue](/backend/03-message-queue/durable-queue/)**：JetStream 的 file storage stream 是 NATS 的 durable queue 實現。
- **跟 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)**：at-least-once + redelivery 要求消費冪等，否則重送造成重複副作用。
- **跟 [RabbitMQ DLQ deep article](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)**：max_deliver 達上限後的處理對應 RabbitMQ 的 DLQ，兩者都是「重試上限後往哪去」的問題。

## 相關連結

- 上游 vendor 頁：[NATS](/backend/03-message-queue/vendors/nats/)
- 對照 vendor：[RabbitMQ DLQ 與分層 retry](/backend/03-message-queue/vendors/rabbitmq/dlq-retry-escalation/)、[Kafka](/backend/03-message-queue/vendors/kafka/)
- 對應案例：[3.C38 Clarifai NATS ML 非同步任務](/backend/03-message-queue/cases/nats-clarifai-async-task-queue/)
- 上游概念：[3.4 consumer design](/backend/03-message-queue/consumer-design/)、[3.2 durable queue](/backend/03-message-queue/durable-queue/)
