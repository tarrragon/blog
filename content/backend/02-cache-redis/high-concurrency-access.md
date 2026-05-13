---
title: "2.1 高併發下的 Redis 讀寫邊界"
date: 2026-04-22
description: "說明高併發服務如何共用 Redis client、控制 pipeline 與避免 cache stampede"
weight: 1
tags: ["backend", "cache"]
---

Redis 在後端服務裡常扮演 cache、session、counter、dedup、presence 或輕量協調層。它通常比 SQL 更適合高併發短操作，但前提是 client、連線池、pipeline 與 key 設計都受控。高併發下的 Redis 仍然會遇到 [hot key](/backend/knowledge-cards/hot-key/)、快取穿透、stampede、過大 pipeline 與不當鎖設計。

## 本章目標

學完本章後，你將能夠：

1. 理解為什麼 Redis client 應該共用
2. 分辨單鍵操作、pipeline、[transaction](/backend/knowledge-cards/transaction/) 與 Lua 的邊界
3. 了解高併發下的 [cache stampede](/backend/knowledge-cards/cache-stampede/) 與 hot key 問題
4. 用 `context` 與 [timeout](/backend/knowledge-cards/timeout/) 保護 Redis 呼叫
5. 把 Redis 用在適合的資料角色，並保留正式狀態來源

---

## 【觀察】Redis 呼叫大多是短網路 I/O

應用端對 Redis 的操作通常是短小但頻繁的網路請求。這代表真正影響效能的往往是 RTT、連線重用、批次送出與 key 設計。

所以高併發時，重點是控制 Redis 邊界：

- 用同一個 client 共用連線池
- 對獨立操作使用合理的 pipeline
- 熱門資料要避免集中到單一 key

## 【判讀】client 共用比每次建立更重要

Redis client 的核心設計通常就是讓應用共用同一個實例。每個 request 都 new client，會把連線管理成本、握手成本與資源回收問題全部放大。

高併發服務通常會採用：

- process 啟動時建立一個 Redis client
- request handler、worker、service layer 共用它
- 所有操作都帶 `context`
- timeout 與取消由上層傳入

## 【策略】pipeline 用來節省 RTT

pipeline 的價值是把多個獨立命令一次送出，減少往返次數。它很適合：

- 多個彼此獨立的讀取
- 批次寫入
- 一次更新多個 cache key

pipeline 的核心限制是批次大小仍要受控。太大的 pipeline 會帶來：

- 內存壓力
- 回應延遲變大
- 單次失敗影響更多操作

## 【判讀】原子性需求要分清楚

Redis 的很多操作本身就可以很快，但原子性與一致性需要額外設計。當需求需要多個資料變更形成同一個結果時，才應該考慮：

- 單鍵原子操作
- transaction
- Lua script
- 由上層做去重或補償

transaction 應服務明確的一致性需求，cache 寫入也應維持輔助狀態定位。Redis 很常是輔助狀態，真正的 [source of truth](/backend/knowledge-cards/source-of-truth/) 通常還是在 SQL 或 domain store。

## 【策略】cache stampede 與 hot key 要先處理

高併發快取最常見的兩個問題，是大量 goroutine 同時 [miss](/backend/knowledge-cards/cache-hit-miss/) 同一筆資料，以及大量流量打到同一個 key。

### cache stampede

當 cache miss 發生時，如果每個 request 都直接回源查 DB，會把後端放大成更大的壓力。常見的處理方式包括：

- 設定合理 [TTL](/backend/knowledge-cards/ttl/)
- 加 single-flight 類型的去重
- 讓部分請求等待同一批重建結果
- 對重建失敗設退避或短暫保護

### hot key

如果某些 key 過度熱門，壓力會集中到 Redis 甚至單一 shard。處理方式通常是：

- 拆 key 或拆資料粒度
- 讓讀取走多層 cache
- 降低單點依賴
- 在應用端做短暫本地快取或節流

## Cache 在規模化服務的角色變化

Cache 在小規模服務扮演「DB 補救」、在規模化服務變成「主要服務面」— cache miss 從常態變成邊緣案例。理解這個角色變化是 cache 容量規劃跟一致性設計的前置。

