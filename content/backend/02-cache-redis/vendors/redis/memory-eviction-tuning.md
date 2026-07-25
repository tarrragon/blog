---
title: "Redis 記憶體與淘汰調校：maxmemory-policy、LFU 與碎片化的實戰判讀"
date: 2026-06-16
description: "Redis 的記憶體是一條會在半夜爆掉的曲線：maxmemory 設多少、policy 選 LRU 還 LFU、碎片化什麼時候開始吃掉 30% RAM、OOM 時 noeviction 怎麼讓寫入全部失敗。本文展開 Redis 記憶體會計模型、eviction policy 的選型判讀、5 個把記憶體配置寫成 production 事故的踩坑，以及單機記憶體撞牆後該往 cluster 還是 DragonflyDB 走的邊界"
weight: 14
tags: ["backend", "cache", "redis", "memory", "eviction", "deep-article"]
---

> 本文是 [Redis](/backend/02-cache-redis/vendors/redis/) overview 的 implementation-layer deep article。選型層（Redis vs Valkey vs Memcached）見 overview；本文只處理「已經選了 Redis、記憶體怎麼配才不會在尖峰爆掉」。配置以 [Redis 官方 memory optimization 文件](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/memory-optimization/) 為準、最後檢查日 2026-06-16。

## 你的 Redis 會在凌晨三點 OOM

Redis 的記憶體問題很少在有人盯著儀表板時發生。它發生在流量爬升、某個 key 集合悄悄長大、AOF rewrite 剛好撞上 RDB save 的那個瞬間——通常是凌晨三點，沒人盯著。徵兆是 application 端突然一片 `OOM command not allowed when used memory > 'maxmemory'`，所有寫入失敗，但讀取還活著，於是監控的「Redis 還在回應」綠燈騙過了 on-call。

這類事故的根因幾乎都不是「Redis 不夠快」，而是三個記憶體旋鈕在設計時被當成預設值放著沒動：`maxmemory` 設多少、`maxmemory-policy` 選哪個、以及沒人注意到的記憶體碎片化。這三個旋鈕決定了 Redis 在記憶體壓力下是「優雅地淘汰冷資料繼續服務」還是「拒絕所有寫入直到有人重啟」。本文處理這三者的會計模型、選型判讀，以及它們怎麼被寫成事故。

對延遲就是業務 KPI 的服務，這個旋鈕的代價更直接。[Tinder 的配對引擎](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)每次滑動要查多個快取（profile、距離、偏好、推薦池），4700 萬月活下 cache 不是 DB 的補救、是主要服務面，cache miss 是邊緣案例。eviction policy 選錯，淘汰掉的若是熱資料，下一次滑動就打回 origin，sub-millisecond 的延遲預算瞬間破表。

## 核心概念：Redis 記憶體的會計模型

要調校記憶體，先要分清楚 `used_memory` 這個數字到底由什麼組成。`INFO memory` 回報的是幾層疊加的記憶體會計，每一層去處不同：

**`used_memory`** 是 Redis allocator（預設 jemalloc）配給資料、結構與 buffer 的總量。**`used_memory_rss`** 是作業系統視角看到的 Redis 進程實體記憶體（resident set size），它通常大於 `used_memory`——兩者的比值就是 `mem_fragmentation_ratio`。**`used_memory_dataset`** 才是純資料的部分，扣掉了 Redis 自身的 overhead。

理解三個跟 OOM 直接相關的記憶體去處：

**資料本身的編碼會放大或縮小記憶體**。一個小 hash（field 數少於 `hash-max-listpack-entries`、value 短於 `hash-max-listpack-value`）用 listpack 緊湊編碼，記憶體可能只有大 hash 用 hashtable 編碼的幾分之一。同樣的邏輯套用在 list、set、sorted set。一個欄位設計的小決定（把 user object 拆成 200 個獨立 key 還是壓成一個 hash）會讓記憶體差好幾倍。

**client output buffer 不計入 dataset 但會吃光記憶體**。慢速 consumer、`MONITOR`、大量 pub/sub 訂閱者都會讓 Redis 在 server 端堆積 reply buffer。`client-output-buffer-limit` 沒設好，一個讀很慢的 replica 或一個掛著的 `MONITOR` 連線就能把記憶體推到 maxmemory。

**fork 期間記憶體會短暫翻倍**。RDB save 與 AOF rewrite 都靠 `fork()` + copy-on-write，父進程在 fork 後若持續寫入，被改動的 page 會被複製，最壞情況記憶體接近翻倍。這是 maxmemory 必須留 headroom 的核心原因，細節見 [persistence 與 fork latency deep article](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)。

