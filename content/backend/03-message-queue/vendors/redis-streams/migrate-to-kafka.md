---
title: "Redis Streams → Kafka：從 embedded stream 長成 dedicated event streaming"
date: 2026-06-16
description: "Redis Streams 是 Redis 生態內的 append-only log data structure、Kafka 是專用 distributed event streaming platform；這趟遷移是 paradigm shift — 從 RAM-bound 單 stream key 換成 partition + log retention 的多節點系統。本文先用 Arcjet 反向案例點明多數中小規模 Redis Streams 就夠、不該為流行遷 Kafka、再講真的該遷的訊號（retention 超出 RAM 成本 / 長期 replay / consumer group 規模超出單 Redis）、XADD/XREADGROUP/XACK/MAXLEN/XCLAIM 的對位、retention 成本翻轉與 PEL→offset 誤用的故障演練、漸進 cutover"
weight: 11
tags: ["backend", "message-queue", "redis-streams", "kafka", "migration", "paradigm"]
---

> 本文是跨 vendor migration playbook、cross-link 到 [Redis Streams](/backend/03-message-queue/vendors/redis-streams/) 跟 [Kafka](/backend/03-message-queue/vendors/kafka/)。對位 [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 的 *paradigm shift* 模板 — 兩端不是同類產品的不同實作、是不同抽象層的系統：一個是 Redis 行程內的 append-only log data structure、一個是專用的 distributed event streaming platform。

## Redis Streams 跟 Kafka 是不同抽象層的東西

Redis Streams 是 Redis 行程內的一個 data structure、Kafka 是一整套獨立的 distributed event streaming platform。這個區別決定整趟遷移的性質：要把 messaging 能力從「既有 Redis 行程的一塊記憶體」搬到「自成一格、要獨立運維的多節點叢集」，遠超過換個相容 broker 的工作量。

Redis Streams 的責任邊界是「在已經跑著的 Redis 裡多一個 append-only log」。它共用 Redis 的記憶體、持久化（AOF / RDB）、failover（Sentinel / Cluster）跟運維團隊。寫入用 `XADD`、消費用 `XREADGROUP`，consumer group 跟 pending entries list（PEL）都活在同一個 Redis 行程。它的設計取捨偏向「低延遲、低運維增量、跟 Redis 生命週期綁定」。

Kafka 的責任邊界是「成為跨系統的事件總線」。它把訊息寫成 partition 化的 log、落在獨立 broker 的磁碟、用 replication 保護、用 consumer group offset 追蹤各 consumer 進度，可長期保留並隨意 replay。它的設計取捨偏向「寫入即承諾、磁碟級長期保留、多 consumer 各自重播、水平擴展吞吐」。

| 維度           | Redis Streams                               | Kafka                                        |
| -------------- | ------------------------------------------- | -------------------------------------------- |
| 部署形態       | Redis 行程內的 data structure               | 獨立 broker 叢集（3-5 broker + KRaft）       |
| 儲存後端       | RAM-bound（受 `maxmemory` 限制）            | Broker 本地磁碟（可加 tiered storage to S3） |
| 拓樸單位       | 單一 stream key（綁單一 shard）             | Topic + 多 partition（跨 broker 分布）       |
| Retention 機制 | `MAXLEN` / `MINID`、application 主動 trim   | Broker 端 retention policy（time / size）    |
| 消費進度       | PEL + `XACK`（broker 維護待 ack 集合）      | Consumer offset commit（per partition）      |
| 失敗接管       | `XCLAIM` / `XAUTOCLAIM`（手動 / 半自動）    | Rebalance protocol（broker 協調自動分配）    |
| Replay         | 從 entry ID 重讀（受 retention 內資料限制） | 從任意 offset 重讀（受磁碟 retention 限制）  |
| 延遲           | 亞毫秒（記憶體操作）                        | 5-50ms                                       |
| 運維增量       | 近乎零（沿用 Redis）                        | 顯著（多養一套叢集 + schema / connect 生態） |

關鍵在「拓樸單位」這列。Redis Streams 的一個 stream key 只能落在單一 shard、沒有 partition 概念，吞吐與資料量受單 shard 的記憶體與單執行緒處理能力封頂。Kafka 的 topic 天然切成多 partition、分散到多 broker，這是兩者在規模上的分水嶺，也是後面所有對位與故障演練的根。

## 先確認是不是真的該遷：多數中小規模不該遷

決定遷移前先做反向確認：在中小規模、且團隊已熟 Redis 的情境，Redis Streams 往往已經夠用，把它換成 Kafka 多半是引入運維負擔而非解決問題。遷移的正當理由來自規模或保留需求真的超出 Redis Streams 的能力邊界，而不是 Kafka 更主流。

[Arcjet](/backend/03-message-queue/cases/redis-streams-arcjet-replace-kafka/) 的方向恰好相反、值得當反向參照。Arcjet 的 security / bot detection 平台需要低延遲請求處理，原本評估 Kafka，發現 managed Kafka 要六位數美元年費、自管運維難度也高；他們把既有的 Redis cache 層升級成 Streams，總成本掉到約一千美元年費。代價是 Redis Streams 沒有自動 retention，他們自寫一個 Janitor process，依約每分鐘一百則的實際處理速度監測 stream 長度跟 consumer group 狀態、selectively trim。

Arcjet 的判讀對遷移方向的啟示：當 workload 是低延遲、資料量留在記憶體可承受的範圍、團隊本來就在跑 Redis，Redis Streams 是務實且便宜的選擇；願意自寫 retention 工具就能補上它缺的治理能力。這條路成立時，遷去 Kafka 是用六位數年費跟一整套叢集運維，去換一個現有方案已能覆蓋的需求。

[Bitso](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/) 是另一個 Redis Streams 站得住的高壓案例。Bitso 的撮合引擎微服務要扛每秒上千則訊息、亞毫秒延遲、撐住 BTC 價格暴動的尖峰；他們先後評估 Kafka（延遲不符）跟 SQS（vendor lock-in + 延遲）後選 Redis Streams，自建一層 Reliable Streams 抽象封裝 PEL + retry + DLQ，走 idempotent processing 接受重複勝過遺失。Bitso 揭露 Redis Streams 是「資料結構」而非「broker 系統」，可靠性責任在 application 層；但在亞毫秒延遲是硬指標的撮合場景，這個取捨反而讓 Redis Streams 勝過 Kafka。

兩個案例共同點：當延遲是硬指標、資料量在 RAM 可承受範圍、團隊能自建缺的治理層，Redis Streams 就站得住。遷去 Kafka 的決策該建立在這些前提不再成立之上，而不是建立在 Kafka 更有名之上。

## 真正該遷的訊號

決定遷移的依據是 Redis Streams 的三個能力邊界被實際 workload 突破：retention 需求超出 RAM 的成本曲線、需要長期 replay、consumer group 或 partition 規模超出單一 Redis 行程。三個訊號中任一個被觸發、且自建工具補不回來時，遷去 Kafka 才划算。

第一個訊號是 retention 超出 RAM 的成本翻轉。Redis Streams 的資料活在記憶體，保留越久、stream 越長、佔的 RAM 越多，而 RAM 是 Redis 叢集裡最貴的資源。當 retention 需求從「幾小時的緩衝」長到「數天到數週的事件保留」，把這些資料留在 RAM 的成本會快速超過 Kafka 把同樣資料留在 broker 磁碟（甚至 tiered storage 到 S3）的成本。[Learning.com 退場案例](/backend/03-message-queue/cases/redis-streams-learning-com-event-source-retreat/)就是這條線被突破的反例 — 把 Redis 當長期事件儲存（Stream 是其中一塊），事件量每週以 GB 成長、AOF fsync 與 EBS I/O 變成 latency 痛點，最終退回 PostgreSQL。成本曲線翻轉是最常見、也最該觸發遷移的訊號。

第二個訊號是需要長期 replay。事件溯源（event sourcing）或合規稽核場景，需要保留並重播數週、數月甚至數年的歷史事件。Redis Streams 的 replay 只能重讀 retention 內還在的資料，而 retention 受 RAM 限制無法拉得很長；Kafka 的磁碟保留加 tiered storage 讓長期 replay 變成 first-class 能力。當 replay 視窗的需求超出 RAM 能承受的 retention，這個訊號成立。

第三個訊號是 consumer group 或 partition 規模超出單一 Redis。Redis Streams 的單一 stream key 綁在單一 shard，吞吐受單 shard 封頂、沒有 partition 可以水平拆分並行度；要跨 shard 只能手動用 hash tag 切成多個獨立 stream，application 自己路由。當單一邏輯 stream 的吞吐需求、或 consumer 並行度需求超過單 shard 能給的，且手動切 stream 的複雜度已經失控，Kafka 的原生 partition 才值得換。

這三個訊號之外，還有一個放大條件：是否需要 Kafka 生態（Schema Registry、Connect / Debezium CDC、Streams 流處理）。如果遷移同時要接上 CDC pipeline 或 schema 強制治理，那 Kafka 帶來的不只是 retention 跟 partition、而是整套生態，這會讓遷移的價值天平更傾向 Kafka。但若只是想要更長 retention、生態用不到，先評估 Redis tiered 方案或自建 Janitor 是否更便宜。

## 概念對位：XADD/XREADGROUP/XACK/MAXLEN/XCLAIM

遷移的核心工作是把 Redis Streams 的五個核心操作對應到 Kafka 的等價概念、並理解每個對位背後語意的偏移，這比換 SDK 重得多。直接照字面搬會在 retention、消費進度、失敗接管三處踩雷，這三處正是後面故障演練的來源。

| Redis Streams 操作           | Kafka 等價                       | 語意偏移                                                  |
| ---------------------------- | -------------------------------- | --------------------------------------------------------- |
| `XADD stream * field val`    | `producer.send(topic, key, val)` | Kafka 用 key 決定 partition、Redis 單 stream 無 partition |
| `XREADGROUP GROUP g c`       | consumer group + `poll()`        | Kafka rebalance 自動分配 partition、Redis 要手動 `XCLAIM` |
| `XACK stream g id`           | offset commit                    | PEL 是逐則待 ack 集合、offset 是單調位移、語意不同        |
| `MAXLEN` / `MINID` / `XTRIM` | retention policy（time / size）  | application 主動 trim → broker 端被動 retention           |
| `XCLAIM` / `XAUTOCLAIM`      | rebalance protocol               | 手動 / 半自動接管 → broker 協調自動 reassign              |

`XADD` 對 `producer.send` 的最大偏移是 partition key。Redis 的單一 stream key 沒有 partition，所有 entry 都在同一條序列上嚴格有序；Kafka 把訊息依 key 雜湊分到不同 partition，只有同一 partition 內保證有序。遷移時要決定哪個欄位當 partition key、這個決定同時決定了 ordering 的範圍跟 hot partition 的風險。

`XREADGROUP` 對 consumer group 的偏移在 rebalance。Redis consumer group 沒有自動 rebalance，consumer 掛掉後它名下未 ack 的訊息留在 PEL，要靠其他 consumer 主動 `XCLAIM` 接管；Kafka 的 consumer group 有 rebalance protocol，consumer 加入或離開時 broker 自動把 partition 重新分配。從手動接管搬到自動 rebalance，application 端負責接管的那段邏輯可以刪掉、但要改成理解 rebalance 行為。

`XACK` 對 offset commit 是最容易誤用的一處，獨立成下一節的故障演練。`MAXLEN` 對 retention policy 是成本模型翻轉的核心，也獨立成故障演練。

## Production 故障演練

### Case 1：Retention 模型從 RAM 限制翻成 log 成本，磁碟與成本失準

**徵兆**：團隊把 Redis Streams 的 `MAXLEN 100000`（保留最近十萬則、控制 RAM）習慣直接對映成 Kafka 的某個數字，結果 cutover 後不是 broker 磁碟暴漲超出預期、就是資料保留遠短於業務需要、replay 視窗對不上。

**根因**：Redis Streams 的 `MAXLEN` 是 application 在每次 `XADD` 主動修剪的「條數上限」，目的是壓住 RAM 佔用，是一個 count-based 的記憶體預算旋鈕。Kafka 的 retention 是 broker 端被動執行的 policy、預設是 time-based（`retention.ms`）或 size-based（`retention.bytes`），目的是控制磁碟保留窗，而磁碟比 RAM 便宜一到兩個數量級。兩者的單位、執行主體、成本曲線都不同 — 把「保留十萬則以省 RAM」直接搬成 Kafka 設定，會錯估磁碟用量，也會把 Redis 時代「為了省 RAM 而被迫短保留」的限制錯誤地帶進一個本來就能長保留的系統。

**修法**：

1. **從業務需求重算 retention、不沿用 Redis 的 RAM 預算**：Redis 的 `MAXLEN` 數字是 RAM 成本的妥協、不是業務的真實保留需求；遷移時回到「業務需要 replay 多久」重新算 `retention.ms`，這正是遷移要解鎖的能力。
2. **改用 time-based 為主、size-based 當保險絲**：Kafka 設 `retention.ms` 對齊業務 replay 窗、再設 `retention.bytes` 防單 partition 磁碟失控。
3. **長保留接 tiered storage**：retention 需求拉到數週數月時，把冷資料分層到 S3、熱資料留本地磁碟，成本曲線進一步壓平，而這在 Redis 的 RAM 模型下做不到。

### Case 2：PEL 觀念被帶進 offset，造成重複或漏消費

**徵兆**：遷移後 consumer 出現「明明處理過的訊息又被重新消費」或「某些訊息整批沒被處理」；團隊照 Redis 時代「逐則 `XACK`」的心智模型管理 Kafka offset commit，結果對不上。

**根因**：PEL 跟 offset 是兩個不同的進度模型。Redis Streams 的 PEL 是 broker 維護的「逐則待 ack 集合」，每則訊息獨立追蹤是否已 ack，consumer 可以亂序 ack 某幾則、其他留在 PEL；`XACK` 是針對特定 entry ID 的點狀確認。Kafka 的 offset 是 per partition 的單調位移、代表「這個位置之前都算消費完」，commit offset N 意味著 0 到 N-1 全部視為已處理。把 PEL 的逐則語意套到 offset 上會出兩種錯：一是處理完亂序的訊息後 commit 了較大的 offset，中間沒處理完的訊息被當成已消費而漏掉；二是 commit 時機錯置（auto-commit 在處理前就 commit），crash 後從錯誤位置重讀造成重複。

**修法**：

1. **理解 offset 是區間承諾、不是逐則確認**：commit offset 前確保該 offset 之前的訊息都已處理完、不要對亂序處理的批次 commit 最大 offset。
2. **關 auto-commit、改 manual commit 在處理之後**：`enable.auto.commit=false`，處理完一批再 commit，對齊 at-least-once。
3. **保留 application 端 idempotency**：這點從 Redis 時代就該有、遷到 Kafka 仍成立 — at-least-once 下重複難免，用 message ID + dedup store 顯式去重，對位 [idempotency 卡](/backend/knowledge-cards/idempotency/)跟 [Bitso 的 idempotent processing](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)。

### Case 3：單 stream key 換成多 partition，ordering 假設破裂

**徵兆**：遷移前所有事件在單一 Redis stream 上嚴格有序、downstream 依賴這個順序（例如同一筆訂單的 created → paid → shipped）；切到 Kafka 多 partition 後，同一筆訂單的事件被分到不同 partition、處理順序錯亂。

**根因**：Redis Streams 的單一 stream key 綁單一 shard、所有 entry 在一條序列上全域有序，application 不需要思考 ordering 範圍就免費得到全序。Kafka 把 topic 切成多 partition 來換取水平吞吐，代價是只保證 *同一 partition 內* 有序、partition 之間無序。遷移時若沒指定 partition key、訊息會被 round-robin 或依預設雜湊散開，同一個業務實體（訂單、帳戶、裝置）的事件落到不同 partition，全序假設就破了。

**修法**：

1. **用業務實體當 partition key**：把需要保序的實體 ID（訂單 ID、帳戶 ID）當 Kafka message key，同 key 雜湊到同 partition、partition 內保序，把「全域有序」收斂成「per-entity 有序」這個多數業務真正需要的粒度。
2. **辨識哪些流真的需要全序**：若某條流真的需要全域嚴格有序且無法拆成 per-entity，設單 partition topic（犧牲該 topic 的水平吞吐）；這也是個訊號 — 若大量流都需要全序，遷 Kafka 的吞吐優勢用不上、該重新評估遷移。
3. **規劃 partition 數對齊並行度跟 hot key**：partition 數決定 consumer 並行上限，同時注意熱門 key 造成的 hot partition，對位 [Kafka topic 設計](/backend/03-message-queue/vendors/kafka/)的 key 策略段。

### Case 4：Redis 既有低延遲被 Kafka 吞吐換掉，延遲敏感路徑受傷

**徵兆**：遷移後某些原本靠 Redis Streams 亞毫秒延遲的路徑（即時風控判斷、撮合前置）延遲跳到數十毫秒，下游 SLA 破線。

**根因**：Redis Streams 的亞毫秒延遲來自記憶體操作 + 行程內 data structure；Kafka 為了長期保留跟高吞吐，訊息要落磁碟、過 replication、走網路到獨立 broker，單則訊息延遲落在 5-50ms 區間，這是它換吞吐跟持久性付出的代價。把延遲敏感路徑無差別搬上 Kafka，等於用一個為吞吐優化的系統去服務一個為延遲優化的需求。

**修法**：

1. **按延遲需求分流、不要全遷**：把延遲敏感的即時路徑留在 Redis Streams（或 Redis 其他結構）、把需要長保留 / 高吞吐 / replay 的事件流遷到 Kafka，這正是 Bitso 在撮合場景堅持 Redis Streams 的理由。
2. **接受混合架構是常態**：Redis Streams 跟 Kafka 共存、各自服務適配的 workload，不追求「全部統一到 Kafka」；對位 [Kafka ↔ NATS 的混合架構是 long-term default](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 思路。
3. **若 Kafka 延遲必須壓低**：調 producer `linger.ms=0` + `acks=1`、consumer `fetch.min.bytes=1` 換取較低延遲，但這會犧牲吞吐與部分可靠性、是 trade-off 不是免費午餐。

## Migration 結構：漸進 cutover + 長期混合

這趟遷移的結構是漸進拆分而非一次性切換：先按 workload 性質分流、再對需要遷的事件流做 dual-write 並行、逐流 cutover、最終留下 Redis Streams 跟 Kafka 共存的混合架構。一次性把所有 stream 搬上 Kafka 既無必要、也會把延遲敏感路徑拖下水。

1. **Phase 0：scope 分流** — 對每條 stream 跑前面三個訊號的判讀，分成「該遷 Kafka」（retention / replay / 規模超界）跟「留 Redis Streams」（延遲敏感 / 規模在範圍內）兩類。這一步直接決定後續工作量、也避免無差別遷移。
2. **Phase 1：Kafka 叢集與 topic 設計** — 建 broker 叢集、依 Case 3 的 partition key 設計建 topic、依 Case 1 的業務需求設 retention，這時做的是基礎設施準備、還沒碰流量。
3. **Phase 2：dual-write 並行** — producer 同時寫 Redis Streams 跟 Kafka、新 consumer 接 Kafka 驗證正確性、舊 consumer 持續吃 Redis Streams，這是可逆階段、出問題退回只讀 Redis 即可。
4. **Phase 3：逐流 cutover** — 逐條 stream 把流量切到 Kafka、確認 consumer 進度（offset）跟 idempotency 都對、再停掉該 stream 的 Redis 端寫入；cutover 以 stream 為單位、不是整批。
5. **Phase 4：長期混合** — 留在 Redis Streams 的延遲敏感流跟遷到 Kafka 的事件流共存、各自運維；需要時用 bridge（消費 Redis Streams 寫入 Kafka、或反向）同步必要資料。

dual-write 階段的可逆性是這個結構的安全邊界：在 Phase 2 之前一切可退回純 Redis、Phase 3 逐流 cutover 把不可逆動作（停 Redis 寫入）切到最小粒度，單條 stream 出問題不影響其他流。

## Capacity / cost 對照

| 維度                 | Redis Streams（既有 Redis 內）        | Kafka（self-managed）                      |
| -------------------- | ------------------------------------- | ------------------------------------------ |
| 部署增量             | 近乎零（沿用 Redis 行程）             | 3-5 broker + KRaft、獨立叢集               |
| 儲存成本曲線         | RAM-bound（最貴的資源）               | 磁碟為主（便宜 1-2 數量級）+ tiered to S3  |
| Retention 上限       | 受 `maxmemory` 限制、實務數小時到數天 | 數週到數月（磁碟）、數年（tiered storage） |
| 吞吐 / 單邏輯 stream | 受單 shard 封頂                       | 多 partition 水平擴展                      |
| 延遲                 | 亞毫秒                                | 5-50ms                                     |
| 運維 FTE 增量        | 近乎零                                | 0.5-2 FTE（含 schema / connect 生態）      |
| Replay 能力          | retention 內重讀（受 RAM 限制）       | 任意 offset 重讀（受磁碟 retention 限制）  |
| 生態                 | Redis 工具鏈                          | Schema Registry / Connect / Streams        |

**判讀**：成本的核心翻轉在「儲存成本曲線」這列。Redis Streams 把資料壓在最貴的 RAM、retention 越長越貴，所以實務上被迫短保留；Kafka 把資料攤到便宜的磁碟、再分層到 S3，讓長保留變得可負擔。但這個翻轉只在「retention 需求真的長」時成立 — 若 retention 只需數小時、資料量小，Redis Streams 沒有獨立叢集跟 0.5-2 FTE 的運維增量，總成本反而低，這正是 Arcjet 的處境。遷移划不划算取決於 retention 跟規模需求落在這條曲線的哪一段。

## 整合 / 下一步

### 混合架構是常見終態

多數從 Redis Streams 起步、因規模長出 Kafka 需求的系統，終態是兩者共存而非取代：

```text
[延遲敏感即時路徑]                    [長保留 / replay / 高吞吐事件流]
   Redis Streams                              Kafka
        │                                       │
        └──────────── Bridge（雙向同步）────────┘
```

Redis Streams 服務亞毫秒延遲的即時路徑（風控、撮合前置）、Kafka 服務需要長保留與 replay 的事件流；需要打通時寫一段 bridge 同步必要 stream。這跟 [Kafka ↔ NATS 的混合架構是 long-term default](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 是同一個 paradigm shift 結論的兩個實例。

### 接上 Kafka 生態

遷到 Kafka 後可解鎖 Redis Streams 沒有的生態能力：

- Schema 治理：用 [Schema Registry](/backend/03-message-queue/vendors/kafka/) 強制 producer / consumer 契約，補上 Redis Streams 缺的 schema enforcement（對位 [Bitso 自建抽象層](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/)的紀律性責任）。
- CDC pipeline：接 [Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) 把資料庫變更流進 Kafka topic，做事件溯源主軸。
- 長期 replay：tiered storage 把冷事件分層到 S3、支援數年 replay。

### 反向確認的 tripwire

遷移後若觀察到：延遲敏感路徑 SLA 破線、Kafka 叢集運維成本超出省下的 RAM 成本、實際 retention 需求遠短於規劃 — 這些是「該遷的訊號其實不成立」的回溯訊號，應重新評估該 stream 是否該退回 Redis Streams，對位 [Arcjet](/backend/03-message-queue/cases/redis-streams-arcjet-replace-kafka/) 的成本判讀。

## 相關連結

- Source / target vendor：[Redis Streams](/backend/03-message-queue/vendors/redis-streams/) / [Kafka](/backend/03-message-queue/vendors/kafka/)
- 反向案例：[Arcjet Redis Streams 取代 Kafka](/backend/03-message-queue/cases/redis-streams-arcjet-replace-kafka/) / [Bitso Reliable Streams](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/) / [Learning.com 退場](/backend/03-message-queue/cases/redis-streams-learning-com-event-source-retreat/)
- 平行 migration playbook（同 paradigm shift）：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)
- 平行 vendor：[RabbitMQ](/backend/03-message-queue/vendors/rabbitmq/) / [NATS](/backend/03-message-queue/vendors/nats/)
- Methodology：[Migration Playbook 寫作方法論](/posts/migration-playbook-methodology/)（Type E paradigm shift）
