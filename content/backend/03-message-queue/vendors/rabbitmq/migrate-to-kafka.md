---
title: "RabbitMQ → Kafka：從『處理即承諾』到『寫入即承諾 + 可 replay』的 paradigm shift"
date: 2026-06-16
description: "RabbitMQ 跟 Kafka 不是同類產品（work queue vs event streaming log）、把 work queue 直接搬成 topic 會踩 paradigm 落差；本文先跑 6 維 diff dimension audit（paradigm 跟 data topology 差最大）、釐清什麼 workload 真該遷什麼不該、再展開 application 重設計的 5 個踩雷（manual ack 觀念帶到 offset commit / routing key → partition key 的 ordering 邊界 / DLX → 自建 DLQ topic / prefetch → max.poll.records / 即刪 vs retention 的 replay 差異）、以及 dual-write / shadow consume 漸進 cutover 與長期混合架構"
weight: 11
tags: ["backend", "message-queue", "rabbitmq", "kafka", "migration", "paradigm"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) 跟 [Kafka](/backend/03-message-queue/vendors/kafka/)。跟同類產品的 drop-in 或 operational 遷移不同、本篇是 *paradigm shift* — 兩端不是「同類 broker 的不同實作」、是 *不同責任模型的 messaging system*：RabbitMQ 是「處理即承諾」的 work queue、Kafka 是「寫入即承諾、可長期 replay」的 event log。

## RabbitMQ → Kafka 不是把 queue 換成 topic

RabbitMQ 跟 Kafka 都被歸在「message queue」這個傘狀詞下、但兩者承擔的責任不同。RabbitMQ 的可靠性建立在 *consumer 處理完才 ack、未 ack 的訊息 broker 重新投遞*；訊息一旦被成功消費就從 queue 移除、broker 是「任務分派 + 重試」的中介。Kafka 的可靠性建立在 *訊息寫進 partition log 就持久化、consumer 各自維護 offset*；訊息在 retention 期內一直留著、broker 是「事件儲存 + 多方各自讀取」的 log。

把 RabbitMQ「migration」成 Kafka 的字面理解通常是：queue 對 topic、exchange 對 producer key、consumer 對 consumer group。這個對映在 transport 層成立、在責任層不成立。RabbitMQ 一個 message 被 ack 後就消失、Kafka 一個 message 寫進 log 後對所有 consumer group 都還在；RabbitMQ 的 routing 由 broker 端 exchange + binding 決定、Kafka 的「routing」由 producer 端 partition key 決定、broker 不做內容路由。先確認這層差異、再決定哪些 workload 值得遷。

## 6 維 diff dimension audit

跨 vendor 遷移前先盤點 source 跟 target 在六個維度的落差、用最大落差維度決定 playbook 結構、而不是反過來套既有模板。RabbitMQ → Kafka 的 audit 結果：

| 維度                 | 落差   | 說明                                                                                               |
| -------------------- | ------ | -------------------------------------------------------------------------------------------------- |
| Schema / API         | 中     | AMQP client → Kafka client、wire protocol 全換、但都是 publish / consume 心智模型                  |
| Operational model    | 中     | 單 broker + management UI → multi-broker + KRaft / Schema Registry / Connect、運維資產變重         |
| Abstraction/paradigm | **高** | work queue「處理即承諾、ack 後即刪」→ event log「寫入即承諾、offset replay」、責任模型整個不同     |
| Number of components | 低     | 兩端都是單一 messaging system、不是一站式拆多工具                                                  |
| Application change   | **高** | consumer 要重設計（ack → offset commit）、producer 要重設計（exchange routing → partition key）    |
| Data topology        | **高** | exchange + queue + binding 的 routing 拓樸 → topic + partition + key 的 log 拓樸、資料分佈邏輯不同 |

三個維度 High：paradigm、application change、data topology。其中 paradigm 是主導維度 —— application change 跟 data topology 的落差都是 paradigm 落差的下游結果。consumer 要重寫，是因為「ack 後即刪」變成「offset 不刪」；資料拓樸要重劃，是因為「broker 路由到 queue」變成「producer 決定 partition」。

主導維度是 paradigm、對映 *Type E paradigm shift* 結構：先講「字面 migration 不成立」、再講適配度（什麼能遷什麼不能）、再講 application 重設計與部分 cutover、最後是長期混合架構。application change 跟 data topology 這兩個高維度不另起 playbook、而是落在 application 重設計段與故障演練段裡展開。

