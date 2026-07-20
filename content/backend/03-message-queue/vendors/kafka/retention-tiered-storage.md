---
title: "Kafka Retention 與 Tiered Storage：保留策略、log compaction 與冷熱分層"
date: 2026-06-16
description: "Kafka 的保留策略決定 replay window 與儲存成本：retention.ms / retention.bytes 控制刪除邊界、cleanup.policy 切換 delete 與 compact、log compaction 用最新值取代歷史、tiered storage 把冷資料卸到 S3 讓 broker 容量與保留期解耦。本文涵蓋配置實機驗證、4 個故障演練（replay 失敗 / compaction 不回收磁碟 / cold tier 讀延遲 / retention.bytes 提早刪）、容量成本與整合路由。"
weight: 13
tags: ["backend", "message-queue", "kafka", "retention", "tiered-storage", "log-compaction", "deep-article"]
---

> 本文是 [Kafka](/backend/03-message-queue/vendors/kafka/) overview 的 implementation-layer deep article、聚焦保留與分層儲存。選型層的「該不該選 Kafka」「跟其他 broker 差在哪」見 overview；本文回答「保留策略怎麼設、log compaction 怎麼運作、冷熱分層怎麼讓容量跟保留期解耦、踩哪些坑」。配置段在 Apache Kafka KRaft 單節點實機驗證；tiered storage 段標註未實機驗證的範圍。

## Retention 是 replay window 的物理邊界

Retention 的核心責任是決定「一筆訊息在 broker 上能存活多久」、而這條邊界直接界定 consumer 能往回重播多遠。Kafka 的 log 是 append-only 的事件序列、訊息寫入後不會被原地修改；retention 是唯一會把舊訊息從磁碟移除的機制。設多久、用什麼條件刪、刪掉之後 consumer 還能不能讀到，全由保留策略決定。

這條邊界之所以重要、是因為 Kafka 的多 consumer 模型讓「重播」變成一級能力。同一個 [topic](/backend/knowledge-cards/topic/) 可以被多組 consumer 各自從任意 [offset](/backend/knowledge-cards/offset/) 開始讀、每組維護自己的進度；只要訊息還在 retention 範圍內、新加入的 consumer 或出事後要補算的 consumer 都能從頭重讀。一旦訊息超過 retention 被刪、[replay window](/backend/knowledge-cards/replay-window/) 就到此為止、補償只能改走資料庫或上游來源。

Kafka 提供兩條獨立的保留軸、可單獨用也可同時用：

| 配置              | 觸發條件                                    | 典型場景                                   |
| ----------------- | ------------------------------------------- | ------------------------------------------ |
| `retention.ms`    | 訊息寫入時間超過設定值（時間軸）            | 「保留 7 天事件供事故 replay」             |
| `retention.bytes` | 該 partition log 總大小超過設定值（容量軸） | 「每 partition 上限 50 GB、防止磁碟塞爆」  |
| 兩者同時設        | 任一條件先達到就刪（取交集、誰先到誰生效）  | 「保留 7 天、但單 partition 不超過 50 GB」 |

時間軸對齊的是 replay 需求：把 retention 設成「事故從發生到偵測到修復的最長時間」、確保發現要補算時事件還在。容量軸對齊的是成本與磁碟保護：避免某個突發高流量 topic 把 broker 磁碟寫滿、拖垮同 broker 上其他 partition。兩者同時設時是「誰先觸發誰生效」、所以容量軸常常會在高流量時段提前砍掉本來預期能保留 7 天的事件——這個交互是後面故障演練的重點之一。

實機建立一個同時設兩軸的 topic、`--describe` 會把保留配置直接列在 Configs：

```bash
# CLI 在容器內 /opt/kafka/bin/、bootstrap-server 指向 broker
kafka-topics.sh --create --topic ret-delete --partitions 1 \
  --config retention.ms=60000 \
  --config retention.bytes=10485760 \
  --config segment.ms=10000 \
  --bootstrap-server localhost:9092

kafka-topics.sh --describe --topic ret-delete --bootstrap-server localhost:9092
# Configs: retention.ms=60000,retention.bytes=10485760,segment.ms=10000,...
```

retention 不是寫死在建 topic 當下、線上可以用 `kafka-configs.sh --alter` 動態調整、立即生效不需重啟 broker：

