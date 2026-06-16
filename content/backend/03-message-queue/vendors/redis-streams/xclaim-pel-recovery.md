---
title: "Redis Streams XCLAIM / PEL 失敗接管與 Cluster 影響"
date: 2026-06-16
description: "Redis Streams 把可靠性責任放在 application 層：PEL 記錄已投遞未 ack 的訊息、XCLAIM / XAUTOCLAIM 是 consumer crash 後唯一的接管機制。本文用實機輸出走 PEL / XACK / XCLAIM / XAUTOCLAIM / min-idle-time 機制、5 個故障演練（PEL 卡死、搶單、MAXLEN 修掉未 ack 訊息、Cluster 單 shard 限制、failover 後 PEL 狀態），跟 MAXLEN / XTRIM retention 取捨。"
weight: 12
tags: ["backend", "message-queue", "redis-streams", "xclaim", "pel", "consumer-group", "deep-article"]
---

> 本文是 [Redis Streams](/backend/03-message-queue/vendors/redis-streams/) overview 的 implementation-layer deep article。Overview 給選型與最短路徑、本文聚焦「consumer crash 之後、卡在 PEL 的訊息怎麼回到處理流程」這條 implementation flow。實機輸出來自 `redis:7`（7.4.9）單節點。

## consumer crash 後、訊息卡在哪裡

Redis Streams 的 consumer group 設計是「先投遞、後 ack」：`XREADGROUP` 把 entry 投給某個 consumer 的同時、entry 進入該 group 的 **PEL（Pending Entries List）**、標記為「已投遞、未確認」。consumer 處理完才呼叫 `XACK` 把 entry 移出 PEL。這一段「已投遞未 ack」的視窗、是 Redis Streams 提供 at-least-once 的全部依據。

問題在於 consumer crash 時機落在這個視窗內。consumer 已經拿到訊息、PEL 已經記了它的名字、但它在 ack 之前就死了。Redis 沒有 broker 級的「重新投遞」背景程序——不像 RabbitMQ consumer 斷線後 unacked 訊息自動 requeue。Redis 把這筆訊息留在 PEL、owner 仍是那個死掉的 consumer、然後什麼都不做。要讓這筆訊息回到處理流程、只有 application 主動呼叫 `XCLAIM` 或 `XAUTOCLAIM` 改寫 owner。

這就是 [Bitso 自建 Reliable Streams 抽象](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/) 揭露的核心事實：Redis Streams 是「資料結構」、不是「broker 系統」、可靠性責任在 application 層。本文展開的就是這個責任的具體形狀——PEL 怎麼累積、怎麼判讀、接管機制怎麼運作、以及哪些操作會讓接管失效。

## PEL 機制：XREADGROUP 進、XACK 出

PEL 是 per-group 的結構、記錄每個 entry 的四個欄位：entry ID、目前 owner consumer、idle time（距上次投遞的毫秒數）、delivery count（被投遞過幾次）。先用實機輸出建立基礎。寫入 5 筆、建 group、兩個 consumer 各讀一部分：

```bash
$ redis-cli XADD mystream '*' event order_1 amount 100
1781584105202-0
# ... order_2 ~ order_5、各得遞增 entry ID

$ redis-cli XGROUP CREATE mystream g1 0
OK

$ redis-cli XREADGROUP GROUP g1 c1 COUNT 3 STREAMS mystream '>'
# c1 拿到 order_1 / order_2 / order_3
$ redis-cli XREADGROUP GROUP g1 c2 COUNT 10 STREAMS mystream '>'
# c2 拿到 order_4 / order_5
```

`'>'` 代表「只取從未投遞給本 group 的新訊息」。投遞後這 5 筆全進 PEL。`XPENDING` 的 summary 形式給總覽：

```bash
$ redis-cli XPENDING mystream g1
5                  # PEL 總數
1781584105202-0    # 最小 pending ID
1781584105578-0    # 最大 pending ID
c1                 # 各 consumer 的 pending 數
3
c2
2
```

5 筆全在 PEL、c1 扛 3 筆、c2 扛 2 筆。展開形式 `XPENDING <key> <group> - + <count>` 給每筆細節：