`maxmemory` 框住的是 `used_memory`，不是 `used_memory_rss`。所以 maxmemory 設成機器 RAM 的 100% 是錯的——碎片化、fork copy-on-write、client buffer 都在 maxmemory 之外，會把 RSS 推爆系統，觸發 Linux OOM killer 直接砍掉 Redis 進程（比 Redis 自己的 noeviction 更糟，因為是無預警 SIGKILL）。

## 配置：maxmemory 與 policy 的設定路徑

設定分兩步：先框住記憶體上限，再決定撞到上限時的行為。

```bash
# 1. 設定記憶體上限（留 headroom 給 fork / fragmentation / client buffer）
# 機器 RAM 8GB → maxmemory 設 ~5-6GB、留 25-35% headroom
redis-cli CONFIG SET maxmemory 6gb

# 2. 設定撞到上限時的淘汰行為
redis-cli CONFIG SET maxmemory-policy allkeys-lfu

# 3. 永久化到 redis.conf（CONFIG SET 重啟後失效）
# redis.conf:
#   maxmemory 6gb
#   maxmemory-policy allkeys-lfu
```

八個 `maxmemory-policy` 選項分三類，選型靠「資料是不是全部都能淘汰」與「淘汰要靠存取頻率還是 TTL」兩個問題：

| policy            | 淘汰範圍      | 淘汰依據           | 適用場景                                  |
| ----------------- | ------------- | ------------------ | ----------------------------------------- |
| `noeviction`      | 不淘汰        | 寫入直接報錯       | 資料是 source-of-truth、不能丟（少見）    |
| `allkeys-lru`     | 所有 key      | 最近最少使用       | 純 cache、無法預判哪些該留                |
| `allkeys-lfu`     | 所有 key      | 最少使用頻率       | 純 cache、有明顯熱資料（多數 cache 場景） |
| `allkeys-random`  | 所有 key      | 隨機               | key 存取均勻、省 LRU/LFU 計算             |
| `volatile-lru`    | 有 TTL 的 key | 最近最少使用       | cache 與持久資料混存、只淘汰可過期的      |
| `volatile-lfu`    | 有 TTL 的 key | 最少使用頻率       | 同上、有熱資料                            |
| `volatile-random` | 有 TTL 的 key | 隨機               | 同上、省計算                              |
| `volatile-ttl`    | 有 TTL 的 key | 最接近過期的先淘汰 | 想讓近期過期的提早讓位                    |

### LRU 跟 LFU 的真實差異

`allkeys-lru` 跟 `allkeys-lfu` 看起來像同一件事的兩種寫法，但選錯會在特定 workload 下讓 hit rate 掉一截。LRU 看「最後一次被存取是多久以前」，LFU 看「被存取的頻率」。差別在一次性掃描（scan pollution）：某個批次任務一次讀過大量冷 key，LRU 會把這些剛被碰過的冷 key 排到淘汰隊伍最後面，反而把真正的熱 key 擠出去。LFU 因為看頻率，一次性的存取不會讓冷 key 假裝成熱 key。

Redis 4.0 後的 LFU 用的是 probabilistic counter（Morris counter）加 decay，不是精確計數，靠兩個參數調：

```bash
# lfu-log-factor：counter 增長的對數速度、越大越能區分高頻 key
redis-cli CONFIG SET lfu-log-factor 10
# lfu-decay-time：counter 衰減的分鐘數、越小越快遺忘舊熱度
redis-cli CONFIG SET lfu-decay-time 1
```

對 [Tinder 這類有明顯熱資料](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)（熱門 profile、熱區域推薦池）的服務，`allkeys-lfu` 比 `allkeys-lru` 更能保護熱 key 不被批次掃描或冷流量擠出。

### approximate eviction 的取樣

Redis 的 LRU/LFU 都是近似演算法，不掃全 keyspace，而是每次取樣 `maxmemory-samples` 個 key（預設 5）挑最該淘汰的。樣本數越大越接近精確 LRU/LFU，但越吃 CPU。記憶體壓力大、淘汰頻繁時，預設 5 已夠；要更精準可調到 10，代價是淘汰路徑的 CPU 上升。

## Production 故障演練

### Case 1：noeviction 讓寫入全滅、讀取假裝健康

**徵兆**：application 寫入路徑大量 `OOM command not allowed when used memory > 'maxmemory'`，但 `GET` 仍正常、health check（通常打 `PING` 或 `GET`）綠燈，on-call 收到的是 application 層的 500、不是 Redis 告警。