```bash
kafka-configs.sh --alter --entity-type topics --entity-name ret-delete \
  --add-config retention.ms=3600000 \
  --bootstrap-server localhost:9092
# Completed updating config for topic ret-delete.

kafka-configs.sh --describe --entity-type topics --entity-name ret-delete \
  --bootstrap-server localhost:9092
# retention.ms=3600000 sensitive=false synonyms={DYNAMIC_TOPIC_CONFIG:retention.ms=3600000}
```

動態調整的 retention 屬於 `DYNAMIC_TOPIC_CONFIG`、優先於 broker 層的 `log.retention.*` 預設值；synonyms 欄位會把覆蓋關係列出來、排查時可確認當前生效的是哪一層。

## Segment 是刪除的最小單位

Retention 刪資料的最小單位是 log segment、不是單筆訊息。理解這一點才能解釋「為什麼設了 retention.ms 之後，過期的訊息有時還在」。每個 partition 的 log 在磁碟上被切成多個 segment 檔、只有 active segment（當前正在寫入的那一個）以外、已經 roll over 的 segment 才會被 retention 檢查並整段刪除。

Segment 何時 roll over 由兩個條件決定：`segment.bytes`（檔案大到上限、預設 1 GB、最小 1 MB）或 `segment.ms`（檔案存在時間超過設定）。實機寫入 ~6 MB 資料到一個 `segment.bytes=1048576`（1 MB）的 topic、磁碟上會看到 6 個 roll 過的 segment：

```text
00000000000000000000.log   1045229   # 已 roll，可被 retention 刪
00000000000000001024.log   1046336   # 已 roll
00000000000000002048.log   1046336   # 已 roll
00000000000000003072.log   1046336   # 已 roll
00000000000000004096.log   1037748   # 已 roll
00000000000000005112.log    904737   # active segment，不會被刪
```

Retention 的實際刪除動作由背景執行緒週期性執行、頻率是 broker 層的 `log.retention.check.interval.ms`、預設 300000 毫秒（5 分鐘）。這代表「過期」跟「被刪」之間有最長一個檢查週期的延遲：訊息超過 retention.ms 的瞬間不會立刻消失、要等下一次檢查跑到、且該訊息所在的 segment 已經 roll over、整段才會被刪。實機把 retention.bytes 設成 2 MB、寫進 6 MB（6 個 segment）、在 5 分鐘檢查週期內查 earliest offset 仍是 0——超量的 segment 還沒被回收、因為檢查執行緒還沒跑到下一輪。

這個機制有兩個操作後果。其一、磁碟用量會在「超過 retention 上限」到「下一次檢查」之間短暫超標、容量規劃要把這段 overshoot 算進緩衝。其二、把 retention.ms 設得比 segment.ms 還短沒有意義：訊息要等所在 segment roll 才可能被刪、active segment 永遠刪不掉、所以實際最短保留時間是 `max(retention.ms, segment 尚未 roll 的時間)`。

## cleanup.policy：delete 與 compact 是兩種回收語意

`cleanup.policy` 決定 retention 用哪種語意回收空間、是保留策略最關鍵的分岔。預設值 `delete` 是時間或容量到期就整段刪除、適合事件流（event stream）：訊息代表「發生過的事實」、過了 replay window 就沒有保留價值。另一個值 `compact` 是 log compaction、語意完全不同：它保留每個 key 的最新值、刪除同 key 的歷史版本、適合「狀態快照」型資料。

兩者的判準是這份 log 表達的是「事件序列」還是「最終狀態」。訂單建立、付款完成、商品瀏覽這類事件、每一筆都是獨立事實、用 `delete`；使用者個人設定、商品庫存當前值、CDC 同步出來的資料表鏡像這類「同一個 key 不斷被覆寫、只關心最新值」的資料、用 `compact`。Kafka 內部的 `__consumer_offsets` topic 就是 compact——它只需要每個 consumer group 的最新 offset、不需要歷史 commit 記錄。

兩者可以同時開（`cleanup.policy=compact,delete`）：先按 key 壓縮保留最新值、同時對壓縮後的結果再套時間 / 容量上限。用 `kafka-configs.sh` 切換時、逗號分隔的值要用中括號群組、否則會被解析成兩個獨立 config：

```bash
kafka-configs.sh --alter --entity-type topics --entity-name ret-delete \
  --add-config 'cleanup.policy=[compact,delete]' \
  --bootstrap-server localhost:9092
# Completed updating config for topic ret-delete.
# describe: cleanup.policy=compact,delete
```

## Log compaction 用最新值取代歷史