```bash
$ redis-cli XPENDING mystream g1 - + 10
1781584105202-0  c1  6318  1    # entry ID / owner / idle ms / delivery count
1781584105278-0  c1  6318  1
1781584105373-0  c1  6318  1
1781584105466-0  c2  6224  1
1781584105578-0  c2  6224  1
```

`idle` 是 6318ms（距投遞已過 6.3 秒）、`delivery count` 都是 1（只投過一次）。這兩個數字是後面接管決策的核心輸入：idle 判斷「owner 是不是死了」、delivery count 判斷「這筆是不是 [poison message](/backend/knowledge-cards/poison-message-quarantine/)」。

`XACK` 把處理完的 entry 移出 PEL：

```bash
$ redis-cli XACK mystream g1 1781584105202-0
1                  # 成功移除 1 筆

$ redis-cli XPENDING mystream g1
4                  # PEL 剩 4 筆
1781584105278-0
1781584105578-0
c1
2
c2
2
```

PEL 從 5 降到 4。判讀原則固定：**PEL 持續成長就是 consumer 健康訊號異常**——不是 crash 沒 ack、就是處理速度跟不上、再不然是 ACK 程式碼漏寫。三者用 idle time 區分：crash 的 entry idle 會單調成長、處理慢的 idle 在 timeout 附近震盪、漏 ACK 的 entry delivery count 停在 1 但 idle 無上限成長。

## XCLAIM 與 XAUTOCLAIM：改寫 owner 的兩條路

接管的本質是把 PEL entry 的 owner 從死掉的 consumer 改成活著的 consumer。`XCLAIM` 是手動指定 entry ID 接管、`XAUTOCLAIM` 是自動掃 idle 超過門檻的 entry 批次接管。兩者都接受 min-idle-time 參數當安全閥。

`XCLAIM <key> <group> <new-consumer> <min-idle-time> <id...>`：把指定 entry 改判給新 consumer、條件是該 entry 的 idle 已達 min-idle-time。下面用 min-idle-time 0（無條件接管）把 c1 的一筆轉給 c3：

```bash
$ redis-cli XCLAIM mystream g1 c3 0 1781584105278-0
1781584105278-0
event
order_2
amount
200               # 回傳被接管 entry 的完整內容

$ redis-cli XPENDING mystream g1 - + 10
1781584105278-0  c3  66     2    # owner 變 c3、idle 歸零(66ms)、delivery count 升到 2
1781584105373-0  c1  14590  1
1781584105466-0  c2  14496  1
1781584105578-0  c2  14496  1
```

接管後三件事同時發生：owner 改成 c3、idle 重置（剛 claim、66ms）、**delivery count 從 1 升到 2**。delivery count 自增是接管機制留下的審計軌跡——一筆訊息 delivery count 累積到 5、10、代表它反覆被接管又反覆沒處理完、這就是 poison message 的訊號、該路由到隔離區（見 [recovery semantics](/backend/knowledge-cards/recovery-semantics/) 與 [poison message quarantine](/backend/knowledge-cards/poison-message-quarantine/)）。

`XAUTOCLAIM <key> <group> <new-consumer> <min-idle-time> <start-id>`（Redis 6.2+）省掉「先 XPENDING 找 ID、再逐筆 XCLAIM」兩步、一次掃描接管：

```bash
$ redis-cli XAUTOCLAIM mystream g1 c3 0 0
0-0                          # 下次掃描的 cursor（0-0 代表掃完一輪）
1781584105278-0 ...          # 接管的 entry 內容（order_2）
1781584105373-0 ...          # order_3
1781584105466-0 ...          # order_4
1781584105578-0 ...          # order_5
(empty array)                # 第三個回傳值：已從 stream 刪除的 entry ID 清單

$ redis-cli XPENDING mystream g1
4
1781584105278-0
1781584105578-0
c3                           # 全部 4 筆 owner 變 c3
4
```

一次呼叫把整個 group 的 idle 訊息全歸到 c3。`XAUTOCLAIM` 是 consumer crash 後接管的主力——consumer 在啟動或處理迴圈裡固定跑一輪 `XAUTOCLAIM`、把孤兒訊息撿回來。回傳的 cursor 支援分批（一次掃不完時帶 cursor 續掃）、第三個回傳值（被刪 entry 清單）對應後面 MAXLEN 修剪的故障。

