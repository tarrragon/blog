---
title: "Pub/Sub Ordering Key、Dead-Letter Topic 與 Schema Enforcement：三道交付治理"
date: 2026-06-16
description: "Pub/Sub overview 之下的 implementation-layer deep article — 把 ordering key 的有序代價、dead-letter topic 的 poison message 隔離、schema enforcement 的契約守門三件事寫到可操作：subscription 是 first-class、ackDeadline 與 extension、push vs pull vs streaming pull + flow control、Avro / Protobuf schema、Pub/Sub Lite 與標準版差異、BigQuery / Cloud Storage subscription，含 5 個 production 故障演練（ordering 限流 / ack deadline 太短重投 / DLT max delivery attempts / push 500 retry storm / schema 擋下不相容 publish）"
weight: 11
tags: ["backend", "message-queue", "google-pubsub", "ordering-key", "dead-letter-topic", "schema", "deep-article"]
---

> 本文是 [Google Cloud Pub/Sub](/backend/03-message-queue/vendors/google-pubsub/) overview 的 implementation-layer deep article。Overview 回答「Pub/Sub 該不該選、跟 Kafka / SQS 差在哪」；本文回答「ordering key 怎麼設、DLT 怎麼擋 poison message、schema 怎麼守契約，各自踩哪些坑」。閱讀前可先讀 overview 的 ordering / DLT / schema 各段建立 context。
>
> 文中 gcloud 指令的語法以 Pub/Sub emulator 實機驗證（topic / subscription / schema / ordering key / DLT / push 各操作均跑通），標準版的雲端配額、IAM 與計費行為依官方文件。

## 三道治理共用同一個交付骨架

Pub/Sub 的 ordering key、dead-letter topic、schema enforcement 看似三個獨立功能，實際都掛在同一個交付骨架上：subscription 是消費進度的 first-class 抽象、訊息經 ackDeadline 控制重投、失敗訊息經投遞次數計數決定去留。理解這個骨架之後，三道治理只是骨架上的三個切面 — ordering 切的是「投遞順序」、DLT 切的是「投遞次數上限」、schema 切的是「投遞前的內容守門」。

這條骨架跟 Kafka 思路不同。Kafka 的消費進度綁在 consumer group + partition offset；Pub/Sub 的 [topic](/backend/knowledge-cards/topic/) 是 first-class，subscription 才是 consumer 抽象，一個 topic 可以掛 N 個 subscription、各自有獨立進度與獨立的 ackDeadline / DLT / ordering 設定。同一份 event 流，A subscription 可以開 ordering 嚴格有序、B subscription 可以不開 ordering 換吞吐，互不影響。

把這三道治理寫進一篇的理由是：它們在 production 會互相牽制。Ordering key 開了之後 DLT 的隔離行為會變（有序流裡一則 poison message 會卡住整把 key 的後續訊息）；schema enforcement 擋下的不相容 publish 不會進 DLT（根本沒進 topic）。分開讀三個官方頁面看不到這層耦合。

## subscription 是 first-class：ackDeadline 與 extension

subscription 承擔「這個消費者讀到哪、還有多少沒 ack」的責任。每則訊息投遞給 subscriber 後，Pub/Sub 啟動一個 ackDeadline 倒數；倒數內收到 ack 就移除訊息、倒數結束沒收到 ack 就重投。預設 ackDeadline 是 10 秒、上限 600 秒。

```bash
# subscription 的 ackDeadline 預設 10 秒、retention 預設 7 天
gcloud pubsub subscriptions describe demo-sub
# ackDeadlineSeconds: 10
# messageRetentionDuration: 604800s   # 7 天

# 建 subscription 時可顯式設更長的 ackDeadline 與更短的 retention
gcloud pubsub subscriptions create cfg-sub \
  --topic=demo-topic \
  --ack-deadline=120 \
  --message-retention-duration=3d
# ackDeadlineSeconds: 120
# messageRetentionDuration: 259200s   # 3 天
```