Log compaction 的核心責任是讓一個 topic 收斂成「每個 key 的最新狀態」、同時保有 Kafka 的 log 重播能力。它的運作方式是背景的 log cleaner 執行緒掃描已 roll 的 segment、對每個 key 只保留 offset 最大的那筆、把同 key 的舊版本標記移除、再把存活的記錄重寫成新 segment。Compaction 後、新加入的 consumer 從頭讀一次、拿到的就是整個 keyspace 的最新快照、而非完整變更歷史。

實機驗證最直接：建一個 compact topic、對 3 個 key 各寫 2 個版本（舊值在前、新值在後）、等 compaction 跑完、從頭消費：

```bash
kafka-topics.sh --create --topic ret-compact --partitions 1 \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.01 \
  --config segment.ms=5000 \
  --config delete.retention.ms=100 \
  --bootstrap-server localhost:9092

# 寫 k1/k2/k3 各舊值一筆、再各新值一筆（key:value 用冒號分隔）
printf 'k1:v1-old\nk2:v1-old\nk3:v1-old\nk1:v2-new\nk2:v2-new\nk3:v2-new\n' | \
  kafka-console-producer.sh --topic ret-compact \
  --property parse.key=true --property key.separator=: \
  --bootstrap-server localhost:9092

# 等 segment roll + compaction，再從頭消費
kafka-console-consumer.sh --topic ret-compact --from-beginning \
  --property print.key=true --property print.offset=true \
  --timeout-ms 6000 --bootstrap-server localhost:9092
# Offset:3  k1  v2-new
# Offset:4  k2  v2-new
# Offset:5  k3  v2-new
```

寫進 6 筆、從頭只讀到 3 筆——k1/k2/k3 的 `v1-old`（offset 0-2）被壓縮移除、只留每個 key 的 `v2-new`。關鍵細節：offset 沒有重新編號、留存記錄保留原始 offset（3、4、5）、log 的位置語意不變、其他 consumer 的 offset 進度不會錯位。

Compaction 的觸發不是即時的、由幾個參數共同決定。`min.cleanable.dirty.ratio` 是「髒比例」門檻、髒記錄（已被新版本取代但還沒清掉的舊版本）佔 log 比例超過這個值、cleaner 才會處理該 partition、預設 0.5（驗證時調成 0.01 加速觸發）。`segment.ms` 控制 active segment 多久 roll、只有 roll 過的 segment 能被 compact。`delete.retention.ms` 控制 tombstone（value 為 null 的刪除標記）保留多久——compaction topic 用 null value 表示「這個 key 已刪除」、tombstone 要保留夠久讓所有 consumer 都讀到刪除事件、之後才清掉。

Tombstone 是 compaction 表達「刪除」的方式：寫一筆 key 存在、value 為 null 的記錄、compaction 會把該 key 的所有歷史連同這筆 tombstone 在 `delete.retention.ms` 之後一起清除。這讓 compact topic 能表達「key 從存在到被刪」的完整生命週期、而不只是「永遠累積最新值」。

## Tiered Storage 讓容量與保留期解耦

> 以下 tiered storage 段落依 Apache Kafka 官方文件（KIP-405）與 Pinterest / LinkedIn 公開案例敘述、未在本文的 KRaft 單節點環境實機驗證。Apache Kafka 的原生 tiered storage（`remote.storage.enable`）在當前版本屬 early-access、需要額外的 RemoteStorageManager plugin 與 broker 設定；正式採用前以官方文件版本標註為準。

Tiered storage 的核心責任是把 broker 的「儲存容量」跟「保留期長度」解耦。傳統 Kafka 的保留期受限於 broker 本機磁碟：想保留 30 天、就得讓每個 broker 的 local disk 容納 30 天的全量資料、retention 拉長等於 broker 數量或單機磁碟線性增長、而 broker 的 CPU / 記憶體 / 網路其實沒用到那麼多。Tiered storage 把 log 分成兩層：熱資料（近期、頻繁讀）留在 broker local disk（local tier）、冷資料（過期門檻之外、偶爾 replay）卸載到遠端物件儲存如 S3（remote tier）。Broker 只需放得下熱資料、保留期可以拉到數月甚至更久、成本變成 S3 的物件儲存費而非 broker 機群。