## min-idle-time：防止活 consumer 被搶單

min-idle-time 不是裝飾參數、是接管機制的安全閥：它要求「只有 idle 超過門檻的 entry 才能被接管」。沒有這個門檻、兩個 consumer 會互相搶對方正在處理的訊息。

驗證搶單防護——剛被 c3 claim 的訊息 idle 很低、用 60 秒門檻去 claim 會落空：

```bash
$ redis-cli XCLAIM mystream g1 c4 60000 1781584105278-0
(empty array)               # 回空：該 entry idle 未達 60000ms、c4 搶不到
```

回空陣列代表 claim 失敗、owner 不變、訊息留在 c3 手上。這就是 min-idle-time 的作用：**門檻 = 我願意相信 owner consumer 還活著的最長時間**。

門檻設定是接管設計的核心取捨、沒有通用值、由訊息處理時間分佈決定。門檻設太短、正常處理中的訊息被當成孤兒搶走、變成多 consumer 重複處理同一筆——這正是 [Harness event-driven 案例](/backend/03-message-queue/cases/redis-streams-harness-event-driven-state/) 揭露的 XAUTOCLAIM head-of-line 風險。門檻設太長、真正 crash 的訊息要等很久才有人接管、recovery 延遲拉高。實務基準是「門檻 > p99 處理時間 + 安全係數」：若單筆處理 p99 是 2 秒、門檻設 30-60 秒、確保只有真的死掉（遠超正常處理時間）的 owner 才被接管。

接管後仍需 application 層去重。XCLAIM 改寫 owner、不代表原 consumer 真的沒處理完——它可能正在 ack 的瞬間被 claim、結果兩邊都處理一次。at-least-once 的去重責任永遠在 application、靠 [idempotency](/backend/knowledge-cards/idempotency/) 兜底、這跟接管門檻設多準無關。

## Memory 與 retention：MAXLEN / XTRIM 的取捨

Stream 是 append-only、不主動丟資料、佔用的 Redis 記憶體單調成長。retention 的唯一旋鈕是修剪：`MAXLEN`（保留最近 N 筆）或 `MINID`（保留 ID 大於某值的 entry）。可以在 `XADD` 寫入時順帶修剪、也可以用 `XTRIM` 獨立執行。

精確修剪 `MAXLEN =` 跟近似修剪 `MAXLEN ~` 的差別在性能。stream 內部是 radix tree of macro-nodes（每個 node 打包多筆 entry）。精確修剪要拆 node 才能剛好留 N 筆、近似修剪只刪「整個可以丟掉的 node」、留下的筆數會略多於 N、但省掉拆 node 的開銷。`~` 是 production 預設、`=` 只在需要嚴格上限時用：

```bash
$ redis-cli XADD mystream MAXLEN '~' 1000 '*' event order_6 amount 600
1781584152570-0             # 近似修剪：超過 ~1000 才整 node 刪
$ redis-cli XADD mystream MAXLEN '=' 3 '*' event order_7 amount 700
1781584152871-0
$ redis-cli XLEN mystream
3                           # 精確修剪到剛好 3 筆
```

stream 不受 `maxmemory-policy` eviction 管理——一般 key 在記憶體壓力下會被 evict、stream entry 不會。這代表 stream 是「只進不出、除非主動修剪」的記憶體成長源。[Learning.com 把 Redis Streams 當長期事件儲存、最後壓垮 Redis](/backend/03-message-queue/cases/redis-streams-learning-com-event-source-retreat/) 就是沒設修剪上限的反例：retention 沒上限、記憶體一路漲到 OOM。判讀訊號是 `MEMORY USAGE mystream` 對比實例 `maxmemory`、超過預算就調低 MAXLEN。

## 故障演練

### Case 1：consumer crash 後 PEL 訊息卡死沒人接

**徵兆**：`XPENDING` 總數持續成長、某個 consumer 的 pending 數停在固定值不降、那些 entry 的 idle time 單調往上爬（幾分鐘、幾小時）、業務端對應的訊息「進了 stream 但沒被處理」。

