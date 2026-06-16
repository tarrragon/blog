---
title: "Memcached"
date: 2026-05-01
description: "純記憶體 key-value cache、無持久化"
weight: 3
tags: ["backend", "cache", "vendor"]
---

Memcached 是純粹的 in-memory key-value cache、承擔三個責任：簡單 string KV cache、多執行緒高吞吐、嚴格的 cache 邊界（無持久化 / 無 data types / 無 lock）。設計取捨偏向「越簡單越好」— 沒有 Redis 的 data types / Streams / Pub/Sub、也沒有持久化 / 複製 / cluster mode。極輕量、運維成本低、適合 strict cache 場景。

對「純 cache、避免誤用為 source-of-truth、需要多執行緒高 throughput、極簡運維」這條路徑、Memcached 是首選。從 LiveJournal 2003 年開源至今、是業界最久經考驗的 cache。

## 本章目標

讀完本章後、你應該能：

1. 跑起 Memcached、用 telnet 或 memcached-tool 驗證
2. 用 SET / GET / DELETE / INCR / DECR 操作、區分 Memcached 跟 Redis 的場景界限
3. 設計 client-side consistent hashing 做 sharding
4. 看懂 hit rate / slab fragmentation / eviction 訊號
5. 評估 Memcached vs Redis 的選用判讀（何時純粹勝過豐富）

## 最短路徑：5 分鐘把 Memcached 跑起來

```bash
# 1. 啟動 Memcached（-t 4 開 4 條 worker thread、-m 64 給 64MB）
docker run -d --name memcached -p 11211:11211 memcached:1.6 memcached -t 4 -m 64

# 2. 用 text protocol 驗證讀寫（沒有 redis-cli 這種專屬 CLI、直接走 TCP）
#    set <key> <flags> <ttl> <bytes>，下一行是 value
printf 'set foo 0 60 3\r\nbar\r\nget foo\r\nquit\r\n' | nc localhost 11211
# STORED
# VALUE foo 0 3
# bar
# END

# 3. 確認多執行緒與記憶體上限
printf 'stats settings\r\nquit\r\n' | nc localhost 11211 | grep -E "num_threads|maxbytes"
# STAT maxbytes 67108864      ← 64MB
# STAT num_threads 4          ← -t 4 生效
```

最短路徑驗證「Memcached 起來、能讀寫、多執行緒生效」。Memcached 沒有 redis-cli 這類專屬 CLI、實際 ops 走 client library（python-memcached / pylibmc / go memcache）+ `stats` 系列命令。實機驗證於 memcached:1.6（VERSION 1.6.42）、最後檢查日 2026-06-16。

## 日常操作與決策形狀

### 協議與 client library

子議題：

- ASCII protocol vs binary protocol（兩種都支援、binary 較有效率）
- Client library：python-memcached、pylibmc（libmemcached 綁定）、go memcache、Java spymemcached
- Connection management：connection pool / persistent connection

### 指令對照

子議題：

- 基本：SET / GET / ADD / REPLACE / DELETE / FLUSH_ALL
- Counter：INCR / DECR（不能 < 0）
- 條件：CAS（compare-and-swap）做 optimistic lock
- 批次：GETS（批次 + CAS token）

### Client-side sharding

Memcached server 本身無 cluster mode、靠 client library 做 sharding。子議題：

- Consistent hashing（ketama）— 加減 node 時 minimum key 移動
- Hash 演算法：md5 / SHA1 / ketama
- 對應 [2.4 cache data shape](/backend/02-cache-redis/cache-data-shape-access-pattern/)

### Memory model（slab allocator）

子議題：

- Memcached 用 slab allocator 預分配記憶體 chunk
- 不同 size class（slab class）對應不同 chunk size
- Fragmentation：當 value size 跟 slab 不對齊、memory 浪費
- 對應指令：`stats slabs` / `stats items`

## 進階主題（按需閱讀）

### Slab allocator 與 memory fragmentation

子議題：

- Slab class 自動分配機制
- Slab reassignment（Memcached 1.4.25+）— 把記憶體在 slab class 間搬移
- 監控 `STAT total_malloced` vs `STAT bytes_read`
- 對應指令：`stats slabs`、`slabs reassign <src> <dst>`

### Multi-threaded scaling

子議題：

- Memcached 從早期就 multi-threaded（vs Redis 早期 single-thread）
- `-t` 設 thread 數、預設 4、依 CPU core 調
- Lock contention：高 thread 數可能 hit per-bucket lock
- 對比 Redis：Redis 6+ 加 I/O threads、但 main thread 仍單線

### AWS ElastiCache for Memcached