分層的觸發由 `local.retention.ms` / `local.retention.bytes`（本機保留多久 / 多大、超過就卸到 remote）跟整體的 `retention.ms` / `retention.bytes`（含 remote 的總保留邊界、超過才真正刪除）共同界定。一筆訊息的生命週期變成：寫入 local tier、超過 local retention 卸到 remote tier、超過整體 retention 從 remote 刪除。Replay window 因此可以遠大於 broker local disk 容量。

讀取路徑分熱冷兩條、效能特性不同。Consumer 讀近期 offset、資料在 local tier、走的是 Kafka 一向的 page cache + 順序讀路徑、低延遲高吞吐。Consumer 讀很舊的 offset（例如出事後從幾週前重播）、資料在 remote tier、broker 要先從 S3 把對應 segment 拉回來才能 serve、第一次讀的延遲明顯高於熱路徑、吞吐受 S3 頻寬與 broker 拉取並行度限制。這個熱冷讀差異是 tiered storage 的核心取捨——也是故障演練要處理的場景。

業界對 tiered storage 有兩條不同的工程路線、對應不同的 broker 角色定位：

| 路線                           | broker 角色                              | 代表案例                                                                                          |
| ------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Broker-coupled（KIP-405 原生） | broker 仍是 remote 讀的熱路徑、代理拉取  | Apache Kafka 原生 tiered storage                                                                  |
| Broker-decoupled               | consumer 直接從 S3 拉、broker 不在熱路徑 | [3.C11 Pinterest Tiered Storage](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/) |

[Pinterest 的 broker-decoupled 做法](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/)把 ~200 TB/day 熱資料卸到 S3、讓 consumer 直接從 S3 拉冷資料、broker 不再是冷讀的熱路徑。它揭露的設計判讀是「broker 運算資源」跟「跨 AZ 網路成本」其實該分開治理、而不是綁在 broker 容量擴張上——保留期變長不該等於 broker 機群變大。

[LinkedIn 的分層叢集策略](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)是另一個層次的「分層」：把不同業務特性與可靠性需求的 workload 拆到不同叢集（依關鍵程度分群、例如關鍵 / 一般 / 實驗性，分層名稱為示意而非案例原文用詞）、避免混在同一叢集時故障與資源競爭互相放大。這裡的「分層」指叢集隔離、不是儲存的冷熱分層。兩種「分層」常被混談、但解的是不同問題：tiered storage 解單一 topic 的儲存成本、tiered clusters 解多 workload 的隔離治理。

## 故障演練

### Retention 太短、replay window 不夠補事故

**徵兆**：下游 consumer 出 bug、產出錯誤的衍生資料、幾天後才被[對帳](/backend/knowledge-cards/data-reconciliation/)發現；要從原始事件重播修復時、發現最舊的事件已經被刪、replay 從某個時間點之後才有資料、之前的修不回來。

**根因**：retention.ms 設得比「事故從發生到偵測到開始修復的最長時間」短。Replay window 由 broker retention 與 consumer checkpoint 共同界定、retention 是其物理上限；偵測延遲一旦超過 retention、要補算時原始事件已過期。常見的隱性誘因是把 retention 按「正常 consumer 跟得上的進度」來設（例如 consumer 通常落後幾分鐘、就設 1 天保險）、卻沒按「最壞情況下多久才會發現問題」來設。

**修法**：

1. 把 retention.ms 對齊事故偵測到修復的最長時間、而非 consumer 正常落後量；對帳 / 審計類 pipeline 的偵測週期常以天計、retention 要跟著拉到對應天數。
2. 對「偵測延遲可能很長」的關鍵 topic、在下游另留可重算的來源（資料庫快照、上游 source of truth）、不把 Kafka retention 當唯一補償依據。
3. 用 `kafka-configs.sh --alter` 動態延長 retention 是即時生效的、但只對「還沒被刪」的訊息有用——已刪的救不回來；所以調整要趁事故升級前、發現偵測週期被低估的當下就改、不是等出事才改。
4. Replay 邊界對齊見 [3.7 Event Contract 與 Replay Boundary](/backend/03-message-queue/event-contract-replay-boundary/)：replay 要能指定 time range、超出 retention 的 time range 直接無效。

### Compaction 開了、磁碟卻沒回收

**徵兆**：topic 設了 `cleanup.policy=compact`、預期同 key 舊版本會被清掉、磁碟用量卻持續上漲、`--describe` 看 partition log 一直變大；從頭消費仍讀到大量同 key 的歷史版本。