**根因**：consumer 進程 crash（OOM kill / 部署滾動 / panic）、留下的 PEL entry owner 仍是死掉的 consumer。Redis 不會自動重投——沒有任何背景程序會碰這些 entry。它們會永遠卡在 PEL、直到有人主動接管。新啟動的 consumer 用 `XREADGROUP ... '>'` 只會拿到「從未投遞」的新訊息、不會碰到前任留下的孤兒。

**修法**：consumer 啟動時跟處理迴圈裡固定跑 `XAUTOCLAIM`、把超過 idle 門檻的孤兒撿回來：

```bash
# 每個 consumer 週期性執行、min-idle-time 設 60s
$ redis-cli XAUTOCLAIM mystream g1 self_consumer_id 60000 0
```

1. **min-idle-time 設成 > p99 處理時間 + 安全係數**：避免把處理中的訊息誤判成孤兒（接 Case 2）。
2. **用回傳 cursor 分批掃**：PEL 大時一次 `XAUTOCLAIM` 不掃完、帶 cursor 續掃、避免單次 block 太久。
3. **接管後檢查 delivery count**：超過閾值（如 5）的 entry 不再處理、路由到 DLQ（Redis Streams 沒原生 DLQ、Bitso 自建一個 stream 當 DLQ）。
4. **監控 PEL 最大 idle**：alert 設在「最老 pending entry 的 idle 超過 N 倍接管門檻」、代表接管機制本身停了。

### Case 2：min-idle-time 設太短、活 consumer 被搶單

**徵兆**：同一筆訊息被多個 consumer 處理、下游出現重複副作用（重複扣款、重複發信）；`XPENDING` 展開看到某些 entry 的 delivery count 異常高（5、10+）但 stream 流量正常、沒有 consumer crash。

**根因**：接管門檻低於正常處理時間。consumer A 拿到一筆要處理 10 秒的訊息、門檻設了 5 秒、consumer B 跑 `XAUTOCLAIM` 時這筆 idle 已過 5 秒、B 把還在 A 手上處理的訊息搶走、兩邊都處理一次。這是 [Harness 案例](/backend/03-message-queue/cases/redis-streams-harness-event-driven-state/) 的 XAUTOCLAIM head-of-line 問題——一筆慢訊息被反覆搶、delivery count 暴衝、卻沒人真正完成。

**修法**：

1. **量測真實處理時間分佈、門檻設 > p99**：先用 metric 抓單筆處理 p50 / p99、門檻設 p99 的數倍。
2. **delivery count 當搶單偵測器**：同一 entry delivery count 快速成長、代表它在被搶來搶去、調高門檻或隔離該訊息。
3. **idempotency 兜底**：門檻再準也防不了「ack 瞬間被 claim」的競態、application 層去重是最後防線、不可省（見 [idempotency 卡](/backend/knowledge-cards/idempotency/)）。

### Case 3：MAXLEN 修剪掉 PEL 內還沒 ack 的訊息

**徵兆**：`XPENDING` 顯示某些 entry 仍 pending、但 `XCLAIM` 接管它時拿不到內容；consumer 接手後發現訊息 body 是空的、無法處理、又無法判斷該不該 ack。

**根因**：**修剪只看 entry ID 的新舊、不看它在不在 PEL**。`XTRIM MAXLEN` 把最舊的 entry 從 stream 物理刪除、即使這些 entry 還在某個 group 的 PEL 裡等 ack。PEL 只記 entry ID、不存 body；body 存在 stream 本體。entry 被 trim 掉、PEL 還記得這個 ID、但 body 已經不存在了。實機驗證——4 筆全在 PEL、把 stream 修剪到剩 2 筆：

```bash
$ redis-cli XLEN mystream
5
$ redis-cli XPENDING mystream g1
4                           # 4 筆未 ack 在 PEL

$ redis-cli XTRIM mystream MAXLEN 2
3                           # 刪掉 3 筆（含 PEL 內的未 ack entry）
$ redis-cli XLEN mystream
2

$ redis-cli XPENDING mystream g1 - + 10
1781584105278-0  c3  19307  3   # PEL 還記得這些 ID
1781584105373-0  c3  19307  2
1781584105466-0  c3  19307  2
1781584105578-0  c3  19307  2

$ redis-cli XCLAIM mystream g1 c5 0 1781584105278-0
(empty array)               # 接管成功改 owner、但 entry body 已被 trim、拿不到內容
```