ackDeadline 是一道「處理時間預算」。設太短，處理還沒完訊息就被重投，consumer 會收到重複；設太長，consumer crash 後訊息要等滿 deadline 才重投，延遲拉高。長任務不靠把 ackDeadline 一次設到 600 秒解決，而是靠 ack deadline extension：consumer 在處理中週期性發 `modifyAckDeadline` 把單則訊息的 deadline 往後延，處理完才 ack。

```bash
# pull 一則但不 auto-ack，拿到 ackId
ACKID=$(gcloud pubsub subscriptions pull demo-sub --limit=1 --format='value(ackId)')

# 處理中動態延長這則訊息的 ackDeadline 到 300 秒
gcloud pubsub subscriptions modify-message-ack-deadline demo-sub \
  --ack-ids="$ACKID" \
  --ack-deadline=300
```

實務上不手動發 `modifyAckDeadline`，而是用 client library 的自動 lease 管理：client 在背景對 outstanding 訊息週期性續約，直到 application code 回 ack / nack。這跟 SQS 的 visibility timeout 語意類似 — 都是「訊息正在被處理、暫時別重投」的租約 — 但 Pub/Sub 是 per-message lease + client 自動續約，SQS 是 per-receive visibility window + 手動 `ChangeMessageVisibility`。

> ackDeadline 的陷阱在 batch 邊界。client library 常以 batch 為單位 pull，但 ackDeadline lease 是 per-message。若 application 把整個 batch 當一個工作單元處理、處理時間超過單則 ackDeadline 且 client 未對每則續約，未 ack 的訊息會被重投。Mercari 的 actionable history pipeline 就踩過「ack deadline 是 batch-level 的誤判」（[3.C63](/backend/03-message-queue/cases/pubsub-mercari-actionable-history/)）。

## Push、Pull、Streaming Pull 與 flow control

subscription 有兩種交付方向，pull 之下又分 unary pull 與 streaming pull。三者對應不同的下游承壓能力。

| 交付模型       | 機制                                        | 適合場景                                  | flow control 由誰掌握       |
| -------------- | ------------------------------------------- | ----------------------------------------- | --------------------------- |
| Push           | Pub/Sub 主動 POST 到 HTTPS endpoint         | 無狀態 worker、Cloud Run、Cloud Functions | Pub/Sub（按 ack 動態調速）  |
| Unary Pull     | consumer 每次發一個 pull 請求拿一批         | 低頻、批次拉取、簡單腳本                  | consumer（自己控拉取頻率）  |
| Streaming Pull | consumer 開長連線、Pub/Sub 持續推送到該連線 | 高吞吐長 worker、需要精確 flow control    | consumer（client lib 設定） |

Push 把投遞節奏交給 Pub/Sub：endpoint 回 2xx 視為 ack、回非 2xx 或逾時視為 nack 並 backoff 重投。Pull 把節奏交給 consumer：consumer 想拉才拉、拉多少自己定。Streaming pull 是 production 高吞吐場景的主力 — client library 默認用它，因為它能在單一長連線上做精細的 flow control。

flow control 是 pull 的核心優勢：consumer 用 `max_outstanding_messages` 與 `max_outstanding_bytes` 設定「同時最多持有多少未 ack 訊息」，超過上限 client 就暫停從連線拉取，等 application ack 釋放額度才繼續。這讓 consumer 能把消費速率對齊到下游能吃的速率，而不是被 broker 灌爆。

> Push vs pull 不是實作偏好，是「下游能否接受 push 衝擊」的判讀。Mercari 的 LINE 整合把 webhook 轉成 Pub/Sub event 後，下游 worker 刻意用 pull subscription 精確控制每秒處理訊息數，因為外部 LINE API 有 RPS 限制 — push 會把瞬間流量直接打到受限的外部 API（[3.C65](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)）。下游有硬性 RPS 上限時，pull + flow control 是讓消費速率可控的手段。

## Ordering Key：有序的代價是吞吐

Ordering key 讓「帶同一個 ordering key 的訊息，在 subscription 端按 publish 順序投遞」。它把全域無序的 Pub/Sub 變成 per-key 有序 — 不同 key 之間仍可並行、亂序，只有同 key 內部保證順序。要生效需要兩端配合：subscription 建立時開 `--enable-message-ordering`，publish 時帶 `--ordering-key`。