### 為什麼 paradigm 是主導、不是 application change

application change 看起來工作量最大（consumer / producer 都要改），直覺會把它當主導維度。但 application change 的方向跟難度是由 paradigm 決定的：如果只是 AMQP client 換 Kafka client、心智模型不變，那 application change 是機械式翻譯、屬於 Schema/API 維度。實際上 consumer 不只是換 SDK、是要把「處理完才 ack、失敗就 nack 重投」的設計改成「拉一批、處理、commit offset、失敗自己重試或寫 DLQ topic」—— 這是責任模型的改變，不是 API 的改變。所以主結構走 paradigm、application change 是它的展開。

## 什麼 workload 真該遷、什麼不該

| Application 模式                          | RabbitMQ 適配  | Kafka 適配              | 遷移可行性                |
| ----------------------------------------- | -------------- | ----------------------- | ------------------------- |
| 任務分派（寄信 / 轉檔 / webhook）         | 強             | 中（overkill）          | 不該遷（保留 RabbitMQ）   |
| 複雜 routing（topic exchange + binding）  | 強             | 弱（broker 不做路由）   | 不該遷或要重新設計拓樸    |
| RPC over messaging（request-reply）       | 強             | 弱（不適合）            | 不該遷                    |
| Event sourcing（多 consumer 各自 replay） | 弱（ack 即刪） | 強                      | 該遷（這是 Kafka 的主場） |
| CDC / 跨系統事件總線                      | 弱             | 強                      | 該遷                      |
| 高吞吐事件流 + 長期 retention             | 弱             | 強                      | 該遷                      |
| 同一事件要被多個獨立團隊各自消費          | 中（多 queue） | 強（多 consumer group） | 該遷                      |

判讀的核心問題是：*這個 workload 需要的是「處理一次就完成的任務」、還是「被多方各自讀取、可回放的事件」*。

任務分派場景不該遷。寄信、轉檔、生成縮圖這類 workload 的本質是「有一個工人池、把任務做完就結束」、RabbitMQ 的 manual ack + prefetch + DLX 對這條路徑是貼合的設計。把它搬到 Kafka 會引入不需要的複雜度：partition 數要規劃、consumer group rebalance 要管、offset commit 時機要自己設計、而換來的 replay 能力在「任務做完就丟」的場景根本用不到。單純 work queue 不需要 Kafka 是這篇 playbook 最該先說清楚的判讀。

事件流場景該遷。當同一份事件要被 analytics pipeline、search index sync、audit log、下游微服務各自消費、而且各自進度不同、偶爾要回放過去 N 天重算 —— RabbitMQ 的「ack 後即刪」就會逼出「為每個 consumer 複製一份 queue」的反模式，這正是 Kafka 的 consumer group + retention 要解的問題。

複雜 routing 場景要重新設計、不是平移。RabbitMQ 的 topic exchange 用 `order.*.created` 這種 binding pattern 在 broker 端做內容路由、consumer 訂閱 binding 就收到符合的訊息。Kafka broker 不做內容路由，要嘛把路由邏輯前移到 producer（按內容決定寫哪個 topic / partition key），要嘛 consumer 端全收後自己 filter。直接平移會發現 Kafka 沒有 exchange 這個概念，routing 拓樸必須重新設計。

## 為什麼會考慮這個 paradigm shift

實務上從 RabbitMQ 評估遷往 Kafka 通常由三條 driver 觸發：

1. **同一事件要 fan-out 給愈來愈多 consumer**：初期一個 queue 一個 worker、後來下游團隊一個個來要「也給我一份」。RabbitMQ 要嘛加 fanout exchange + 每團隊一個 queue、要嘛 consumer 互搶。Kafka 的 consumer group 天然支援「N 個獨立團隊各自從頭讀」、這是最常見的 driver。
2. **需要 replay 重算**：下游邏輯出 bug、要重跑過去 7 天的事件修資料；RabbitMQ ack 後訊息已刪、無從回放。Kafka retention 期內可以從任意 offset 重讀。
3. **吞吐量壓到 RabbitMQ 的設計邊界**：單 queue 的 throughput 受限於單一 queue 的處理模型、量大時要拆 queue 手動分流；Kafka 的 partition 並行是 first-class。

