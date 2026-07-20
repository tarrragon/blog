---
title: "2.10 Pub/Sub 與即時 fan-out"
date: 2026-06-16
description: "說明 Redis Pub/Sub 的即時廣播責任、at-most-once 邊界，以及何時升級到 Streams 或正式 message queue"
weight: 10
tags: ["backend", "cache", "redis", "pub-sub"]
---

Redis [Pub/Sub](/backend/knowledge-cards/pub-sub/) 的核心責任是把一則訊息即時推送給當下所有訂閱者，讓跨節點的狀態變更可以在同一瞬間擴散。它承擔的是「現在發生的事，立刻讓所有人知道」，正式的可靠投遞與重播責任由 [message queue](/backend/knowledge-cards/queue) 與 [Redis Streams](/backend/03-message-queue/) 承擔。把這條邊界放在最前面，是因為 Pub/Sub 的多數事故都來自把它當成可靠訊息系統使用。

## at-most-once：訊息只送給此刻在線的訂閱者

訊息[投遞語意](/backend/knowledge-cards/delivery-semantics/)有三種：at-most-once（最多送一次、可能漏）、at-least-once（至少送一次、可能重複）、[exactly-once](/backend/knowledge-cards/exactly-once/)（剛好一次、最難實作）。Pub/Sub 採 [at-most-once](/backend/knowledge-cards/duplicate-delivery/)，用「可能漏」換取低延遲與無狀態，後兩種語意由 Streams 或 message queue 承擔。具體來說：`PUBLISH` 把訊息送給發布當下已經 `SUBSCRIBE` 該 channel 的連線，沒有訂閱者就直接丟棄，訊息不寫入任何持久結構。訂閱者離線、重連、或處理速度跟不上時，那段時間的訊息不會補送。

這個語意決定了 Pub/Sub 適合承擔什麼。可以接受「偶爾漏一則、下一則狀態會蓋過來」的場景，Pub/Sub 的低延遲與簡單模型是優勢；要求「每一則都不能掉」的場景，例如訂單事件、扣款通知、稽核軌跡，這些責任屬於 durable queue，不該放在 Pub/Sub。

判讀的關鍵問題是：漏掉一則訊息的代價是什麼。presence 狀態廣播漏一則，下次 heartbeat 會修正；cache invalidation 廣播漏一則，該節點會保留 stale 副本直到 TTL 到期，代價是短暫不一致；扣款事件漏一則，代價是金額錯誤且無法自動修復。前兩者落在 Pub/Sub 的能力範圍，第三者越界。

## 適用場景：狀態變更的即時扇出

Pub/Sub 的典型用途是把一個節點上發生的狀態變更，即時扇出給其他節點。這類場景的共同特徵是「最終狀態會自我修正」，所以單則訊息可丟。

fan-out 有兩種語意要先分清，因為它們決定能不能用 Pub/Sub。一種是全量 fan-out：每個訂閱者都收到同一則訊息的完整副本，適合「所有節點都要知道這件事」的廣播（presence、cache invalidation、config reload）。另一種是分攤 fan-out：同一則訊息只交給一個 consumer 處理、多個 consumer 之間分攤負載，適合「這件工作只要有一個人做」的任務分派。Pub/Sub 只提供全量 fan-out——`PUBLISH` 把訊息送給所有訂閱者，沒有「只給其中一個」的語意。需要分攤 fan-out 時要轉 Redis Streams 的 consumer group（`XREADGROUP` 讓一則訊息只有一個 consumer 拿到），這條邊界在本章末的升級段展開。

presence 變更廣播是最直接的應用。[2.5 presence store](/backend/02-cache-redis/presence-store/) 的 cross-node query 回答「現在誰在線」，但當某個使用者上線或離線時，其他節點需要被即時通知才能推播給好友列表。presence key 寫入時同步 `PUBLISH` 一則 `user:online` 訊息，訂閱該 channel 的節點立刻更新本地視圖。漏一則的代價是某個好友的線上狀態延遲幾秒，下次狀態同步會補正，落在可接受範圍。

cache invalidation 扇出是第二類應用。當一個節點更新了 [source of truth](/backend/knowledge-cards/source-of-truth/) 並失效了自己的本地 cache，其他持有同一份 process-local cache 的節點需要被通知一起失效。`PUBLISH cache:invalidate product:123` 讓所有節點丟棄該 key 的本地副本。這條路徑要跟 [2.2 cache aside](/backend/02-cache-redis/cache-aside/) 的失效策略對齊：Pub/Sub 負責「通知」，實際失效仍由各節點執行，且因為 at-most-once，必須有 TTL 作為兜底，避免廣播漏送讓某節點永久持有 stale 副本。

即時配置熱刷新是第三類。feature flag、限流閾值、路由表這類低頻變更的配置，更新時 `PUBLISH config:reload`，各節點收到後重新拉取最新配置。低頻特性讓 at-most-once 風險很低，而即時性比輪詢配置中心更省資源。

