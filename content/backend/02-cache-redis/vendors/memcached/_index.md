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
# 1. 啟動 Memcached
# TODO: docker run -d --name memcached -p 11211:11211 memcached:1.6

# 2. 用 telnet 驗證
# TODO: telnet localhost 11211 / set foo 0 60 3 / bar / get foo

# 3. 用 client library 驗證（python-memcached、pylibmc、go memcache）
# TODO: python set / get 範例
```

最短路徑驗證「Memcached 起來、能讀寫」。沒有 CLI tool 像 redis-cli 那麼便利、實際 ops 多靠 client library + monitoring。

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
# TODO: echo "stats" | nc localhost 11211 | grep -E "get_hits|get_misses|evictions"
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
| Process-local cache                  | Caffeine / Guava Cache（T4 候選）                                                                   |

## 不在本頁內的主題

- 各語言 Memcached client 完整 API
- Memcached internal data structure 細節
- Custom binary protocol 實作
- ASCII vs binary protocol 完整對照

## 案例回寫

### 直接相關案例

| 案例                                                                                      | 對 Memcached 的對應                       |
| ----------------------------------------------------------------------------------------- | ----------------------------------------- |
| [2.C4 Meta Mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)   | Mcrouter 是 Memcached 的 routing proxy    |
| [2.C5 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/) | EVCache 基於 Memcached、跨 AZ replication |

### 跨 vendor 對照

| 案例                                                                                            | 對 Memcached 的對應                                                 |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [2.C9 Cache Stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) | 通用、Memcached 也需 TTL jitter                                     |
| [2.C10 規模對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)               | 小型 single instance / 中型 client-side ketama / 大型 Mcrouter 路由 |

## 下一步路由

- 上游概念：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)、[2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)、[AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/)
- 下游能力：[2.4 cache data shape](/backend/02-cache-redis/cache-data-shape-access-pattern/)