這三條 driver 都指向 event streaming 的特性、不是「Kafka 普遍比較好」。任務隊列場景套不上這三條 driver、就不該被這個評估帶著走。

## Migration 結構：application 重設計 + 部分 cutover + 長期混合

RabbitMQ → Kafka 不是一次性 cutover，是按 workload 拆分、漸進遷移、長期共存：

1. **Phase 0：workload 盤點** — 把現有 queue / exchange 逐一分類「適合 Kafka（event 性質）」vs「保留 RabbitMQ（task 性質）」。盤點輸出是清單，不是「全遷」。
2. **Phase 1：application code 重設計** — 對判定要遷的 workload，重寫 producer（exchange routing → topic + partition key）跟 consumer（manual ack → offset commit + 自管重試 / DLQ）。這是 paradigm 翻譯，不是 SDK 替換。
3. **Phase 2：dual-write 並行** — producer 同時寫 RabbitMQ 跟 Kafka、新 consumer 從 Kafka shadow consume 驗證行為對齊、舊 consumer 持續從 RabbitMQ 消費。
4. **Phase 3：cutover 個別 workload** — shadow 驗證通過後、把該 workload 的真正消費切到 Kafka、停掉 RabbitMQ 端的對應 consumer 與 dual-write。
5. **Phase 4：長期混合** — task 性質的 workload 永遠留在 RabbitMQ、event 性質的在 Kafka。兩者共存是終態、不是過渡。

整體不是「把 RabbitMQ 換成 Kafka」、是「把適合 event log 的部分搬到 Kafka、其餘留在 RabbitMQ」。多數環境的終態是兩者並存。

## Application 重設計範例：manual ack → offset commit

RabbitMQ consumer 的核心是 *每個 message 處理完顯式 ack、broker 才認定投遞成功*；失敗就 nack、broker 重投或進 DLX。Kafka consumer 沒有 per-message ack 的概念、是 *批次拉取、處理、commit offset*；commit 的是「讀到哪了」、不是「哪幾條成功了」。

```python
# RabbitMQ 端：manual ack、per-message 成敗
channel.basic_qos(prefetch_count=10)

def on_message(ch, method, properties, body):
    try:
        process(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        # 拒絕並不重新入列、由 DLX 接住
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

channel.basic_consume(queue="orders", on_message_callback=on_message)
channel.start_consuming()
```

```python
# Kafka 端：批次 poll、處理後 commit offset
consumer = KafkaConsumer(
    "orders",
    group_id="orders-worker",
    enable_auto_commit=False,        # 關掉 auto commit、自己控制時機
    auto_offset_reset="earliest",
    max_poll_records=10,             # 對應 RabbitMQ 的 prefetch
)

for batch in iter_batches(consumer):
    for msg in batch:
        try:
            process(msg.value)
        except Exception:
            send_to_dlq_topic(msg)   # 自建 DLQ topic、Kafka broker 不提供 DLX
    consumer.commit()                # commit 的是 offset、不是個別 message
```

差異的關鍵不在 API 形狀、在責任邊界：

- RabbitMQ 一條失敗就 nack 一條、其餘正常 ack；Kafka commit 的是 offset 這個「水位線」、水位線以下視為已處理。失敗的單條訊息無法「跳過不 commit 但繼續往後」—— 要嘛阻塞、要嘛自己寫 DLQ topic 後讓 offset 照常前進。
- RabbitMQ 重試由 broker 負責（重投 / DLX）；Kafka 重試要 application 自己設計（原地重試 / 寫 retry topic / 寫 DLQ topic）。
- RabbitMQ prefetch 控制「broker 一次推幾條未 ack 的給我」；Kafka `max.poll.records` 控制「我一次 poll 拉幾條」—— 方向相反，一個是 broker push、一個是 consumer pull。

## Production 故障演練

### Case 1：manual ack 觀念帶到 offset commit、誤判「已處理」

**徵兆**：cutover 後某 worker crash 重啟、發現一批訊息被重複處理；或反過來、一批訊息明明沒處理成功卻再也讀不到。RabbitMQ 端跑了多年的 ack 邏輯搬過來就出事。