```bash
# subscription 端開啟 ordering
gcloud pubsub subscriptions create ord-sub \
  --topic=ord-topic \
  --enable-message-ordering
# describe 可見 enableMessageOrdering: true

# publish 端帶 ordering key（同一 key 的訊息會保序）
gcloud pubsub topics publish ord-topic --message=m1 --ordering-key=user-123
gcloud pubsub topics publish ord-topic --message=m2 --ordering-key=user-123
```

Ordering key 的設計責任在於選對 key 的粒度。粒度太粗（例如所有訊息共用一個 key）會把整條 topic 退化成單線序列、吞吐崩塌；粒度太細（例如每則訊息一個 key）等於沒開 ordering。正確做法是按「需要保序的業務實體」選 key — 同一個 `user-123` 的事件要保序、不同 user 之間不需要 — 這樣並行度等於活躍 key 數，既保序又不犧牲整體吞吐。

跟 Kafka 對照能看清取捨。Kafka 用 partition + 同 key hash 到同 partition 達成保序，partition 數是固定預先規劃的並行上限；Pub/Sub 沒有顯式 partition，ordering key 的並行度是動態的、由活躍 key 數決定。代價是 Pub/Sub 的有序投遞要求同 key 訊息送到同一個內部處理單元，這個約束讓單一 ordering key 的吞吐有上限（官方標稱單 ordering key 約 1 MB/s）。

> Ordering 跟 DLT 在 production 會耦合：有序流裡若一則訊息反覆失敗、Pub/Sub 為維持順序不會跳過它去投後面的訊息，整把 key 的後續訊息全卡住，直到該訊息 ack 或送進 DLT。沒開 ordering 時 poison message 只卡自己；開了 ordering 後它卡住整條 key 序列。這是下一節 DLT 要解的問題在 ordering 場景下被放大的原因。

## Dead-Letter Topic：投遞次數上限決定隔離時機

Dead-letter topic 是 [poison-message quarantine](/backend/knowledge-cards/poison-message-quarantine/) 在 Pub/Sub 的實作：subscription 對每則訊息計數投遞次數，超過 `max-delivery-attempts` 就把訊息轉發到另一個 topic（DLT），主 subscription 不再重投它，後續正常訊息得以前進。

```bash
gcloud pubsub topics create main-topic
gcloud pubsub topics create dl-topic

gcloud pubsub subscriptions create main-sub \
  --topic=main-topic \
  --dead-letter-topic=dl-topic \
  --max-delivery-attempts=5
# deadLetterPolicy:
#   deadLetterTopic: projects/<proj>/topics/dl-topic
#   maxDeliveryAttempts: 5
```

DLT 是 topic 不是 queue，這是 Pub/Sub 跟 SQS DLQ 的關鍵差異。SQS 的 DLQ 是另一個 queue、消費者直接 receive；Pub/Sub 的 DLT 是 topic，要再掛一個 subscription 才能讀。好處是 DLT 上可以同時掛多個 subscription — 一個給人工檢視、一個給自動 replay、一個給長期歸檔 — fan-out 內建。代價是多一層 subscription 配置，且 DLT 也有自己的 retention（同樣預設 7 天，poison message 要在這之內處理掉）。

`max-delivery-attempts` 設定的是「容忍多少次暫時性失敗」與「多快放棄」之間的平衡。設太低（例如 1-2 次），下游短暫抖動就把訊息丟進 DLT、誤殺可恢復的訊息；設太高（例如 50 次），一則真正壞掉的訊息會反覆重試半天、占用 consumer 資源、在有序流裡還會長時間卡住整條 key。官方允許範圍 5-100，常見起點是 5。

搭配 retry policy 的 backoff 能讓重投不至於太密集：

```bash
gcloud pubsub subscriptions create retry-sub \
  --topic=main-topic \
  --min-retry-delay=10s \
  --max-retry-delay=600s
# retryPolicy:
#   minimumBackoff: 10s
#   maximumBackoff: 600s
```

