---
title: "Redis"
date: 2026-05-01
description: "OSS in-memory data structure store、cache 主流"
weight: 1
tags: ["backend", "cache", "vendor"]
---

Redis 是 in-memory data structure store、承擔三個責任：cache serving layer（with eviction）、data structure operation（string / hash / list / sorted set / stream / hyperloglog / geo）、輕量持久化（AOF / RDB）。設計取捨偏向「記憶體優先 + data type rich + 可選持久化」、cache 是主用場、但 data type 讓它跨入 session store / counter / leaderboard / lock 等場景。2024 起授權變動為 RSALv2 / SSPL（OSI 不認）、引發 Valkey fork。

對「通用快取、session store、rate limit counter、leaderboard、distributed lock」這條路徑、Redis 是事實標準。本頁先給最短路徑、再展開日常 CLI / API 與 key 設計、最後進階治理（cluster / persistence / modules）跟排錯。

## 本章目標

讀完本章後、你應該能：

1. 用 docker 跑起 Redis、用 redis-cli 驗證
2. 用 SET / GET / EXPIRE / DEL / KEYS 操作、區分 6 大 data types 適用場景
3. 設計 key naming + TTL + eviction policy 對齊 cache miss 行為
4. 看懂 hit rate / memory pressure / eviction / replication lag 訊號
5. 評估 Cluster vs Sentinel、AOF/RDB、modules、授權變動下的選擇

## 最短路徑：5 分鐘把 Redis 跑起來

```bash
# 1. 啟動 Redis
# TODO: docker run -d --name redis -p 6379:6379 redis:7

# 2. 連線
# TODO: docker exec -it redis redis-cli

# 3. 驗證 SET / GET / EXPIRE
# TODO: SET foo bar / GET foo / EXPIRE foo 60 / TTL foo
```