**根因**：把 RabbitMQ 的「per-message ack」心智直接套到 Kafka 的 offset commit。常見錯法是 `enable.auto.commit=true` + 預設 `auto.commit.interval.ms`、消費迴圈還沒處理完、背景 thread 已經把 offset commit 出去了 —— crash 後 offset 已前進、未處理的訊息永遠跳過（資料遺失）。或反過來、處理完才 commit 但 commit 失敗、重啟後從舊 offset 重讀（重複處理）。RabbitMQ 的 ack 是「這一條我處理完了」、Kafka 的 commit 是「這個 offset 之前我都讀過了」—— 後者是水位線、不是逐條確認。

**修法**：

1. **關掉 auto commit、手動 commit**：`enable.auto.commit=false`、在一批訊息確實處理完之後才 `commit()`。
2. **接受 at-least-once、設計 idempotency**：Kafka 的預設語意是 at-least-once、重啟重讀無法完全避免、consumer 端要用 message key + dedup store 顯式去重。對應 [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)。
3. **commit 時機對齊處理邊界**：批次處理完才 commit、不要一邊處理一邊讓背景 commit 跑在前面。

### Case 2：routing key → partition key、ordering 邊界悄悄改變

**徵兆**：cutover 後同一個訂單的 `created` / `paid` / `shipped` 事件偶爾亂序到達 consumer；RabbitMQ 端用 consistent hash exchange 跑了兩年、同一訂單的事件一直是有序的。

**根因**：RabbitMQ 用 consistent hash exchange 把同 key 的訊息路由到同一個 queue、單一 consumer 順序處理就有序。Kafka 的 ordering 保證範圍是 *單一 partition 內*、跨 partition 無序。如果 producer 沒設 partition key、或設了但 key 選得不對（例如用 event type 當 key 而不是 order id）、同一訂單的事件就散到不同 partition、被不同 consumer 並行處理、ordering 就斷了。RabbitMQ 的 ordering 邊界是「queue」、Kafka 的 ordering 邊界是「partition key」—— 邊界從 broker 端的 binding 移到了 producer 端的 key 選擇。

**修法**：

1. **ordering 單位當 partition key**：需要保序的單位（order id / user id）設成 partition key、同 key 落同 partition。
2. **盤點現有 RabbitMQ 的保序假設**：哪些 queue 隱含「同 key 有序」、把那個 key 顯式提升為 Kafka partition key。
3. **接受 partition 數限制並行**：保序的代價是同 key 只能單一 partition、partition 數是並行上限；保序需求跟並行度需要一起設計。對應 [Partition](/backend/knowledge-cards/partition/) 卡。

### Case 3：DLX → 自建 DLQ topic、毒訊息卡住整個 partition

**徵兆**：某條訊息 application 處理永遠拋例外、consumer 不斷在這條上重試、整個 partition 後面的訊息全卡住、consumer lag 暴增；RabbitMQ 端這種毒訊息會被 nack 進 DLX、不影響後面。

**根因**：RabbitMQ 有原生 DLX、處理失敗的訊息 nack 後自動進 dead-letter exchange、queue 繼續往下。Kafka broker 沒有 DLX 概念、也沒有「跳過這一條」的機制 —— offset 是連續水位線、要往後就得處理掉當前這條。如果 application 在毒訊息上無限重試、offset 永遠不前進、後面所有訊息餓死。把 RabbitMQ「broker 幫我處理毒訊息」的假設帶過來、就會卡死。

**修法**：

1. **自建 DLQ topic**：consumer 端設重試上限、超過上限把訊息寫進專屬的 `orders.DLQ` topic、然後 commit offset 讓主流程前進。對應 [Dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) 卡。
2. **retry topic 分層**：仿 RabbitMQ 的延遲重試、可以設 `orders.retry.5s` / `orders.retry.1m` 多層 retry topic、由獨立 consumer 延遲後重投主 topic。
3. **DLQ 要有人看**：自建 DLQ topic 不像 RabbitMQ management UI 有現成可視化、要主動監控 DLQ topic 的訊息數、否則毒訊息靜默堆積。

### Case 4：prefetch → max.poll.records，poll 間隔超時觸發 rebalance

**徵兆**：consumer 處理一批訊息花的時間偏長、Kafka 突然判定這個 consumer 死了、觸發 rebalance、partition 被重新分配、同一批訊息被另一個 consumer 重複處理；RabbitMQ 端用 prefetch 控制併發從沒這問題。