## SUBSCRIBE 的連線模型

訂閱會把連線切換進專用模式：一旦 `SUBSCRIBE`，該連線只能再執行 `SUBSCRIBE`、`UNSUBSCRIBE`、`PING` 與訂閱相關命令，不能在同一條連線上跑 `GET`、`SET` 等一般命令。原因是訂閱連線進入了等待推送的狀態，伺服器隨時可能把訊息推過來，與請求應答式命令的時序會衝突。

這個模型的工程含義是：訂閱要用獨立的連線，不能跟一般讀寫共用同一個 client。共用連線池的應用要為 Pub/Sub 保留專門的訂閱連線，避免訂閱模式污染了拿來做 cache 讀寫的連線。這條限制跟 [2.1 高併發讀寫邊界](/backend/02-cache-redis/high-concurrency-access/) 的連線管理直接相關：訂閱連線是長連線、數量應該受控，與短命的請求應答連線分開計量。

訂閱連線斷線重連時，要重新 `SUBSCRIBE` 所有 channel，且要意識到斷線期間的訊息已經永久丟失。可靠性敏感的設計會在重連後主動拉一次全量狀態，用一次 [reconciliation](/backend/knowledge-cards/data-reconciliation/) 補上廣播漏掉的窗口。

## cluster 下的 fan-out 與 sharded Pub/Sub

在單節點與傳統 cluster 中，`PUBLISH` 的訊息會傳播到 cluster 內所有節點，確保任何節點上的訂閱者都能收到。這個全傳播模型保證了廣播的完整性，但代價是每則訊息都要在節點間擴散，高頻發布時會佔用 cluster 內部頻寬。

sharded Pub/Sub（`SPUBLISH` / `SSUBSCRIBE`）把這個成本收斂：sharded channel 的訊息只在負責該 channel slot 的分片內傳播，不擴散到整個 cluster。代價是訂閱者必須連到正確的分片才能收到。判讀條件是發布頻率與 cluster 規模：低頻廣播用一般 Pub/Sub 換取部署簡單；高頻發布且 cluster 節點多時，sharded Pub/Sub 避免內部頻寬被廣播流量吃掉。`PUBSUB SHARDNUMSUB` 可以查某 shard channel 的訂閱者數，用來判讀扇出是否落在預期分片。

## keyspace notifications：把 key 事件變成廣播源

keyspace notifications 讓 Redis 在 key 發生變更（寫入、刪除、過期）時自動 `PUBLISH` 一則事件，訂閱者不必輪詢就能知道某個 key 變了。開啟後，`SET`、`DEL`、TTL 過期都會發出對應 channel 的訊息。

這個能力把 presence cleanup 變得更即時。[2.5 presence store](/backend/02-cache-redis/presence-store/) 的 cleanup 策略依賴 TTL 過期讓離線狀態消失，但「過期了」這件事本身可以透過 `__keyevent@0__:expired` 事件廣播出去，讓其他節點即時得知某連線下線，而不必等到下次查詢才發現。

keyspace notifications 同樣採 at-most-once 語意，且過期事件的觸發時機與 Redis 的惰性過期機制有關：key 在被存取或背景掃描到時才真正過期並發出事件。延遲量級取決於 key 下次被存取的時機與背景掃描週期（active expiry 預設每秒約執行 10 輪、每輪抽樣部分過期 key），最差情況下事件可能延遲數秒到數分鐘。需要精確過期時序的設計，仍要保留主動查詢路徑作為依據。

## 何時從 Pub/Sub 升級

Pub/Sub 的邊界訊號出現時，責任應該往 [Redis Streams](/backend/03-message-queue/) 或正式 [message queue](/backend/knowledge-cards/queue) 移動。判準是 durable 與 replayable 這兩個 Pub/Sub 不提供的能力。

| 需求訊號                   | Pub/Sub 的限制             | 該轉向的能力                                                                                    |
| -------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------- |
| 訂閱者離線期間的訊息不能丟 | at-most-once、不持久化     | Redis Streams 的 [persistence](/backend/knowledge-cards/message-persistence/) 與 consumer group |
| 需要重播歷史訊息           | 訊息發布後即丟棄、無法回放 | Streams 的 ID 範圍讀取、message queue 的 replay                                                 |
| 需要確認訊息已被處理       | 沒有 ack 機制              | Streams 的 `XACK`、queue 的 acknowledgement                                                     |
| 消費者失效時訊息要被接手   | 訊息隨連線丟失             | Streams consumer group 的 pending list 與 claiming                                              |
| 需要消費者群組分攤負載     | 每個訂閱者都收到全部訊息   | Streams `XREADGROUP` 的單一 owner 語意                                                          |