**根因**：`maxmemory-policy` 預設是 `noeviction`。當 Redis 把 cache 當 cache 用，但 policy 留在 `noeviction`，記憶體一滿，所有會增加記憶體的命令（`SET`、`LPUSH`、`HSET`）直接報錯，唯讀命令照常。health check 若只測讀取，完全偵測不到。

**修法**：

1. 純 cache 場景把 policy 改成 `allkeys-lru` 或 `allkeys-lfu`，讓記憶體壓力自動透過淘汰釋放
2. health check 加一個寫入探針（`SET healthcheck:probe <ts> EX 10`），讓 OOM 寫入失敗能被偵測
3. 告警掛在 `used_memory / maxmemory > 0.85`，不要等 OOM 才反應
4. 若資料真的不能淘汰（誤把 Redis 當 source-of-truth），那不該用 cache 配置，見本文 Capacity / cost 邊界段的路由判斷

### Case 2：碎片化吃掉 30% 記憶體

**徵兆**：`used_memory` 顯示 4GB、但 `used_memory_rss` 是 5.5GB，`mem_fragmentation_ratio` 是 1.37，機器 RAM 開始吃緊但資料量沒漲。重啟 Redis 後 RSS 掉回 4GB 出頭。

**根因**：大量寫入後刪除、或 value 大小頻繁變動（例如 list 一直 push/pop），jemalloc 的記憶體頁出現空洞——配出去的 page 還佔著 RSS，但裡面只有零星資料。`mem_fragmentation_ratio` 持續 > 1.5 是明確訊號。

**修法**：

1. 開 active defrag 讓 Redis 在背景整理（4.0+）：

   ```bash
   redis-cli CONFIG SET activedefrag yes
   redis-cli CONFIG SET active-defrag-ignore-bytes 100mb
   redis-cli CONFIG SET active-defrag-threshold-lower 10
   ```

2. fragmentation_ratio < 1.0 是另一種警訊——代表 Redis 在用 swap，比碎片化更危險，要立刻降記憶體壓力
3. 結構選擇上避免大幅波動的 collection；穩態大小的資料碎片化天然較低
4. 計算 maxmemory headroom 時把 1.2-1.4 的 fragmentation 算進去

### Case 3：一個 MONITOR 連線把記憶體推爆

**徵兆**：某次 debug 後記憶體莫名持續上升，`used_memory_dataset` 沒變但 `used_memory` 一直漲，`CLIENT LIST` 看到一個連線的 `omem`（output buffer memory）有幾百 MB。

**根因**：有人開了 `MONITOR` 去看即時命令流、然後忘了關（或 client crash 但連線沒斷）。`MONITOR` 把每一條命令都推給該連線，高 QPS 下 server 端 output buffer 爆量堆積，計入 `used_memory` 但不在 dataset。慢速 replica 或大量 pub/sub 訂閱者也會觸發同類問題。

**修法**：

1. 設定 client output buffer 上限，超過就斷線：

   ```bash
   # normal client / replica / pubsub 分開設
   redis-cli CONFIG SET client-output-buffer-limit "normal 256mb 64mb 60"
   redis-cli CONFIG SET client-output-buffer-limit "pubsub 32mb 8mb 60"
   ```

2. `MONITOR` 在 production 嚴格禁用或限時，它本身也拖慢整個 server
3. 監控加 `CLIENT LIST` 的 `omem` 巡檢，找出異常 buffer 的連線
4. replica lag 過大時 output buffer 會堆，對應 [replication / failover deep article](/backend/02-cache-redis/vendors/redis/sentinel-ha-failover/)

### Case 4：欄位設計讓記憶體多用三倍

**徵兆**：資料筆數跟預估一致，但 `used_memory` 是試算的 3 倍。`MEMORY USAGE <key>` 抽樣發現單筆 object 的記憶體遠超 value 本身的 byte 數。

**根因**：把一個有 10 個欄位的 user object 拆成 10 個獨立 string key（`user:123:name`、`user:123:age`...），每個 key 都帶 Redis 的 key overhead（dict entry、expire dict entry、key 字串本身）。10 個 key 的 overhead 是一個 hash 的好幾倍。反過來，超過 `hash-max-listpack-entries` 的大 hash 從緊湊的 listpack 退化成 hashtable 編碼，也會放大記憶體。

**修法**：

1. 同一 entity 的欄位用一個 hash 存，共享 key overhead
2. 保持 hash 在 listpack 閾值內以用緊湊編碼：

   ```bash
   redis-cli CONFIG GET hash-max-listpack-entries  # 預設 128
   redis-cli CONFIG GET hash-max-listpack-value    # 預設 64
   ```