> 啟用 DLT 需要把 Pub/Sub service account 授權對主 subscription 有 subscriber、對 DLT 有 publisher（emulator 不校驗 IAM，正式環境若漏授權，訊息超過 max attempts 後不會進 DLT、而是繼續留在主 subscription 重投，看起來像 DLT 沒生效）。授權細節依 GCP 官方 IAM 文件。

Mercari 的商品 feed 同步示範了 DLT 的標準用法：pull subscription + 自家 batch requester、成功 ack 整批、失敗 nack 讓 Pub/Sub 重送、重試多次仍失敗送 DLT、後續訊息優先處理；同一個 topic 還兼當突發流量的 load-leveling buffer（[3.C64](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)）。

## Schema Enforcement：投遞前的契約守門

Schema enforcement 把 [event schema compatibility](/backend/knowledge-cards/event-schema-compatibility/) 從「應用層約定」提升到「broker 強制」。topic 綁定一個 Avro 或 Protobuf schema 後，不符 schema 的 publish 在進 topic 前就被拒絕 — 訊息根本不會被儲存、不會投遞、不會進 DLT。

```bash
# 1. 建 schema（Avro，一個必填 string 欄位 id）
gcloud pubsub schemas create order-schema \
  --type=avro \
  --definition='{"type":"record","name":"Order","fields":[{"name":"id","type":"string"}]}'

# 2. topic 綁 schema + 指定 message encoding
gcloud pubsub topics create sch-topic \
  --schema=order-schema \
  --message-encoding=json
```

綁定後的 publish 行為（emulator 實機驗證 enforce）：

```bash
# 符合 schema：通過
gcloud pubsub topics publish sch-topic --message='{"id":"abc"}'
# messageIds: ['4']

# 欄位不符 schema：被拒
gcloud pubsub topics publish sch-topic --message='{"wrong":123}'
# ERROR: INVALID_ARGUMENT: Could not parse message

# 非 JSON 垃圾：被拒
gcloud pubsub topics publish sch-topic --message='not-json'
# ERROR: INVALID_ARGUMENT: Could not parse message
```

schema 守門的價值在於把契約破壞擋在 producer 端、而不是 consumer 端。沒有 schema enforcement 時，producer 改了 payload 結構、不相容的訊息照樣進 topic、要到 consumer 解析失敗才爆 — 此時訊息已經在系統裡流動、可能已 fan-out 到多個 subscription、修復成本高。有 schema enforcement 時，不相容的 publish 在源頭就失敗，問題暴露在「誰送了壞訊息」而不是「誰收到壞訊息」。

schema evolution 要在「擋住破壞性改版」與「不阻塞合理演進」之間取捨。新增可選欄位或帶預設值的欄位維持相容、可以平滑演進；新增必填欄位、刪欄位、改型別是破壞性改版，會讓既有 producer 或 consumer 失效。設計上先定相容性等級（backward / forward / full）再演進，刪欄位分兩步（先停用再移除），避免一次破壞性改版打掛下游。

跟 Kafka Schema Registry 對照：Kafka 的 schema 校驗在 client 端（producer / consumer 各自向 Registry 查 schema、序列化時校驗），broker 本身不認識 schema；Pub/Sub 的 schema 綁在 topic、校驗在 broker 端 publish 路徑上。前者校驗點分散、靈活但要求所有 client 守規矩；後者校驗點集中在 broker、強制但耦合到 topic 配置。

## 五個 Production 故障演練

deep article 的差異化價值在故障演練。以下五個徵兆對應前述三道治理在 production 的典型失效。

### 演練一：Ordering key 把吞吐限到單線

**徵兆**：開了 ordering 後整條 topic 的吞吐從數萬 msg/s 掉到數百 msg/s，subscription backlog（`num_undelivered_messages`）持續攀升、`oldest_unacked_message_age` 越拉越長，但 consumer CPU 並不滿載 — consumer 在等訊息、不是在忙。