Redis Streams 是介於 Pub/Sub 與重量級 broker 之間的選項：它持久化訊息、支援 consumer group 與 ack，又仍在 Redis 內，遷移成本低於引入 Kafka 或 RabbitMQ。Streams 與正式 message queue 的選型、consumer 設計、replay 邊界屬於 [模組三 message queue](/backend/03-message-queue/) 的責任，本章只負責標出「何時該離開 Pub/Sub」這條邊界。

## 判讀訊號

| 訊號                           | 判讀重點                                      | 對應動作                                        |
| ------------------------------ | --------------------------------------------- | ----------------------------------------------- |
| 訂閱者抱怨偶爾漏訊息           | at-most-once 在重連窗口丟訊息                 | 重連後補一次全量 reconciliation，或轉 Streams   |
| cluster 內部頻寬被廣播流量吃掉 | 一般 Pub/Sub 全節點傳播成本過高               | 改 sharded Pub/Sub、收斂傳播範圍                |
| 訂閱連線數量隨流量無上限成長   | 訂閱連線與一般讀寫連線混用                    | 分離訂閱連線池、獨立計量                        |
| 廣播漏送導致某節點長期 stale   | 只靠 Pub/Sub 通知失效、缺 TTL 兜底            | 補 TTL 作為失效兜底，廣播只當加速               |
| 訂閱者跟不上發布、訊息靜默丟棄 | Pub/Sub 無 backpressure、發布方看不到消費積壓 | 改 Streams（pending list 可量積壓）或限發布速率 |
| 開始需要「這則處理了沒」的確認 | Pub/Sub 無 ack、責任已越界                    | 轉 Redis Streams 或正式 message queue           |

訂閱者抱怨漏訊息時，先確認這是不是 at-most-once 的預期行為而非 bug。Pub/Sub 在訂閱者重連窗口丟訊息是設計而非故障，正確的修法是判斷這個場景能不能接受丟；能接受就保留 Pub/Sub 並補 reconciliation，不能接受就轉向 durable 方案。

廣播漏送導致長期 stale 之所以難防，是因為 cache invalidation 廣播在多數時候成功，讓人把失效當成可靠，直到某次漏送讓一個節點持有錯誤價格或權限數小時而沒有任何報錯。TTL 兜底的意義就是把「廣播失敗」的最壞影響限制在一個 TTL 週期內，把 Pub/Sub 定位成「加速失效」而非「保證失效」。

## 常見誤區

把 Pub/Sub 當成可靠訊息系統，是最常見也代價最大的誤區。Pub/Sub 沒有持久化、沒有 ack、沒有重播，這些是它換取低延遲與簡單模型的設計取捨。需要這些能力時，正確做法是換工具，而不是在 Pub/Sub 外圍補一層補丁去模擬可靠投遞。

把訂閱連線跟一般讀寫連線共用，是第二個誤區。訂閱會讓連線進入專用模式，混用會讓 cache 讀寫命令在該連線上失敗或行為異常。訂閱連線要獨立管理。

只靠 Pub/Sub 廣播做 cache invalidation 而沒有 TTL 兜底，是第三個誤區。廣播的 at-most-once 特性意味著總有漏送的可能，TTL 是讓漏送影響有上界的保險。

## 情境回寫

Pub/Sub 的即時扇出語意，回寫到真實服務時最常見的形狀是多節點即時狀態同步。一個多區域部署的即時通訊服務，使用者上線狀態由所在區域的節點寫入，其他區域的節點需要即時得知才能更新好友列表的線上指示。這條路徑用 Pub/Sub 廣播狀態變更，回寫時要保留「跨區傳播有延遲窗口、單則訊息可丟、靠後續 heartbeat 收斂」的判讀，而非把它當成可靠投遞。

這個形狀支撐的是「即時廣播 + 最終狀態收斂」的判讀。若根因是訊息不能丟（狀態變更會觸發扣款、稽核或計費），應回到 [模組三 message queue](/backend/03-message-queue/) 的 durable 方案；模組三的 fan-out 案例（如 Twitch EventSub 用 SNS + SQS 扇出給第三方）記錄了 durable 扇出的設計，可在需要持久化與重播時對照。

## 跨模組路由

1. 與 2.5 的交接：presence 狀態變更的廣播回到 [presence store 與即時狀態](/backend/02-cache-redis/presence-store/)。
2. 與 2.2 的交接：cache invalidation 扇出與 TTL 兜底回到 [cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)。
3. 與 2.1 的交接：訂閱連線管理與一般讀寫連線分離回到 [高併發下的 Redis 讀寫邊界](/backend/02-cache-redis/high-concurrency-access/)。
4. 與模組三的交接：需要持久化、ack 與重播時轉向 [message queue](/backend/03-message-queue/) 與 Redis Streams。

## 下一步路由

要看即時狀態本身如何建模與清理，回到 [2.5 presence store 與即時狀態](/backend/02-cache-redis/presence-store/)。要看廣播訊息升級成 durable 投遞後的 consumer 設計與重播邊界，接著讀 [模組三 message queue](/backend/03-message-queue/)。
