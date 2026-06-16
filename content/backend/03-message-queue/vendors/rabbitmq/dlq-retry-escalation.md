---
title: "RabbitMQ DLQ 與分層 retry：別把失敗訊息 requeue 回隊首"
date: 2026-06-16
description: "RabbitMQ 處理失敗訊息最常見的錯是直接 requeue 回原隊列——它回到隊首、反覆失敗、把後面的訊息全卡住（head-of-line blocking）。正解是用 dead-letter exchange + TTL 組出 work → delay → DLQ 的分層 escalation。本文展開 DLX 求值模型、實機驗證的三層拓樸、5 個把 retry 寫成無限迴圈與隊列阻塞的 production 踩坑，以及 retry 拓樸的容量邊界"
weight: 11
tags: ["backend", "message-queue", "rabbitmq", "dlq", "retry", "deep-article"]
---

<!-- TODO(merge): feat/backend_03 worktree 同時在深化 03 vendor overview。本檔是 main 上新增的 deep article、未動 rabbitmq/_index.md。合併 feat/backend_03 後須檢查：(1) 本檔與對方是否有重複主題 (2) rabbitmq/_index.md 是否該加本檔的 deep-article 指標 (3) vendors/_index.md 覆蓋表合併。 -->

> 本文是 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) overview 的 implementation-layer deep article。選型層（RabbitMQ vs Kafka / SQS、何時選 RabbitMQ）見 overview；本文只處理「決定用 RabbitMQ 後，失敗訊息怎麼 retry 才不會卡死隊列」。DLX 拓樸實機驗證於 rabbitmq:3-management、最後檢查日 2026-06-16；機制以 [RabbitMQ DLX 官方文件](https://www.rabbitmq.com/docs/dlx) 為準。

## 失敗訊息 requeue 回隊首，會卡住整條隊列

消費一則訊息失敗了——下游 API 超時、資料還沒就緒、暫時性錯誤。最直覺的處理是 `nack` 加 `requeue=true`，讓它重新排隊再試一次。問題是 RabbitMQ 的 requeue 把訊息放回**原隊列的隊首**，於是它立刻又被同一個 consumer 取出、再次失敗、再 requeue……在「下游還沒恢復」的那段時間裡，這則訊息反覆佔據隊首，後面所有正常訊息全被卡住。這就是 head-of-line blocking：一則毒訊息（poison message）拖垮整條隊列。

[Indeed 每天處理 35M+ 職缺訊息](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/)，原本的架構正是把失敗訊息 requeue 回隊首，造成阻塞。他們的解法是設計 **Requeue → Delay queue → Dead Letter Queue 三層 escalation**：retry 幾次後讓訊息進延遲隊列（隔一段時間再試）、再失敗幾次才進 DLQ（停止重試、留待人工或專門處理）。這個案例揭露的核心原則是——**retry 策略要跟隊列拓樸一起設計，不是純 client 端的 backoff**。

本文展開 RabbitMQ 實現這套分層 retry 的機制（dead-letter exchange + TTL）、實機驗證的拓樸、以及把它寫成事故的踩坑。

## 核心概念：dead-letter exchange 的求值模型

RabbitMQ 的失敗訊息處理建立在 dead-letter exchange（DLX）上。理解它要抓住「訊息在什麼條件下被 dead-letter、去哪裡」。

**訊息在三種情況被 dead-letter**。一則訊息會從它所在的隊列被轉送到該隊列設定的 DLX：(1) 被 consumer `nack` / `reject` 且 `requeue=false`；(2) 訊息 TTL 到期（`x-message-ttl` 或 per-message expiration）；(3) 隊列達到長度上限（`x-max-length`）被擠掉。這三種 reason 會記在訊息的 `x-death` header 裡。

**DLX 是隊列的屬性、不是訊息的**。在宣告隊列時用 `x-dead-letter-exchange` 指定這個隊列的「死信要送去哪個 exchange」，搭配 `x-dead-letter-routing-key` 指定送過去時用什麼 routing key。死信被當成一則新訊息發布到那個 exchange，再依綁定路由到 DLQ。

**TTL + DLX 組出「延遲隊列」**。RabbitMQ 沒有原生的延遲投遞，但可以用「一個沒有 consumer、只設 TTL + DLX 的隊列」模擬：訊息進這個隊列、躺到 TTL 到期、被 dead-letter 回工作 exchange——等於延遲了 TTL 那麼久才重新可被消費。這是分層 retry 的關鍵積木。

**`x-death` header 累積重試歷史**。每次 dead-letter，RabbitMQ 在 `x-death` header 追加一筆記錄（哪個隊列、什麼 reason、次數 count）。消費端讀這個 count 就能判斷「這則訊息重試幾次了」，決定要再延遲還是進 DLQ。這是實現「retry n 次後升級」的依據。

## 配置：work → delay → DLQ 三層拓樸

實機驗證的最小 DLX 拓樸（工作隊列的訊息 TTL 到期後 dead-letter 到 DLQ）：

```bash
# 宣告 DLX exchange 與 DLQ
rabbitmqadmin declare exchange name=dlx type=direct
rabbitmqadmin declare queue name=dlq
rabbitmqadmin declare binding source=dlx destination=dlq routing_key=app.work

# 工作隊列：設 TTL + 指向 DLX（TTL 到期或 nack(requeue=false) 都會 dead-letter）
rabbitmqadmin declare queue name=app.work \
  arguments='{"x-message-ttl":2000,"x-dead-letter-exchange":"dlx","x-dead-letter-routing-key":"app.work"}'

# 驗證：發一則、等 TTL 到期、它從 app.work 搬到 dlq
rabbitmqadmin publish routing_key=app.work payload="poison-msg"
# 4 秒後：
rabbitmqctl list_queues name messages
# app.work   0     ← TTL 到期被搬走
# dlq        1     ← 落到 DLQ（訊息帶 x-death header、reason=expired）
```

實機驗證於 rabbitmq:3-management（最後檢查日 2026-06-16）：publish 後等 TTL 過期，`app.work` 歸零、`dlq` 出現該訊息。

三層 escalation 的完整拓樸（對應 Indeed 模式）：

```text
app.work（主工作隊列）
  └─ consumer nack(requeue=false) 或處理失敗
       ↓ dead-letter 到
app.retry（延遲隊列：x-message-ttl=30s、無 consumer、DLX 指回 app.work）
  └─ TTL 到期
       ↓ dead-letter 回
app.work（再次嘗試；消費端讀 x-death count）
  └─ 重試達上限（例如 count >= 3）→ 消費端主動 nack 到
app.dlq（死信終點：無自動重試、人工 / 專門 consumer 處理）
```

判讀：

- 延遲時間靠 `app.retry` 的 TTL 控制；要指數退避就設多個不同 TTL 的 delay 隊列（30s / 5m / 1h）逐層升級
- 「重試幾次」由消費端讀 `x-death` 的 count 判斷、達上限才送終點 DLQ
- DLQ 不該有自動重試的 consumer（否則又是迴圈）；它是給人看的、或給冪等的專門修復流程

## Production 故障演練

### Case 1：requeue 回隊首、毒訊息卡死整條隊列

**徵兆**：下游短暫故障期間，整條隊列的消費停滯、consumer CPU 衝高但吞吐歸零，恢復後發現大量正常訊息延遲。

**根因**：失敗時用 `nack(requeue=true)`，訊息回到隊首被立刻重取、反覆失敗，head-of-line blocking。下游故障越久，毒訊息霸佔隊首越久。

**修法**：

1. 失敗一律 `nack(requeue=false)` 走 DLX，不要 requeue 回原隊列
2. 用 delay 隊列（TTL + DLX）讓重試隔一段時間，給下游恢復時間
3. 重試有上限，達上限進終點 DLQ，停止自動重試
4. 這正是 [Indeed 案例](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/) 的核心教訓：retry 拓樸化，不要 requeue-to-head

### Case 2：delay 隊列綁錯、retry 變無限迴圈

**徵兆**：某些訊息永遠在重試、`x-death` count 累積到幾百次，DLQ 卻一直是空的。

**根因**：delay 隊列的 DLX 指回工作隊列，但消費端沒有檢查 `x-death` count、或上限判斷寫錯，訊息在 work ↔ retry 之間無限往返、永遠到不了終點 DLQ。

**修法**：

1. 消費端每次處理前讀 `x-death` 的 count，超過上限就主動投遞到終點 DLQ（不再走 retry）
2. 上限判斷要涵蓋所有 retry 路徑，不要漏掉某條
3. 監控 `x-death` count 分布，出現高 count 訊息代表升級邏輯漏了
4. 終點 DLQ 絕對不要接會 nack-to-DLX 的 consumer，否則迴圈

### Case 3：per-queue TTL 的隊首阻塞陷阱

**徵兆**：用 `x-message-ttl` 設隊列級 TTL 做延遲，但發現訊息沒有按預期時間 dead-letter，延遲時間忽長忽短。

**根因**：隊列級 TTL（`x-message-ttl`）只在訊息到達隊首時才檢查是否過期。如果用 per-message TTL 且不同訊息 TTL 不同，前面一則長 TTL 的訊息會擋住後面短 TTL 的——後者明明過期了卻因為不在隊首而沒被 dead-letter。

**修法**：

1. delay 隊列用統一的隊列級 TTL（同一個 delay 隊列裡所有訊息延遲時間相同），不要在同隊列混用 per-message TTL
2. 要多種延遲時間就開多個 delay 隊列（每個固定 TTL），不要靠 per-message TTL
3. 理解 TTL 是「到隊首才檢查」的惰性求值，不是精準定時器
4. 需要精準排程的延遲用專門的 delay 機制（rabbitmq-delayed-message-exchange plugin），不靠 TTL 模擬

### Case 4：DLX 沒綁好、死信靜默消失

**徵兆**：訊息明明該 dead-letter，但 DLQ 一直收不到，訊息憑空消失。

**根因**：DLX exchange 存在、隊列也設了 `x-dead-letter-exchange`，但 DLX 到 DLQ 的 binding 不存在或 routing key 對不上。死信被發布到 DLX 後沒有任何隊列接收（unroutable），直接被丟棄。

**修法**：

1. 確認 DLX → DLQ 的 binding 存在且 routing key 匹配（`x-dead-letter-routing-key` 對上 binding key）
2. 沒設 `x-dead-letter-routing-key` 時死信沿用原 routing key，binding 要對應原 key
3. 給 DLX 設 alternate exchange 或在 DLX 上掛一個 catch-all 隊列，避免 unroutable 死信靜默消失
4. 監控 DLX 的 unroutable / drop 指標，死信消失是嚴重的資料遺失

### Case 5：DLQ 無上限成長、變成第二個問題

**徵兆**：DLQ 累積到幾十萬則訊息、記憶體吃緊，沒人處理。

**根因**：DLQ 是終點但沒有處理流程——訊息一直進、沒人消費，DLQ 變成一個越長越大的垃圾堆，最終吃光 broker 記憶體（classic queue 訊息在記憶體）。

**修法**：

1. DLQ 要有處理流程：告警 + 人工 / 自動修復 consumer（冪等地重新投遞或記錄）
2. DLQ 設 `x-max-length` 或自己的 TTL，避免無限成長（但要先確認丟棄可接受）
3. 監控 DLQ 深度與成長速率，持續成長代表上游有系統性失敗、要根治而非堆 DLQ
4. quorum queue 對 DLQ 是合理選擇（持久、不純靠記憶體），見 [quorum vs mirrored queue deep article](/backend/03-message-queue/vendors/rabbitmq/quorum-vs-mirrored-queue/)

## Capacity / cost 邊界

分層 retry 拓樸的容量判讀：

| 訊號                 | 健康區間             | 警戒與動作                                    |
| -------------------- | -------------------- | --------------------------------------------- |
| 主隊列消費吞吐       | 穩定、無停滯         | 歸零但有積壓 → 毒訊息 head-of-line blocking   |
| `x-death` count 分布 | 多數低（1-2 次成功） | 高 count 訊息多 → 下游系統性故障 / 升級邏輯漏 |
| DLQ 深度             | 低且有處理流程       | 持續成長 → 無人處理、會吃光記憶體             |
| delay 隊列堆積       | 隨重試量波動、可消化 | 持續堆高 → 重試量超過下游恢復速度             |
| unroutable 死信      | 0                    | > 0 → DLX binding 錯、死信靜默遺失            |

撞牆後的路由判斷：

- **重試量大、delay 隊列堆積**：重試治標、下游系統性故障要根治；考慮 circuit breaker 在上游擋住而非無限重試。
- **需要精準延遲排程**：TTL 模擬的延遲不精準（惰性求值），用 rabbitmq-delayed-message-exchange plugin。
- **DLQ / 隊列要持久可靠**：classic queue 靠記憶體 + 鏡像，大量積壓有風險；用 [quorum queue](/backend/03-message-queue/vendors/rabbitmq/quorum-vs-mirrored-queue/)（Raft 持久）。
- **吞吐 / 保留需求超過 RabbitMQ**：retry / replay 是 log-based broker 的強項，大規模 replay 走 [Kafka](/backend/03-message-queue/vendors/kafka/)（consumer 各自 offset、可重讀）。

## 整合 / 下一步

分層 retry 是 RabbitMQ 可靠消費的核心，它跟其他議題交織：

- **跟 [3.2 durable queue](/backend/03-message-queue/durable-queue/)**：DLQ 要持久才不會在 broker 重啟時丟失死信。
- **跟 [3.4 consumer design](/backend/03-message-queue/consumer-design/)**：prefetch / ack 策略決定毒訊息影響範圍，跟 retry 拓樸一起設計。
- **跟 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)**：retry 與 DLQ 重新投遞都要求消費冪等，否則重試造成重複副作用。
- **跟 [quorum vs mirrored queue](/backend/03-message-queue/vendors/rabbitmq/quorum-vs-mirrored-queue/)**：DLQ 與重試隊列的持久性選 quorum queue，避開 mirrored queue 的網路成本。

## 相關連結

- 上游 vendor 頁：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/)
- 同 vendor deep article：[quorum vs mirrored queue](/backend/03-message-queue/vendors/rabbitmq/quorum-vs-mirrored-queue/)
- 對應案例：[3.C25 Indeed delay queue + DLQ 三層 escalation](/backend/03-message-queue/cases/rabbitmq-indeed-delay-dlq-escalation/)
- 上游概念：[3.2 durable queue](/backend/03-message-queue/durable-queue/)、[3.4 consumer design](/backend/03-message-queue/consumer-design/)