**根因**：ordering key 粒度太粗。最常見是「所有訊息共用同一個 ordering key」（例如固定字串、或單一租戶 ID），整條 topic 退化成單一有序序列，並行度等於 1。單一 ordering key 的吞吐有上限（官方標稱約 1 MB/s），所有訊息擠進一個 key 就被這個上限封頂。

**判讀與修法**：

1. 確認 ordering key 的基數（cardinality）。`gcloud pubsub topics publish` 帶的 `--ordering-key` 在 production 是業務欄位映射來的 — 檢查映射邏輯是否塌縮成低基數。
2. 把 key 粒度對齊到「真正需要保序的業務實體」：同一筆訂單 / 同一個 user / 同一個 device 內要保序，跨實體不需要。粒度從「全域一個 key」改成「per-user 一個 key」，並行度從 1 拉到活躍 user 數。
3. 評估是否真的需要 ordering。多數 pipeline 靠 consumer 端 idempotency + 版本號就能容忍亂序，不需要 broker 層保序 — 把保序成本從吞吐換成 consumer 設計（見 [3.7 event contract](/backend/03-message-queue/event-contract-replay-boundary/) 的 idempotency key 段）。

### 演練二：Ack deadline 太短導致重複投遞

**徵兆**：consumer 處理邏輯正確、下游也成功，但同一則訊息被處理多次；`DELIVERY_ATTEMPT` 計數異常偏高、下游出現重複副作用（重複扣款 / 重複發信）。Backlog 不一定高，但「處理量」遠大於「publish 量」。

**根因**：ackDeadline 比實際處理時間短。預設 10 秒對「呼叫一個慢的外部 API」「處理大 payload」這類任務不夠，訊息在 application 還沒 ack 前就過了 deadline、被 Pub/Sub 重投，於是同一則訊息有多個 consumer 副本在跑。若 client library 的自動 lease extension 沒生效（例如 application 阻塞在同步呼叫、background lease thread 餓死），重投更嚴重。

**判讀與修法**：

1. 量測 p99 處理時間，把 ackDeadline 設到 p99 之上留 buffer，但不要無腦設 600 秒 — deadline 越長，consumer crash 後訊息重投的延遲越長。
2. 長任務靠 lease extension 而非長 ackDeadline：確認 client library 的自動續約有在跑，application code 不要在處理迴圈裡阻塞到讓 background 續約 thread 餓死。
3. consumer 端做 idempotency：用 message 的 dedup key（[3.7](/backend/03-message-queue/event-contract-replay-boundary/)）讓重複投遞變成無害 — at-least-once 交付下重複是常態，不靠調 ackDeadline 消除、靠 consumer 設計吸收。

### 演練三：DLT max delivery attempts 設定誤判

**徵兆**：兩種反向徵兆。其一，DLT 堆滿了「其實能恢復」的訊息 — 下游一抖動就被丟進 DLT，DLT backlog 暴增、人工 replay 不完。其二，主 subscription 卡著一則壞訊息反覆重投半天都不進 DLT、後面訊息（尤其在 ordering 流裡）全堵住。

**根因**：第一種是 `max-delivery-attempts` 設太低（1-2 次），暫時性失敗就被當成 poison。第二種是設太高（數十次）或根本沒設 DLT，真正的 poison message 反覆重試、占資源、卡序列。

**判讀與修法**：

1. 區分「暫時性失敗」與「結構性失敗」。暫時性（下游超時、限流）需要重試容忍度，結構性（payload 解析不了、業務規則永久拒絕）越早隔離越好。
2. `max-delivery-attempts` 起點設 5，搭配 retry policy backoff（`--min-retry-delay` / `--max-retry-delay`）讓重試之間有間隔、給下游恢復時間，而不是密集重打。
3. 確認 DLT 真的接得到訊息：檢查 Pub/Sub service account 對 DLT 的 publisher 授權（漏授權會讓訊息超過 attempts 後繼續留在主 subscription、看起來像沒進 DLT）。
4. DLT 要掛 subscription 才讀得到 — DLT 是 topic 不是 queue，建完 DLT 還要建 DLT 的 subscription 並設好 retention，否則 poison message 在 DLT 裡放滿 7 天後一樣丟失。