**根因**：RabbitMQ prefetch 只控制「broker 一次最多推幾條未 ack 給這個 consumer」、處理多久 broker 不管。Kafka 用 `max.poll.interval.ms` 監控「兩次 poll 之間最多隔多久」、如果一批 `max.poll.records` 拉太多、處理超過 `max.poll.interval.ms` 還沒回來 poll、broker 認定 consumer 卡死、踢出 group 觸發 rebalance。把 prefetch 的數值直接套成 `max.poll.records`、又沒考慮單批處理時間、就會超時。

**修法**：

1. **`max.poll.records` 配合單條處理時間設**：一批的總處理時間要明顯小於 `max.poll.interval.ms`；處理慢就把 batch 設小。
2. **長處理 workload 調大 `max.poll.interval.ms`**：單條本來就慢（呼叫外部 API）的、把 interval 放寬、或把處理移到另一個 thread pool、poll 迴圈只負責拉取。
3. **理解 push vs pull 的差異**：RabbitMQ 是 broker push、consumer 慢只是堆積；Kafka 是 consumer pull、consumer 慢會被誤判為死亡。這層差異是 prefetch 跟 max.poll.records 不能直接對映的根因。對應 [Consumer group](/backend/knowledge-cards/consumer-group/) 卡。

### Case 5：RabbitMQ 即刪 vs Kafka retention、replay 行為差異炸出資料量

**徵兆**：團隊以為 Kafka「跟 RabbitMQ 一樣處理完就沒了」、結果 disk 持續長大；或反過來、需要 replay 時才發現 retention 設太短、要回放的事件已經被清掉。RabbitMQ 心智下「訊息消費完就不佔空間」的假設不成立。

**根因**：RabbitMQ ack 後訊息即刪、queue 的空間隨消費釋放。Kafka 寫進 log 後在 *retention 期內一直留著*、不管有沒有被消費 —— 這正是 replay 能力的來源、也是 disk 成本的來源。沒設好 retention，要嘛留太久 disk 爆、要嘛留太短該 replay 時沒得 replay。RabbitMQ 沒有「retention」這個旋鈕（它是 ack 即刪），Kafka 必須顯式設 retention policy。

**修法**：

1. **按 replay 需求設 retention**：event sourcing 要回放幾天就設幾天的 `retention.ms`、不是抄 RabbitMQ 的「處理完即刪」心智。
2. **算清 retention 的 disk 成本**：retention × 寫入速率 = 佔用空間、納入容量規劃；對比 RabbitMQ 只佔「未消費」的量、Kafka 佔「retention 期內全部」的量。
3. **compact topic 給狀態類資料**：如果只需要「每個 key 最新值」（像 RabbitMQ 不存在的場景）、用 `cleanup.policy=compact` 而非 time-based delete、避免無限長大。對應 [Topic](/backend/knowledge-cards/topic/) 卡的 retention policy。

## 漸進 cutover：dual-write 與 shadow consume

paradigm shift 不能一次切換、因為 consumer 行為（offset 語意、ordering、DLQ、重試）全變了、需要在真實流量下驗證新 consumer 跟舊 consumer 結果一致才敢切。漸進 cutover 用兩個機制：

**dual-write**：producer 同時往 RabbitMQ 跟 Kafka 寫同一份事件。RabbitMQ 端維持舊 consumer 正常生產、Kafka 端讓新 consumer 接收。dual-write 期間 RabbitMQ 仍是 source of truth、Kafka 只是並行驗證。要處理的細節是雙寫的一致性 —— 寫了 RabbitMQ 但 Kafka 寫失敗時怎麼辦、實務上通常容忍 Kafka 端短期缺漏（因為還沒切過去）、但要監控雙端的訊息數落差。

**shadow consume**：新的 Kafka consumer 跑完整處理邏輯、但 *side effect 導到影子環境*（寫影子 DB、不發真實 webhook、不寄真實信）。把 Kafka consumer 的處理結果跟 RabbitMQ consumer 的真實結果比對、確認 ordering、去重、DLQ 行為都對齊。shadow 期是 paradigm 翻譯正確性的驗證窗口、不是效能測試。