子議題：

- ElastiCache 提供 managed Memcached cluster
- Auto Discovery：客戶端自動發現 cluster node 變化
- ElastiCache config endpoint 取代 client-side sharding 配置
- 跟 Redis ElastiCache 的成本對照

### CAS（compare-and-swap）

子議題：

- GETS 拿 value + token、SET 帶 token 做 conditional update
- 適合做 optimistic lock（vs Redis SETNX + lua）
- CAS 失敗時的 retry 策略

### Memcached vs Redis 的場景區分

子議題：

- 純 cache 不需 data types → Memcached 更輕量
- Session store / counter / hot key 兩者都行
- Leaderboard / sorted set / Streams / Pub/Sub → 只 Redis
- Distributed lock → Redis（Memcached CAS 不夠強）
- 持久化（cache warmup 後不想全失）→ Redis（RDB / AOF）

## 排錯快速判讀

### Hit rate 下降

操作原則：先看 eviction 是否提高、再看 key naming 是否變動。

```bash
printf 'stats\r\nquit\r\n' | nc localhost 11211 | grep -E "get_hits|get_misses|evictions"
# get_hits / get_misses 算 hit rate、evictions 持續增加代表 memory 壓力
```

### Eviction 增加（memory pressure）

操作原則：超過 `-m` 設定的 memory limit、Memcached 用 LRU evict 老 key。看 `stats slabs` 哪些 slab class 最常 evict、可能要 slab reassign。

### Slab fragmentation

操作原則：value size 跟 slab class 不對齊造成 wasted memory。判讀：`stats slabs` 看每個 slab class 的 used vs total chunks。

### Client-side sharding 不平衡

操作原則：node 加減後、ketama 應 minimum 移動、但實際分布可能因 key 集中而偏斜。判讀：每個 node 的 `stats` 看 key count + memory usage 是否均衡。

### Connection 耗盡

操作原則：每個 client 開太多 connection、Memcached 預設 max 1024 connection。看 `stats curr_connections`。

## 何時改走其他服務

| 需求形狀                             | 改走                                                                                                |
| ------------------------------------ | --------------------------------------------------------------------------------------------------- |
| 需要 data types（hash / list / set） | [Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/) |
| 需要持久化 / 半持久化                | Redis with AOF / RDB                                                                                |
| 需要 distributed lock                | Redis（Redlock 或 SETNX）                                                                           |
| 需要 Pub/Sub / Streams               | Redis / Kafka / NATS                                                                                |
| 多核高 throughput                    | [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)                                         |
| AWS managed                          | [AWS ElastiCache for Memcached](/backend/02-cache-redis/vendors/aws-elasticache/)                   |
| Process-local cache                  | [Caffeine](/backend/02-cache-redis/vendors/caffeine/) / Guava Cache（JVM 內、無網路）               |

## 不在本頁內的主題

- 各語言 Memcached client 完整 API
- Memcached internal data structure 細節
- Custom binary protocol 實作
- ASCII vs binary protocol 完整對照

## 案例回寫

### 直接相關案例

| 案例                                                                                         | 對 Memcached 的對應                                                                          |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)      | mcrouter 是 Memcached 專屬 protocol-aware routing proxy、處理跨叢集 / 跨區流量收斂與失效隔離 |
| [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/)    | EVCache 基於 Memcached、Netflix 加上跨 AZ replication + client-side smart routing            |
| [2.C8 Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)        | TAO 底層用 Memcached 作為 graph 資料的快取層、上層加一致性 / 關聯查詢能力                    |
| [2.C1 Meta cache consistency](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/) | Meta 大規模 Memcached 部署的 invalidation / shard move 一致性治理                            |

### 跨 vendor 對照

| 案例                                                                                                | 對 Memcached 的對應                                                                    |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)     | 通用、Memcached 也需 TTL jitter / lease / probabilistic early expiration               |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)                   | 小型 single instance / 中型 client-side ketama / 大型 mcrouter 路由 + 跨區 pool        |
| [2.C4 Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) | CacheLib 是 Memcached 之後 Meta 的分層 cache library、處理 DRAM 經濟極限後的議題       |
| [2.C3 Shopify serialization](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)  | Payload 編碼遷移在 Memcached 上一樣適用、雙軌策略不依賴 vendor                         |
| [2.C5 Shopify write-through](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/)   | Write-through 模式 Memcached 用 SET + CAS 實作、不像 Redis 有 Lua / transaction 可組合 |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)、[2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)、[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- 下游能力：[2.4 cache data shape](/backend/02-cache-redis/cache-data-shape-access-pattern/)