PEL 還有 4 筆記錄、但對應的 body 已從 stream 消失。`XCLAIM` 接管這種 entry、改得了 owner、拿不到 body——這是訊息靜默遺失。

**修法**：

1. **修剪上限要 > 處理 backlog 深度**：MAXLEN / 流入速率 = 訊息在被修剪前的最長存活時間、這個時間要遠大於「最慢 consumer 清空 backlog 的時間」。
2. **修剪前檢查 PEL 最舊 ID**：自動修剪前比對 `XPENDING` 的最小 pending ID、確保不會修到還在 PEL 的 entry。
3. **慢 consumer 監控優先於積極修剪**：先解決 consumer 處理太慢導致 PEL 積壓的根因、再談用小 MAXLEN 壓記憶體；倒過來只會修掉未 ack 訊息。
4. **MINID 修剪比 MAXLEN 安全**：MINID 用時間/業務邊界（如「保留 24 小時內」）、比 MAXLEN 的「保留 N 筆」更容易保證涵蓋未 ack 視窗。

### Case 4：Redis Cluster 對單 stream 的 shard 限制

**徵兆**：stream 流量成長到單 node 容量上限、想像 Kafka 那樣「加 partition 分流」、卻發現 Redis Cluster 沒有這個機制；單一 stream key 的全部讀寫永遠打在同一個 node。

**根因**：Redis Cluster 用 `CRC16(key) % 16384` 把 key 映射到 slot、slot 分佈在 node 上。**一個 stream 是一個 key、永遠落在單一 slot、永遠在單一 shard**。Streams 沒有 Kafka partition 那種「同一 topic 切多片、分散到多 broker」的概念。單 stream 的吞吐天花板就是單 node 的天花板。

實機驗證 keyslot 計算（cluster-enabled 節點）：

```bash
$ redis-cli CLUSTER KEYSLOT stream:orders
6139
$ redis-cli CLUSTER KEYSLOT stream:payments
3696                        # 不同 key 落不同 slot、可能在不同 shard
```

**修法**：要分流就在 application 層切多個 stream key（`stream:orders:0`、`stream:orders:1` ...）、自己做 partition 路由。若需要某幾個 stream 保證落同一 shard（為了跨 stream 的原子操作或 co-located 處理）、用 hash tag——只有 `{}` 內的部分參與 CRC16：

```bash
$ redis-cli CLUSTER KEYSLOT '{shard1}:stream:orders'
10271
$ redis-cli CLUSTER KEYSLOT '{shard1}:stream:payments'
10271                       # 同 hash tag、強制落同 slot
```

兩個不同 key 因為共用 `{shard1}` hash tag、CRC16 算出同一個 slot 10271、保證在同一 shard。判讀邊界：需要真正的 partition + replication + 跨節點水平擴展、Redis Streams 不是答案、改走 [Kafka](/backend/03-message-queue/vendors/kafka/)。Redis Streams 的定位是中等規模、單 shard 容量內、不跨節點分片。

> Cluster 多節點分片下的端到端行為（resharding 期間 stream key 隨 slot 搬移、client topology cache）需要多節點環境、本文未實機驗證；slot migration 機制與踩雷見 [Redis Cluster Re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)。

### Case 5：failover 後 PEL 狀態不一致

**徵兆**：Sentinel / Cluster failover 後（replica 升 primary）、原本在 PEL 的部分訊息「消失」或「重複投遞」；`XPENDING` 數字跟 failover 前對不上；consumer 接管邏輯撿到不該撿的訊息、或漏撿該撿的。

**根因**：Redis 的 replication 是非同步的。primary 上的 `XADD` / `XACK` / `XCLAIM` 先在本地生效、再非同步傳給 replica。failover 那一刻、replica 的 PEL 狀態落後 primary 一個 replication lag 的視窗。新 primary 從它當下的（落後的）PEL 狀態接手：lag 視窗內已 ack 的訊息在新 primary 上仍 pending（重複投遞）、lag 視窗內剛 claim 的 owner 改寫可能丟失（接管邏輯錯亂）。AOF / RDB 持久化只保證單機重啟的恢復、不改變跨 replica 的非同步本質。