### 演練四：Push endpoint 500 觸發 retry storm

**徵兆**：push subscription 的下游 HTTP endpoint 開始大量回 500，Pub/Sub backoff 重投、但 endpoint 仍 500，重投量隨 backlog 累積越滾越大；endpoint 一旦短暫恢復就被積壓的重投流量瞬間打回 500，形成「恢復即再掛」的震盪。

**根因**：push 的 flow control 由 Pub/Sub 掌握、按 ack 動態調速 — endpoint 回 2xx 視為 ack、非 2xx 視為 nack 並重投。當 endpoint 因下游依賴（DB / 外部 API）掛掉而持續 500，Pub/Sub 的 backoff 重投跟累積的 backlog 疊加，恢復瞬間的流量遠超 endpoint 平時負載。這正是「下游能否接受 push 衝擊」的反面 — push 沒有 consumer 端的 flow control 閥門。

**判讀與修法**：

1. 先判訊息毒性 vs endpoint 健康。若是 endpoint 整體掛（所有訊息都 500），是容量 / 依賴問題；若是特定訊息 500（多數成功、少數失敗），是 poison message，該走 DLT。
2. endpoint 整體掛的場景，push 不是好選擇 — 改 pull + flow control，讓 consumer 用 `max_outstanding_messages` 把消費速率對齊到下游能吃的速率，避免恢復瞬間被積壓流量打垮（對照 [3.C65](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/) 的下游 RPS 限制場景）。
3. 對 push 配 DLT，把反覆 500 的特定訊息隔離出去，避免單一 poison message 混在正常流量裡放大 retry。
4. endpoint 側對「Pub/Sub 重投」做 idempotency，因為 push 也是 at-least-once、500 後的重投會帶來重複。

### 演練五：Schema enforcement 擋下不相容 publish

**徵兆**：某次 producer 部署後，該 service 的 publish 開始大量回 `INVALID_ARGUMENT: Could not parse message`，訊息發不出去；但 consumer 端風平浪靜、沒有任何解析錯誤、backlog 也沒異常。

**根因**：這通常不是故障、是 schema enforcement 正常運作。producer 改了 payload 結構（加必填欄位 / 改型別 / 漏欄位），新 payload 不符 topic 綁定的 schema，broker 在 publish 路徑上擋下、訊息根本沒進 topic。徵兆出現在 producer 端（publish 失敗）而非 consumer 端（解析失敗），正是 schema 守門把問題前移到源頭的設計意圖。

**判讀與修法**：

1. 先確認是「該擋」還是「誤擋」。對照 producer 的新 payload 與 topic schema：若是破壞性改版（加必填欄位 / 改型別），enforcement 擋對了 — 該回滾 producer 或先演進 schema。
2. 用 `gcloud pubsub schemas validate-message` 在部署前 dry-run 校驗 payload 對 schema，把「不相容」暴露在 CI 而不是 production publish。
3. schema 演進走相容路徑：新增欄位帶預設或設可選、刪欄位分兩步、避免一次破壞性改版。先升 schema 再升 producer，順序反了就會出現這個徵兆。
4. 區分 schema enforcement 失敗與 DLT：schema 擋下的訊息不進 topic、不進 DLT（DLT 隔離的是「進了 topic 但消費反覆失敗」的訊息）。兩者是交付管線的不同關卡，徵兆與修法都不同。

## 容量與選型邊界：標準版 vs Pub/Sub Lite

前述配置適用標準版 Pub/Sub。標準版的計費與容量模型偏向「全域路由內建、按用量計費、不需預先規劃容量」；當吞吐極高且 region 確定時，Pub/Sub Lite 的 partition-based / zonal 模型成本更低。