**根因**：compaction 觸發條件沒滿足。log cleaner 只處理已 roll 的 segment、active segment 永遠不壓縮；`min.cleanable.dirty.ratio` 預設 0.5、髒比例沒到一半 cleaner 不動手；如果寫入集中在少數 key、active segment 遲遲不 roll（segment.bytes / segment.ms 都沒到）、髒記錄全積在 active segment 裡、compaction 看不到它們。另一個常見原因是 broker 的 log cleaner 執行緒數（`log.cleaner.threads`）不足以跟上高寫入量、cleaner backlog 累積。

**修法**：

1. 確認 active segment 會適時 roll：對寫入量不大但需要及時壓縮的 topic、設 `segment.ms`（例如數小時）強制 roll、讓髒記錄離開 active segment 進入可壓縮範圍。
2. 視壓縮急迫度調 `min.cleanable.dirty.ratio`：要更積極壓縮就調低（驗證時用 0.01）、但調太低會讓 cleaner 頻繁重寫 segment、增加 I/O——這是壓縮及時性跟 cleaner 開銷的取捨。
3. 監控 cleaner backlog：看 broker 的 `log-cleaner` 相關 metric、backlog 持續成長代表 cleaner 執行緒不夠、加 `log.cleaner.threads`。
4. 確認沒有把 compact 用在「其實該 delete」的事件流上——事件流每筆 key 多半唯一、compaction 沒有舊版本可壓、磁碟自然不會降；那種情況該用 `delete` 加 retention。

### Cold tier 讀延遲拖垮 replay

**徵兆**：開了 tiered storage、平時讀近期資料正常、一旦發起從幾週前的舊 offset 大規模 replay、consumer 的吞吐驟降、p99 拉取延遲飆高、broker S3 拉取頻寬打滿、同 broker 上其他正常 consumer 也跟著受影響。

**根因**：舊 offset 的資料在 remote tier、每次讀要先從 S3 把 segment 拉回 broker、第一次冷讀延遲遠高於 local tier 的順序讀。大規模 replay 等於一次要從 S3 拉大量冷 segment、S3 頻寬與 broker 拉取並行成為瓶頸；broker-coupled 架構下這些拉取流量全經過 broker、會排擠到熱路徑的正常服務。

**修法**：

1. 把大規模冷 replay 排到低流量時段、避免跟線上熱路徑爭 broker 資源與 S3 頻寬。
2. 控制 replay 的並行度與範圍：依 [replay boundary](/backend/03-message-queue/event-contract-replay-boundary/) 指定 time range / tenant / partition、分批拉冷資料、不要一次全量回放整個保留期。
3. 評估 broker-decoupled 架構（如 [Pinterest 做法](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/)）：consumer 直接從 S3 拉冷資料、把冷讀流量從 broker 熱路徑移開、保護線上服務。
4. 容量規劃把「冷讀延遲」算進 RTO：replay window 拉很長能補很久以前的事故、但補的速度受 cold tier 吞吐限制、事故修復時間估算要把這段拉取時間算進去。

### retention.bytes 在高流量時段提早刪

**徵兆**：retention.ms 明明設了 7 天、某次流量突增後、consumer 卻發現幾小時前的事件就已經被刪、replay 拿不到本該還在的資料；earliest offset 在沒人預期的時候大幅前移。

**根因**：retention.ms 與 retention.bytes 同時設時是「誰先觸發誰生效」。流量突增讓 partition log 在遠不到 7 天時就撞到 retention.bytes 容量上限、容量軸先觸發、舊 segment 被提前刪除——時間軸的 7 天承諾在高流量下失效。常見於「按平均流量估容量上限、卻遇到尖峰流量」、或多個 topic 共享磁碟時為了保護磁碟把每 topic 容量上限壓得偏低。

**修法**：

1. 釐清這個 topic 的保留承諾是時間還是容量主導：以 replay window 為準的關鍵 topic、容量上限要按「尖峰流量 × 保留天數」估、而非平均流量、否則尖峰時容量軸會偷走時間承諾。
2. 監控 earliest offset 與 log 大小的變化率：earliest offset 在非預期時間前移、就是 retention.bytes 提前觸發的訊號、加進告警。
3. 要硬保證時間保留、就把 retention.bytes 設成 -1（不限容量、純時間軸）、改用獨立的磁碟告警與容量規劃來防磁碟塞爆、而不是用 retention.bytes 兼做兩件事。
4. 評估 tiered storage：把保留壓力從 broker local disk 移到 remote tier、local 只留熱資料、就不必為了保護 broker 磁碟而把 retention.bytes 壓低、時間承諾不再被容量上限侵蝕。