> failover 對 PEL 一致性的影響需要多節點 Sentinel / Cluster 環境跨節點觀測、本文未實機驗證；以下依官方 replication 語義與案例敘述判讀。

**修法**：

1. **接受 at-least-once、靠 idempotency 收斂**：failover 造成的重複投遞跟正常的重複投遞同一性質、application 去重邏輯本來就要處理（見 [idempotency 卡](/backend/knowledge-cards/idempotency/)）。
2. **failover 後主動全量 XAUTOCLAIM 對帳**：failover 偵測到後、consumer 跑一輪低門檻 `XAUTOCLAIM` 重新接管、用 application 端的處理紀錄判斷哪些真的沒處理。
3. **降低 replication lag**：lag 越小、failover 視窗的 PEL 偏差越小；監控 `master_repl_offset` 與 replica offset 差。
4. **語義誤配風險**：把 Redis Streams 當「不丟訊息的 broker」用、在 failover 邊界會破功——這是 [3.C9 語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/) 的思路、選型時就要認清 Redis Streams 的一致性等級。

## Capacity 與判讀路由

| 維度                | 判讀訊號                                        | 邊界                                                 |
| ------------------- | ----------------------------------------------- | ---------------------------------------------------- |
| PEL 深度            | `XPENDING` 總數持續成長                         | 成長不停 = consumer 健康問題、不是調 MAXLEN 能解     |
| 接管門檻            | delivery count 異常高（搶單）/ 最老 idle 不收斂 | 門檻 > p99 處理時間 + 安全係數                       |
| Stream 記憶體       | `MEMORY USAGE` 對比 `maxmemory`                 | stream 不被 eviction、唯一旋鈕是 MAXLEN / MINID 修剪 |
| 修剪 vs 未 ack 視窗 | 修剪上限 / 流入速率 < backlog 清空時間          | 違反就會修掉 PEL 內未 ack 訊息（Case 3）             |
| 單 stream 吞吐      | 單 node CPU / memory 打滿、無法加 partition     | 達單 shard 天花板 = 該評估 Kafka                     |

判讀路由固定三層：先看 PEL 是「整 group 成長」（流入 > 處理、擴 consumer）還是「單 consumer 卡住」（crash、要接管）；接管時先確認 min-idle-time 對得上處理時間分佈、再看 delivery count 篩 poison message；retention 調整前先確認修剪上限涵蓋 PEL 未 ack 視窗。

## 整合與下一步

接管機制是 [consumer 設計](/backend/03-message-queue/consumer-design/) 在 Redis Streams 上的具體落地——consumer 不只是讀訊息的迴圈、還要承擔「撿前任孤兒」的責任。設計 consumer 時把 `XAUTOCLAIM` 排進處理迴圈、跟 `XREADGROUP '>'` 並列、不是事後補丁。

知識卡對位：delivery count 超閾值的訊息對應 [poison message quarantine](/backend/knowledge-cards/poison-message-quarantine/)（Redis Streams 沒原生 DLQ、自建一個 stream 當隔離區）；接管後的去重對應 [recovery semantics](/backend/knowledge-cards/recovery-semantics/) 跟 [idempotency](/backend/knowledge-cards/idempotency/)（at-least-once 的收斂責任在 application）。

案例延伸：[Bitso](/backend/03-message-queue/cases/redis-streams-bitso-reliable-streams/) 把本文這些機制封裝成 Reliable Streams 抽象層 + 自建 DLQ、是「application 層補可靠性」的完整實作參考；[Klaxit Rust + Logplex](/backend/03-message-queue/cases/redis-streams-klaxit-rust-log-pipeline/) 是高吞吐 log ingestion 下 consumer group 分流長時間穩定運轉的範例；接管門檻搶單的反面教訓在 [Harness event-driven](/backend/03-message-queue/cases/redis-streams-harness-event-driven-state/)。

選型回路：單 stream 撞到單 shard 天花板、或 failover 一致性要求超出 at-least-once、回 [Redis Streams overview 的「何時改走其他服務」](/backend/03-message-queue/vendors/redis-streams/#何時改走其他服務)、評估 [Kafka](/backend/03-message-queue/vendors/kafka/)（partition + replication）。Cluster 層的 slot / topology 行為見 [Redis Cluster Re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)。