最短路徑驗證「Redis 起來、能讀寫 + TTL」。實際應用見[日常操作](#日常操作與決策形狀)。

## 日常操作與決策形狀

### CLI 與 client API

子議題：

- redis-cli 指令對照表（SET / GET / DEL / EXPIRE / TTL / KEYS / SCAN / MGET / MSET）
- Client library 配置：connection pool / timeout / pipeline / cluster mode
- Pub/Sub vs Streams 的選用判讀
- 對應指令範例：`INFO replication`、`CLIENT LIST`、`SLOWLOG GET`

### Key design 與 data types

不同 data type 對應不同[資料形狀](/backend/02-cache-redis/cache-data-shape-access-pattern/)。子議題：

- String：cache / counter / config flag
- Hash：object cache（避免反覆 serialize）
- List：queue / activity feed（小規模）
- Set：membership / tag
- Sorted set：leaderboard / time-series sliding window
- Stream：log-style queue / event stream
- HyperLogLog / Geo：approximate count / 地理座標

Key naming 規範：`<service>:<entity>:<id>:<field>`、用 `:` 分層、避免大 key（單 key > 10KB / list 長度 > 10K）。

### TTL 與 eviction 策略

[TTL 跟 eviction](/backend/02-cache-redis/ttl-eviction/) 是 cache 行為的核心旋鈕。子議題：

- 顯式 EXPIRE vs SET EX 設 TTL
- maxmemory + maxmemory-policy（allkeys-lru / allkeys-lfu / volatile-lru / volatile-ttl / noeviction）
- TTL 設計：固定 TTL vs 動態 TTL vs 不設 TTL
- 對應指令：`CONFIG SET maxmemory 2gb`、`CONFIG SET maxmemory-policy allkeys-lfu`

## 進階主題（按需閱讀）

### Cluster vs Sentinel

子議題：

- Sentinel：HA 模式、無 sharding、適合單 master 容量足夠
- Cluster：sharding 模式、16384 hash slot、橫向擴展容量
- Hash tag `{...}` 強制 multi-key 同 shard
- Cluster failover 對 PEL（Streams）跟 distributed lock 的影響

### AOF / RDB 持久化策略

子議題：

- AOF（append-only file）：fsync 策略（always / everysec / no）、rewrite
- RDB（snapshot）：save 策略、backup 還原
- 混合模式：AOF + RDB
- 持久化在 cache 場景的取捨（持久化是回填還是 source-of-truth）

### Eviction policy 詳細

子議題：

- LRU vs LFU：access pattern 對選擇的影響
- volatile-* vs allkeys-*：只淘汰有 TTL 的 vs 全 key
- approximate LRU 的 sampling 影響
- 對應 [2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)

### Distributed lock

子議題：

- SETNX + EXPIRE 模式
- Redlock 算法（多 master quorum）+ 取捨爭議
- Redlock 何時不夠：fence token / lease renewal
- 對應 [2.5 distributed lock](/backend/02-cache-redis/distributed-lock/)

### Pub/Sub vs Streams

子議題：

- Pub/Sub：fire-and-forget、訂閱者離線會錯過
- Streams：append-only log、consumer group + PEL
- 何時用 Streams 取代 Pub/Sub
- Redis Streams 細節見 [03 messaging 模組 Redis Streams vendor](/backend/03-message-queue/vendors/redis-streams/)

### Redis Modules

子議題：

- RedisJSON / RedisSearch / RedisTimeSeries / RedisBloom / RedisGraph
- Module 隨授權變動受影響、Valkey 部分 fork
- Module 在 ElastiCache 的支援限制

### 授權變動與選型影響

子議題：

- 2024 RSALv2 / SSPL 變動的影響範圍
- 對 managed service（ElastiCache 改 default 為 Valkey）的衝擊
- 從 Redis 遷 Valkey 的相容性路徑
- 商業 vs OSS 邊界

### Hot key 處理

子議題：

- Hot key 偵測（redis-cli --hotkeys、`MONITOR` 慎用）
- Hot key 解法：local cache + Redis 兩層、key 拆分（讀多寫少場景）
- 對應 [2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)

## 排錯快速判讀

### Hit rate 下降

操作原則：先看 cache pattern 是否變（新功能 / TTL 變短）、再看 origin 壓力是否擴大。

```bash
# TODO: INFO stats（看 keyspace_hits / keyspace_misses 比例）
```

判讀路徑：TTL 太短 → eviction 太積極 → key 命名變動造成 cache miss → origin 失敗 retry storm。

### Memory pressure / eviction 異常

操作原則：先看 maxmemory + maxmemory-policy 設定、再看 key size 分布。

```bash
# TODO: INFO memory / MEMORY USAGE <key> / --bigkeys
```

### Hot key

對應案例 [2.C5 Shopify Write-Through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)。判讀路徑：某 key 的 QPS 遠高於其他、單 shard CPU 接近 100%、其他 shard 閒置。

### Replication lag

操作原則：replica 跟 master 差距、看 `INFO replication` 的 master_repl_offset vs slave_repl_offset。對 [2.C1 Meta Cache Consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/) 的對照。

### Cache stampede（雷霆崩潰）

對應反例 [2.C9 Cache Stampede Rollout](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)。判讀路徑：TTL 同時過期 → 大量 cache miss → origin 被打爆 → 連鎖失敗。修法：jitter TTL、early refresh、[singleflight](/backend/knowledge-cards/singleflight/) 模式。

## 何時改走其他服務

| 需求形狀                  | 改走                                                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 需要 OSI 認可開源授權     | [Valkey](/backend/02-cache-redis/vendors/valkey/)                                                                     |
| 純 cache、不需 data types | [Memcached](/backend/02-cache-redis/vendors/memcached/)                                                               |
| 極高 throughput / 多核    | [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)                                                           |
| AWS 生態 managed          | [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)                                                   |
| Durable Redis-compatible  | AWS MemoryDB（介於 cache 與 DB）                                                                                      |
| 大規模 event stream       | [Kafka](/backend/03-message-queue/vendors/kafka/) / [Redis Streams](/backend/03-message-queue/vendors/redis-streams/) |
| Process-local cache       | [Caffeine](/backend/02-cache-redis/vendors/caffeine/) / Guava Cache（JVM 內、無網路）                                 |
| Search / full-text        | Elasticsearch / OpenSearch（不在本模組）                                                                              |

## 不在本頁內的主題

- 各語言 Redis client 完整 API
- Redis command 百科（詳查 redis.io/commands）
- Redis Stack 商業 modules 細節
- AOF / RDB 內部 binary format

## 案例回寫

### 直接相關案例

| 案例                                                                                               | 對 Redis 的對應                                                                 |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [2.C3 Shopify serialization](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/) | Shopify Redis 上做 Marshal → MessagePack 雙軌遷移、payload 編碼演進             |
| [2.C5 Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)  | Shopify 在 read-heavy 路徑用 Redis 做 write-through、對應 hot key / 命中率治理  |
| [2.C1 Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/)       | invalidation / shard move 一致性議題、Redis Cluster 與 replica 場景共用判讀框架 |

### 跨 vendor 對照

| 案例                                                                                                    | 對 Redis 的對應                                                                                |
| ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)         | Redis TTL 切換 / key rename 都會觸發 stampede、需 jitter / singleflight / early refresh        |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                       | 小型 single instance + AOF / 中型 Sentinel + replica / 大型 Cluster + hash tag                 |
| [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)                 | Memcached 路由層案例、Redis 對應為 Cluster + proxy（Envoy / Twemproxy）或 client-side routing  |
| [2.C4 Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/)     | 分層 cache（DRAM + flash）對照、Redis on flash（RoF / Speedb）的成本決策參考                   |
| [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)               | EVCache 基於 Memcached + 跨 AZ replication、Redis 對應為 active-active CRDB / Global Datastore |
| [2.C8 Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)                   | Graph cache 演進案例、Redis 對應為 RedisGraph（已 deprecated）或自建 graph 索引                |
| [2.C7 Cloudflare Cache Reserve](/backend/02-cache-redis/cases/cloudflare-cache-reserve-tiered-storage/) | Edge tiered（HTTP cache）對照、Redis 對應為 hot tier + S3 cold tier 自建分層                   |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)、[2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)
- 平行 vendor：[Valkey](/backend/02-cache-redis/vendors/valkey/)、[Memcached](/backend/02-cache-redis/vendors/memcached/)
- 下游能力：[2.5 distributed lock](/backend/02-cache-redis/distributed-lock/)、[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)