cutover 是 per-workload 的：某個 workload shadow 驗證通過、就把它的真實消費切到 Kafka、停掉該 workload 的 RabbitMQ consumer 與 dual-write；其他 workload 維持原狀繼續驗證。不是全站一次切。

## Capacity / cost 對照

| 維度                | RabbitMQ（self-managed）         | Kafka（self-managed）                       |
| ------------------- | -------------------------------- | ------------------------------------------- |
| Cluster baseline    | 1-3 node（含 management plugin） | 3-5 broker + KRaft controller               |
| RAM / node baseline | 4-16GB                           | 16-64GB                                     |
| Storage 模型        | 未消費訊息量（ack 即刪）         | retention 期內全部訊息（與消費無關）        |
| Operational FTE     | 0.2-0.5 FTE                      | 0.5-2 FTE                                   |
| 額外運維元件        | 通常無                           | Schema Registry / Connect / 監控 lag        |
| Throughput / node   | 數萬到數十萬 msg/s               | 100K-1M+ msg/s                              |
| Replay 能力         | 無（ack 即刪）                   | retention 期內任意 offset                   |
| 複雜 routing        | 強（exchange + binding）         | 弱（producer 端決定、broker 不路由）        |
| 學習與運維成本      | 低                               | 高（partition / offset / rebalance 都要懂） |

判讀：純 work queue 場景 RabbitMQ 的運維成本顯著低、Kafka 的 storage 跟運維是為了 replay 與高吞吐付的價。如果 workload 用不到 replay 跟跨 consumer group fan-out、遷到 Kafka 是用更高的成本換用不到的能力。

## 整合 / 下一步

### 混合架構是 long-term default

多數環境的終態是 RabbitMQ 與 Kafka 共存、各管各的責任：

```text
[task 分派：寄信 / 轉檔 / webhook]        [event log：CDC / 事件總線 / replay]
         RabbitMQ                                    Kafka
         │                                            │
         └──────── Bridge（Connect source / 自寫）────┘
```

RabbitMQ 跑「處理即承諾」的任務隊列、Kafka 跑「寫入即承諾」的事件流。需要從任務流產生事件記錄時、用 Kafka Connect 的 RabbitMQ source connector 或自寫 bridge 把選定的訊息搬到 Kafka topic。

### 跟 outbox pattern 對位

從 RabbitMQ 遷往 Kafka 常伴隨 *資料庫交易與事件發布一致性* 的需求 —— 因為 event sourcing 場景要求事件不能丟。直接在交易中寫 Kafka 有雙寫一致性問題、應該走 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)：交易內只寫 outbox 表、再由 [Debezium CDC](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 把 outbox 變更發到 Kafka topic。

### 跟其他 migration 結構的對照

| 篇                       | Schema 差 | Operational 差 | Paradigm 差 | 結構           |
| ------------------------ | --------- | -------------- | ----------- | -------------- |
| Kafka ↔ NATS             | 中        | 中             | **高**      | partial + 混合 |
| RabbitMQ → Kafka（本篇） | 中        | 中             | **高**      | partial + 混合 |

兩篇都是 paradigm shift、都是 partial migration + 長期混合。差別在落差的方向：Kafka ↔ NATS 是 log vs subject messaging 的抽象層差異、RabbitMQ → Kafka 是 work queue vs event log 的責任模型差異 —— 後者的核心翻譯是「處理即承諾」如何重新表達成「寫入即承諾 + offset replay」。

## 相關連結

- Source / target vendor：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) / [Kafka](/backend/03-message-queue/vendors/kafka/)
- 平行 vendor：[NATS](/backend/03-message-queue/vendors/nats/) / [Redis Streams](/backend/03-message-queue/vendors/redis-streams/)
- 平行 migration playbook：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [Kafka → MSK](/backend/03-message-queue/vendors/kafka/migrate-to-msk/)
- 關鍵概念卡：[Partition](/backend/knowledge-cards/partition/) / [Topic](/backend/knowledge-cards/topic/) / [Consumer group](/backend/knowledge-cards/consumer-group/) / [Dead-letter queue](/backend/knowledge-cards/dead-letter-queue/) / [Ack/nack](/backend/knowledge-cards/ack-nack/)
- 下游能力：[3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/) / [3.4 consumer 設計](/backend/03-message-queue/consumer-design/) / [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
- Methodology：[Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)