對應 [9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) — 4700 萬 MAU 配對引擎、每次滑動查多個 cache（用戶 profile、距離、偏好過濾、推薦池），cache lookup 是 critical path、不是優化。對應 [9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML inference 之前的 feature lookup 用 ElastiCache、cache miss 路徑（回到 ScyllaDB 或重算）延遲會跳到 100ms+、超過用戶體驗門檻。

判讀含義：

- **角色 = DB 補救**（小型）：cache miss 可接受、回源即可、不必設計 stampede 防護
- **角色 = 主要服務面**（規模化）：cache miss 是事故、要設計 cache warmup、singleflight、降級
- **角色 = 資料平面**（Meta TAO / Netflix EVCache 等級）：cache 變成跨區資料層、不再只是 *DB 前面的一層*、要設計跨區一致性窗口跟資料模型治理。對應 [2.C8 Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/) 跟 [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)。

角色變化是 *規模* 引起的、不是 *選擇*。當服務每次互動都查多個 cache、cache hit rate 變成業務 KPI、cache layer 已自然變成主要服務面、不能繼續用 DB 補救心態設計。

## Cache 容量規劃跟 DB 不一樣

Cache 容量規劃跟 DB 容量規劃用不同基準。DB 容量受 *total dataset size* 影響（要存所有資料）；cache 容量受 *working set size* 影響（只存熱資料）。兩者的擴容邏輯、成本曲線、評估指標都不同。

對應 [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) — 47M MAU sustained growth、容量規劃變成「每月線性擴容 X%」的長期決策、不是峰值規劃。對應 [2.C4 Meta CacheLib / Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) — 當熱資料超過 DRAM 經濟範圍、單層 cache 同時遇到成本跟命中率瓶頸、要分層（DRAM + flash）。

**Cache 容量規劃的三個維度**：

- **Working set size**：熱資料大小、決定 cache 需要多少 RAM。要監控 *hot key 分布* 跟 *resident set growth*。
- **命中率目標**：90% / 95% / 99% 對應不同 cache 大小。每加一個 9 需要的 cache size 通常翻倍。
- **回源 budget**：cache miss 後 origin（DB / 重算）能承受多少 QPS。命中率掉 5% 可能讓 origin QPS 翻 5 倍。

**判讀重點**：cache 命中率變化是 *業務變化訊號*、不一定是 cache capacity 問題。突然命中率掉、可能是新功能影響 access pattern（推薦演算法改、查詢條件擴大、tenant 結構變化）、要先看業務側、再考慮加 cache。

## Redis 規模化的單執行緒邊界

Redis 7 之前是 single-threaded、單實例吞吐受 CPU 單核限制（通常 100K-200K ops/sec）。規模化服務遇到這個邊界時、四個選項：

1. **拆 cluster**（應用層分散 key）：Redis Cluster 自帶分片、適合 key 數量多、單 key 不熱的場景。每 shard 仍 single-threaded、但總吞吐線性擴展。
2. **Redis 7+ I/O thread**：保留 Redis protocol、I/O 處理 multi-threaded、command 執行仍 single-threaded。提升 ~2-3x throughput、適合 I/O bound workload。
3. **KeyDB / Dragonfly**（multi-threaded fork）：command 執行也 multi-threaded、單實例吞吐提升 5-10x。對應 [9.C35 Snap KeyDB](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) — 大型用戶採用 KeyDB 在 GCP 上替代原生 Redis。代價是 vendor lock-in 跟 fork 走向不確定。
4. **Memcached**（multi-threaded、功能少）：純 KV 不支援複雜資料結構、適合 cache-only 場景。

**規模化常用組合**：ElastiCache for Redis 7.1（[r7g.4xlarge 單節點 ~100 萬 RPS](https://aws.amazon.com/blogs/database/achieve-over-500-million-requests-per-second-per-cluster-with-amazon-elasticache-for-redis-7-1/)、單 cluster 5 億 RPS）+ Cluster 模式 + 應用層 connection multiplexing。對應 [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 的設計。

判讀順序：先確認 *是不是* 單實例吞吐瓶頸（看 CPU 單核滿載 vs 整體 RAM / network）、再選方案。應用層 key 分布不均（hot key）跟 single-threaded 限制是兩回事、混在一起會誤選方案。

## 【執行】把 Redis 用在對的角色

Redis 在高併發場景常見角色有：

- cache
- session store
- counter / [rate limit](/backend/knowledge-cards/rate-limit/)
- presence / online state
- dedup / [idempotency](/backend/knowledge-cards/idempotency/) key
- lightweight [queue](/backend/knowledge-cards/queue/) / stream

每一種角色都有不同容錯方式。counter、presence 和 cache 的失敗語意各自不同，因此需要依資料角色選擇處理策略。

## 【策略】分散式 lock 要謹慎使用

Redis 常被拿來做 distributed lock，但這類機制要非常清楚 lease、過期、持有者與失效風險。高併發下最怕的是鎖住之後沒有安全釋放，或以為鎖保證了完整業務一致性。

原則上：

- 鎖應該短
- 鎖持有者要可辨識
- 鎖過期要可接受
- 業務上若能不用分散式鎖，通常應優先考慮更簡單的設計

## 【延伸】語言端仍然要負責限流與取消

Redis 很快，但應用端仍然要設計邊界。語言端應使用 timeout、cancellation、[worker pool](/backend/knowledge-cards/worker-pool/)、rate limit 或 [backpressure](/backend/knowledge-cards/backpressure/) 把壓力收斂起來；否則排隊等待 Redis 回應的工作會越堆越多。

## 跨語言適配評估

Redis 高併發邊界會受語言 runtime 影響。Thread-based runtime 要管理 client pool 與 blocking command；async runtime 要確認 Redis client 不會阻塞 event loop；輕量 task runtime 要限制同時呼叫 Redis 的工作數量。動態語言要特別控制 cache value schema 與序列化格式；強型別語言要避免把內部型別直接當成跨服務 cache [contract](/backend/knowledge-cards/contract/)。

## 案例對照

| 案例                                                                                                  | 高併發 cache 場景重點                                           |
| ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) | 47M MAU 配對引擎、cache 是主要服務面、sustained growth 成本曲線 |
| [9.C25 Tubi feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) | ML inference 之前 feature lookup、p99 < 10ms 是業務 KPI         |
| [9.C35 Snap KeyDB](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/)                | KeyDB multi-threaded fork、單實例吞吐 5-10x、跨 cloud 部署      |
| [2.C8 Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)                 | cache 成為資料層能力、社交圖查詢的快取治理                      |
| [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)             | 跨區分散式 cache、平台層基礎設施                                |
| [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)               | client 散落邏輯收斂到路由層、跨叢集 cache 路由                  |

## 小結

高併發服務處理 Redis 的核心原則是：client 共用、操作要短、pipeline 要有節制、熱點 key 要設計、cache miss 要防 stampede、鎖要保守使用。規模化後 cache 從 *DB 補救* 變成 *主要服務面* 再變成 *資料平面*、容量規劃要按 working set size 跟命中率目標、不能套用 DB 規劃邏輯。Redis 規模化的單執行緒邊界有四個選項（cluster / Redis 7+ I/O thread / KeyDB / Memcached）、判讀順序是先確認瓶頸再選方案。