## 容量與成本

| 維度               | 估算與判讀                                                            | 警戒                                            |
| ------------------ | --------------------------------------------------------------------- | ----------------------------------------------- |
| Local disk 用量    | partition 數 × 單 partition log 大小 × replication factor             | 接近磁碟上限時 retention.bytes 會提前砍時間承諾 |
| 保留期 vs 成本     | 純 local 時 retention 線性推高 broker 磁碟成本                        | 數月保留 + 純 local = broker 機群為冷資料買單   |
| Tiered remote 成本 | S3 物件儲存費 + 冷讀時的拉取 / egress 流量費                          | 跨 AZ / 跨 region 冷讀 egress 成本易被低估      |
| Retention 檢查延遲 | 過期到實際刪除最長一個 `log.retention.check.interval.ms`（預設 5 分） | 容量規劃要預留 overshoot 緩衝                   |
| Compaction 開銷    | cleaner 重寫 segment 的 I/O、隨 dirty.ratio 調低而上升                | dirty.ratio 過低 = cleaner 頻繁重寫、I/O 壓力升 |
| Cold replay 吞吐   | 受 remote tier（S3）頻寬與 broker 拉取並行度限制                      | 大規模 cold replay 排低流量時段、分批進行       |

實務 default：

- 事件流 topic 用 `delete`、retention.ms 對齊事故偵測到修復的最長時間、retention.bytes 設 -1 或按尖峰流量估、不讓容量軸偷走時間承諾。
- 狀態快照 / CDC 鏡像 topic 用 `compact`、確認 active segment 會適時 roll、監控 cleaner backlog。
- 需要長保留期（數月以上）且 broker 磁碟成本敏感時、評估 tiered storage、把冷資料移到 S3、broker 只放熱資料。
- 任何 retention 調整前先確認當前生效層級（`kafka-configs.sh --describe` 看 synonyms）、避免 broker 預設與 topic 動態配置混淆。

## 整合與下一步

### 跟 replay 邊界對齊

Retention 是 [replay window](/backend/knowledge-cards/replay-window/) 的物理上限、但 replay 能不能正確執行還要看 [event contract](/backend/03-message-queue/event-contract-replay-boundary/) 是否齊備（event id / schema version / occurred time / dedup key）。保留策略設計要跟 [3.7 Event Contract 與 Replay Boundary](/backend/03-message-queue/event-contract-replay-boundary/) 一起看：retention 決定「能不能讀到」、event contract 決定「讀到了能不能正確重播」、兩者缺一 replay 都不成立。相關概念見 [retention](/backend/knowledge-cards/retention/) 與 [offset](/backend/knowledge-cards/offset/) 知識卡。

### 跟分層叢集治理對位

本文的 tiered storage 解的是單一 topic 的儲存成本；[3.C4 LinkedIn 分層叢集](/backend/03-message-queue/cases/linkedin-kafka-tiered-clusters/)解的是多 workload 的隔離——把不同可靠性需求的 topic 拆到不同叢集、避免資源競爭互相放大。保留策略在分層叢集裡會按層差異化：critical 叢集拉長 retention 保 replay、experimental 叢集縮短 retention 控成本。

### 跟 broker-decoupled 架構的取捨

[3.C11 Pinterest broker-decoupled tiered storage](/backend/03-message-queue/cases/kafka-pinterest-tiered-storage/) 把冷讀流量從 broker 熱路徑移開、是「cold tier 讀延遲拖垮 replay」故障演練的架構級解法；它跟 [3.C12 Pinterest Shallow Mirror](/backend/03-message-queue/cases/kafka-pinterest-shallow-mirror/) 揭露的「跨區同步是 CPU + memory + 網路三維壓力」一起、構成 Pinterest 在儲存與複製兩條路徑上的成本治理。

### 回上游

- 上游 vendor 頁：[Apache Kafka](/backend/03-message-queue/vendors/kafka/)（「Tiered storage」與「Cross-region 與分層叢集」段）
- 平行 deep article：[consumer rebalance 與 lag 診斷](/backend/03-message-queue/vendors/kafka/) / [replication、ISR 與 exactly-once](/backend/03-message-queue/vendors/kafka/)（同 vendor 其他實作層議題）
- 下游能力：[3.4 consumer 設計](/backend/03-message-queue/consumer-design/) / [6.12 idempotency / replay](/backend/06-reliability/idempotency-replay/)
