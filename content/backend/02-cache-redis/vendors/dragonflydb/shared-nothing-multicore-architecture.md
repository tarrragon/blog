---
title: "DragonflyDB shared-nothing 多核架構：用 scale-up 取代 Redis Cluster"
date: 2026-06-16
description: "Redis 要靠 Cluster 分片才能用滿一台多核機器，DragonflyDB 賭的是相反方向——單一進程 thread-per-core、shared-nothing、把單機推到 Redis 要好幾個 shard 才達到的規模。本文展開 thread-per-core 與 dashtable 的架構、fork-less snapshot、5 個把架構假設寫成 production 事故的踩坑，以及 scale-up 撞牆該回 Cluster 的邊界"
weight: 11
tags: ["backend", "cache", "dragonflydb", "multicore", "architecture", "deep-article"]
---

> 本文是 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) overview 的 implementation-layer deep article。選型層（為何選 DragonflyDB、BSL 授權、相容度）見 overview；本文只處理「決定用 DragonflyDB 後，多核架構怎麼用、相容邊界在哪」。命令實機驗證於 dragonfly df-v1.39.0（`redis_version:7.4.0`）、最後檢查日 2026-06-16；效能數字以 [DragonflyDB 官方 benchmark](https://www.dragonflydb.io/) 為準。

## scale-up 還是 scale-out：一個架構賭注

把一台 32 核機器交給 Redis，Redis 的主執行緒只用得到其中一核處理命令——要榨乾這台機器，你得在同一台上跑好幾個 Redis 進程、組成 Cluster、用 hash slot 把 key 分片。多核利用變成了一個分散式系統問題（[cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)、cross-slot transaction、hash tag 治理全都來了）。

DragonflyDB 賭的是相反方向：一個進程、thread-per-core、shared-nothing，讓單機在不分片的情況下用滿所有核。它的論點是——多數「需要 Redis Cluster」的場景，真正的需求是吞吐與記憶體，不是跨機器分散；如果單機就能撐到那個規模，Cluster 的複雜度就不必付。實機可以看到這個架構：

```bash
redis-cli INFO server | grep -E "thread_count|redis_version|dragonfly_version"
# thread_count:8               ← 自動對齊 CPU 核數
# redis_version:7.4.0          ← 對 client 裝成 Redis 7.4
# dragonfly_version:df-v1.39.0
```

`thread_count:8` 在一個進程內，不是 8 個 Redis 進程組 Cluster。這就是賭注的核心：把 Redis Cluster 的水平分片，收進單一進程的垂直多核。理解 DragonflyDB 就是理解這個賭注成立的條件與它撞牆的地方。

對高吞吐單機 workload，這個賭注有現成的對照。[Snap 在 multi-cloud 用 KeyDB](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)（Redis 的 multi-threaded fork、單實例吞吐提升 5-10x）撐超高吞吐 cache，正是「不想為了多核去組 Cluster」的同一類需求；DragonflyDB 是這條路線更激進的版本（從零用 C++ 重寫、不是在 Redis 上加 thread）。

## 核心概念：thread-per-core 與 shared-nothing

DragonflyDB 的多核不是「多個執行緒搶同一份資料」，而是把資料切給各個執行緒、彼此不共享——這是它能線性擴展到多核的關鍵。

**thread-per-core + 資料分區**。每個 thread 綁一個核，keyspace 被 hash 切成多個 slice，每個 slice 只由一個 thread 擁有。一個命令進來，被路由到擁有該 key 的 thread 處理。因為一個 key 只有一個 thread 碰，單 key 操作不需要鎖——這消除了 Redis 多執行緒方案最大的開銷（lock contention）。

**dashtable 取代 Redis 的 dict**。DragonflyDB 用自製的 dashtable（一種 hash table）取代 Redis 的 dictionary，記憶體佈局更緊湊、resize 時不需要像 Redis 那樣漸進式 rehash 全表，同樣的 dataset 通常比 Redis 省 20-40% 記憶體（依資料形狀，以官方 benchmark 為準）。

**fork-less snapshot**。Redis 的持久化靠 `fork()`，大記憶體下會凍結主執行緒並讓記憶體接近翻倍（見 [Redis persistence deep article](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)）。DragonflyDB 不用 fork——它用自己的快照演算法在不複製整個進程的前提下做一致性快照，大記憶體場景不付 fork 的延遲尖峰與記憶體翻倍代價。這是它對「fork 是 Redis 結構性瓶頸」這個痛點的直接回答。

**多執行緒的代價：沒有 Redis Cluster mode**。資料分區在單進程內，DragonflyDB 不提供 Redis Cluster mode（它的哲學是單機撐大、不跨機器分片）。這個取捨決定了它的相容邊界與容量天花板，是後面踩坑的根源。

## 配置：多核與持久化的設定路徑

```bash
docker run -d --name dragonfly -p 6379:6379 \
  docker.dragonflydb.io/dragonflydb/dragonfly \
    --threads 8 \              # thread 數、預設等於 CPU 核數（一般不需手動設）
    --maxmemory 4gb \          # 記憶體上限、行為類似 Redis maxmemory
    --cache_mode true \        # 純 cache 模式：記憶體滿時自動 evict（類似 allkeys-lru）
    --snapshot_cron "0 3 * * *" # fork-less snapshot 排程（cron 格式、這裡每天 3 點）
```

調校判讀：

- `--threads` 預設對齊 CPU 核數，多數情況不需手動設；設小於核數會浪費核，設大於核數沒有意義
- `--cache_mode true` 讓 DragonflyDB 在記憶體滿時自動淘汰（純 cache 行為）；不開則記憶體滿時拒絕寫入（類似 Redis noeviction）
- `--maxmemory` 留 headroom，但因為 fork-less，headroom 不需要像 Redis 留那麼多給 fork copy-on-write
- snapshot 用 `--snapshot_cron` 排程，fork-less 機制讓大記憶體快照不產生延遲尖峰

## Production 故障演練

### Case 1：client 配 Cluster mode、連不上

**徵兆**：從 Redis Cluster 遷來，application 的 client library 還配著 cluster mode，連 DragonflyDB 報錯或 hang，`CLUSTER` 相關命令行為不如預期。

**根因**：DragonflyDB 不提供 Redis Cluster mode（單進程多核、不跨機器分片）。cluster-aware client 會嘗試 `CLUSTER SLOTS` 之類的拓樸發現，跟 standalone 的 DragonflyDB 對不上。

**修法**：

1. client 改回 standalone 配置（不要 cluster mode）
2. 評估原本用 Cluster 的理由：若是為了多核吞吐，DragonflyDB 單進程多核已涵蓋，不需要 cluster mode
3. 若原本用 Cluster 是為了超過單機的容量 / 跨機器分散，DragonflyDB 的 scale-up 模型撐不住，該留在 [Redis Cluster](/backend/02-cache-redis/vendors/redis/cluster-resharding/)
4. 確認 application 沒有依賴 cluster-specific 行為（hash tag 的跨 slot 語意等）

### Case 2：某些 Redis 命令 / module 不支援

**徵兆**：核心 SET/GET/HASH 等正常，但某個命令報 `unknown command` 或行為跟 Redis 不同，特別是 module 命令（RedisJSON / RedisSearch）與部分冷門命令。

**根因**：DragonflyDB 相容大多數 Redis 命令但不是 100%；它宣稱相容 `redis_version:7.4.0`，但部分 module、部分冷門命令、部分 Lua 行為有差異。

**修法**：

1. 遷移前盤點 application 用到的命令，對照 DragonflyDB 的 API 相容清單（官方 docs）
2. module 重度依賴（RedisJSON / RedisSearch）要特別確認——DragonflyDB 的 module 生態比 Redis 淺
3. Lua script 行為差異要實測，不要假設跟 Redis 完全一致
4. 相容性是遷移的主要風險，跟 [Valkey 的相容性驗證](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)同理但 DragonflyDB 邊界更寬（重寫而非 fork）

### Case 3：thread 沒對齊核數、多核優勢沒發揮

**徵兆**：吞吐沒有達到預期、CPU 使用率不均（部分核閒置），`thread_count` 跟機器核數對不上。

**根因**：`--threads` 被手動設成小於 CPU 核數，或容器的 CPU limit 限制了實際可用核數，DragonflyDB 沒能用滿所有核。

**修法**：

1. `redis-cli INFO server | grep thread_count` 確認 thread 數對齊實體核數
2. 容器環境確認 CPU limit 沒有卡住 DragonflyDB 的核數（cgroup CPU quota）
3. 不要手動把 `--threads` 設小，預設對齊核數就是最佳
4. 吞吐沒到預期也可能是 workload 本身（大命令、網路 RTT），用 [連線 / pipeline](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/) 的 RTT 分析交叉判斷

### Case 4：跨 partition 的多 key 操作有額外成本

**徵兆**：大量多 key 命令（MGET 跨很多 key、跨 key 的 Lua）的延遲比預期高，單 key 操作則很快。

**根因**：shared-nothing 下 key 分散在不同 thread，多 key 操作要跨 thread 協調——單 key 免鎖的好處在多 key 跨 partition 時要付協調成本。這跟 Redis Cluster 的 cross-slot 是類似的本質（資料分散的代價），只是發生在單進程內。

**修法**：

1. 高頻的多 key 操作盡量讓 key 落在同 partition（DragonflyDB 的 key 分布規則）
2. 評估能否用單 key 結構（hash）取代多個 key 的聚合
3. 跨 partition 協調是分區架構的固有成本，不是 bug，量大時要設計繞過
4. 對照 [Redis Cluster 的 cross-slot 限制](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)，兩者都是「資料分散換吞吐」的代價

### Case 5：BSL 授權踩到商業使用限制

**徵兆**：準備把 DragonflyDB 包成對外的 managed service 提供給客戶，法務 review 卡關。

**根因**：DragonflyDB 用 BSL（Business Source License），商業使用受限——具體限制是不可把 DragonflyDB 當成 managed service 對外提供（4 年後該版本轉 Apache 2.0）。內部使用無限制，但 SaaS 對外提供 DragonflyDB 即服務受限。

**修法**：

1. 內部使用（多數企業場景）無限制，直接用
2. 要把 DragonflyDB 當 managed service 對外賣，聯絡 DragonflyDB 取得商業 license
3. 開源合規敏感（公部門 / 企業 OSI 政策）走 OSI 認可的 [Valkey](/backend/02-cache-redis/vendors/valkey/)（BSD）
4. 授權法律解讀諮詢法務，不要憑技術判斷

## Capacity / cost 邊界

DragonflyDB 的容量判讀，核心在 scale-up 的天花板與多核效率：

| 訊號                  | 健康區間                     | 警戒與動作                                       |
| --------------------- | ---------------------------- | ------------------------------------------------ |
| `thread_count`        | = CPU 實體核數               | < 核數 → 沒用滿多核、查 --threads / cgroup       |
| 單機吞吐              | 遠高於單 Redis 進程          | 撞單機網路 / CPU 上限 → scale-up 到頂            |
| 記憶體效率            | 比 Redis 省 20-40%（依形狀） | 以官方 benchmark + 自己量為準                    |
| snapshot 延遲尖峰     | 接近 0（fork-less）          | 有尖峰 → 確認用的是 DragonflyDB 快照不是相容路徑 |
| 單機容量 / 跨 AZ 需求 | 單機 + replica 撐得住        | 超單機 / 要跨機器分散 → DragonflyDB 撐不住       |

撞牆後的路由判斷：

- **超過單機容量、需要跨機器分散**：DragonflyDB 的 scale-up 賭注在這裡輸——它沒有 Cluster mode。要跨機器分片走 [Redis / Valkey Cluster](/backend/02-cache-redis/vendors/redis/cluster-resharding/)。
- **需要 OSI 認可開源授權**：BSL 不是 OSI 認可，合規敏感走 [Valkey](/backend/02-cache-redis/vendors/valkey/)（BSD）。
- **不想自管**：DragonflyDB 目前沒有 fully managed offering（無 ElastiCache for Dragonfly），必須自管。要 managed 走 [ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)（Redis / Valkey / Memcached）。
- **跨 AZ / 跨 region HA**：DragonflyDB 有 replica 模式（primary-replica）跨 AZ 可行，但跨 region 需自建——大規模跨區走 managed 的 Global Datastore。

## 整合 / 下一步

DragonflyDB 的定位是「Redis 相容 + 激進多核」，它在 Redis 相容服務的光譜上有明確座標：

- **跟 [Valkey](/backend/02-cache-redis/vendors/valkey/)**：兩者都打「Redis 相容 + 更好的多核」，但 Valkey 是 fork（同源、最高相容、漸進加 thread），DragonflyDB 是 C++ 重寫（相容核心但架構激進、多核更徹底）。相容度要極致選 Valkey，多核吞吐要極致選 DragonflyDB。
- **跟 KeyDB / Garnet**：KeyDB 是 Redis 的 multi-threaded fork（[Snap 採用](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)、Snap 收購後相對停滯）；Garnet 是 Microsoft 的研究型高吞吐 store（生態淺）。DragonflyDB 是這個「高吞吐 Redis 替代」群裡商業化最積極、生態最活躍的。
- **跟 [Redis Cluster re-sharding](/backend/02-cache-redis/vendors/redis/cluster-resharding/)**：如果你的 Redis Cluster re-sharding 頻繁觸發、運維負擔重，DragonflyDB 的 scale-up 模型可能用單機取代整個 Cluster——這是評估遷移的主要動機。
- **跟 [Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)**：write-through 在 DragonflyDB 上行為一致，但單進程多核能承接比單 Redis 進程更大的 throughput，是 read-heavy + write-through 場景的 scale-up 選項。

## 相關連結

- 上游 vendor 頁：[DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)
- 對照 vendor：[Valkey 相容性與 io-threads](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)、[Redis persistence 與 fork latency](/backend/02-cache-redis/vendors/redis/persistence-fork-latency/)（fork-less 對照的痛點）
- 相關 migration：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)
- Methodology：[Vendor 深度技術文章寫作方法論](/posts/vendor-deep-article-methodology/)