| 維度        | 標準版 Pub/Sub                 | Pub/Sub Lite                               |
| ----------- | ------------------------------ | ------------------------------------------ |
| 路由        | 全域、無 region 概念           | zonal / regional、需指定                   |
| 容量模型    | 自動擴縮、按用量計費           | partition-based、預先 provision throughput |
| 成本        | 高吞吐時單位成本較高           | 高吞吐 + 確定 region 時顯著較低            |
| CLI surface | `gcloud pubsub topics`         | `gcloud pubsub lite-topics`（獨立）        |
| 適用        | 全域分發、彈性流量、不想管容量 | 已知高且穩定的吞吐、成本敏感、region 確定  |

Pub/Sub Lite 是獨立的 CLI surface（`gcloud pubsub lite-topics` / `gcloud pubsub lite-subscriptions`），不是標準版的一個 flag。選 Lite 的代價是要自己 provision partition 數與 throughput capacity（回到接近 Kafka 的容量規劃），換來的是高吞吐穩定流量下顯著更低的成本。判準是吞吐「夠高且夠穩定到值得自己管容量」— 流量彈性大、或不想管 partition 的場景仍該留在標準版。

> Spotify 的 autoscaling 案例揭露 backlog 不等於 consumer healthy：下游 export 失敗時 consumer 不 ack 仍持續耗 CPU，autoscaling 把 CPU 越拉越高、反而擴出更多空轉 consumer；解法是 exponential backoff 抑制 CPU 消耗（[3.C61](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)）。容量規劃的 autoscale signal 要看「處理成功率」而非「CPU + backlog」，否則擴縮方向會反。

## 整合與下一步

### BigQuery / Cloud Storage subscription：免 consumer 的落地路徑

標準版提供兩種「不需要自寫 consumer」的 subscription，直接把訊息落地到分析 / 儲存層：

- **BigQuery subscription**（`--bigquery-table`）：訊息直接寫進 BQ table，免 Dataflow 中介，適合 streaming analytics。可搭配 `--use-topic-schema` 讓 BQ table schema 對齊 topic schema — schema enforcement 在這裡延伸成「落地結構也受契約約束」。
- **Cloud Storage subscription**（`--cloud-storage-bucket`）：訊息批次寫成 GCS object，適合 data lake / 歸檔。

這兩種 subscription 把「event 流 → 分析 / 儲存」的常見管線收進 Pub/Sub 配置，省掉一層自管 consumer。它們仍受同一套 ackDeadline / DLT 骨架管轄。

### Cross-link

- 上游 vendor 頁：[Google Cloud Pub/Sub overview](/backend/03-message-queue/vendors/google-pubsub/) — 選型層、跟 Kafka / SQS 取捨
- 契約與重播邊界：[3.7 Event Contract 與 Replay Boundary](/backend/03-message-queue/event-contract-replay-boundary/) — schema / idempotency key / replay window 先於 broker 選型
- 知識卡：[Event Schema Compatibility](/backend/knowledge-cards/event-schema-compatibility/)（schema enforcement 守的契約等級）、[Poison-Message Quarantine](/backend/knowledge-cards/poison-message-quarantine/)（DLT 的隔離機制）
- 對應 case：[3.C64 Mercari Item Feed DLT](/backend/03-message-queue/cases/pubsub-mercari-item-feed-dlt/)、[3.C65 Mercari LINE flow control](/backend/03-message-queue/cases/pubsub-mercari-line-flow-control/)、[3.C61 Spotify autoscaling](/backend/03-message-queue/cases/pubsub-spotify-autoscaling-consumers/)、[3.C63 Mercari actionable history](/backend/03-message-queue/cases/pubsub-mercari-actionable-history/)
- 方法論：[Vendor 深度技術文章的寫作方法論](/posts/vendor-deep-article-methodology/)

### 何時 revisit

- ordering key 吞吐撞上單 key 上限、且無法再細分 key：評估改用 Kafka partition 模型，或把保序成本移到 consumer 端 idempotency
- 高吞吐穩定流量 + 成本壓力浮現：評估標準版 → Pub/Sub Lite，接受自管 partition 容量換成本
- schema 需要跨多 vendor 共用契約（同一份 event 同時進 Pub/Sub 與 Kafka）：評估把 schema source of truth 抽到 broker 外的 registry