3. 用 `MEMORY USAGE <key>` 跟 `redis-cli --bigkeys` 抽樣驗證實際記憶體，不靠試算
4. [Shopify 的 serialization 遷移](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)（Marshal → MessagePack）正是用更省的編碼壓 payload，欄位編碼決策對記憶體與頻寬同時有效

### Case 5：淘汰把熱 key 一起帶走、hit rate 崩

**徵兆**：記憶體壓力下開始 eviction（`evicted_keys` 持續上升），同時 `keyspace_hits / (hits + misses)` 從 95% 掉到 70%，origin QPS 跟著飆，下游 DB 開始吃緊。

**根因**：用了 `allkeys-random`，或 `allkeys-lru` 撞上批次掃描污染，淘汰演算法把熱 key 跟冷 key 一視同仁，熱 key 被淘汰後下一個請求 miss、回源、再寫回，形成淘汰與回填的拉鋸，hit rate 持續惡化。

**修法**：

1. 有明顯熱資料就用 `allkeys-lfu`，讓頻率高的 key 留下
2. 把 maxmemory-samples 調到 10 提高淘汰精準度
3. 根因常是記憶體真的不夠——`evicted_keys` 持續高代表 working set 超過 maxmemory，該擴容或分片，不是純調 policy 能解
4. 熱 key 本身過熱（單 key QPS 遠超其他）要走 local cache + Redis 兩層，對應 [2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)

## Capacity / cost 邊界

記憶體配置的容量判讀，核心是「working set 對 maxmemory 的比值」與「淘汰是否健康」：

| 訊號                      | 健康區間                     | 警戒與動作                                       |
| ------------------------- | ---------------------------- | ------------------------------------------------ |
| `used_memory / maxmemory` | < 80%                        | > 85% 告警、> 95% 接近 OOM 或大量淘汰            |
| `mem_fragmentation_ratio` | 1.0 - 1.5                    | > 1.5 開 active defrag、< 1.0 在用 swap 要救火   |
| `evicted_keys` 速率       | 接近 0（working set 放得下） | 持續高 → working set 超量、該擴容 / 分片         |
| hit rate                  | > 90%（多數 cache）          | 持續下滑 → 淘汰太兇或 TTL 太短                   |
| fork 期間 RSS 峰值        | < 機器 RAM                   | 接近 RAM → maxmemory headroom 不足、降 maxmemory |

撞牆後的路由判斷：

- **單機記憶體不夠、working set 持續超量**：垂直擴容（換更大記憶體機型）是第一步，但有單機上限。超過後走 [Redis Cluster 分片](/backend/02-cache-redis/vendors/redis/cluster-resharding/)，把 keyspace 切到多 node。
- **想用 Redis API 但要極致單機記憶體效率**：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) 的 dashtable 在同 dataset 下通常比 Redis 省 20-40% 記憶體（依資料形狀、以官方 benchmark 為準），且單機多核能撐到 Redis 要靠 cluster 才能達到的規模——若 cluster re-sharding 頻繁觸發，評估直接遷 DragonflyDB 是否更省維運。
- **資料其實不能淘汰（被當 source-of-truth）**：那它不是 cache，該走 durable store。AWS 生態下用 [MemoryDB](/backend/02-cache-redis/vendors/aws-elasticache/)（Redis-compatible durable），或把正式狀態放回 [database 模組](/backend/01-database/)。

## 整合 / 下一步

記憶體與淘汰是 Redis 運維的第一層旋鈕，但它跟其他子系統耦合：

- **跟 [persistence / fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)**：fork 期間的 copy-on-write 是 maxmemory headroom 的主要消耗者，記憶體調校跟持久化調校必須一起看。
- **跟 [TTL 與 eviction 概念](/backend/02-cache-redis/ttl-eviction/)**：TTL 設計決定哪些 key 帶過期時間，直接影響 `volatile-*` policy 的淘汰範圍。
- **跟 [cache stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)**：大量 key 同時被淘汰或同時過期會引發回源雪崩，eviction 調校要跟 TTL jitter / [singleflight](/backend/knowledge-cards/singleflight/) 一起設計。
- **跟 [Tubi 的 cache vs durable 選型](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)**：Tubi 把 ML feature store 從 ScyllaDB 遷到 ElastiCache，前提是「feature 可重新計算」——這個判斷決定了 eviction 是可接受的，記憶體調校才有意義。資料若不可重建，問題不在淘汰 policy，在選錯了儲存層。

## 相關連結

- 上游 vendor 頁：[Redis](/backend/02-cache-redis/vendors/redis/)
- 同 vendor deep article：[persistence 與 fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)、[Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
- 上游概念：[2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
