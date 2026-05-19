---
title: "Redis → Memcached：Memcached 不是 simpler Redis、是 cache paradigm"
date: 2026-05-19
description: "Redis → Memcached 是 Type E paradigm reduction migration — 從 multi-paradigm（KV + 資料結構 + pub/sub + Lua + streams）退到 pure cache；不是「remove Redis features」、是「重新分配 Redis-specific feature 到對應 specialized 服務」；5 個 production 踩雷 + paradigm reduction 路線"
weight: 13
tags: ["backend", "cache", "redis", "memcached", "paradigm-shift", "migration", "type-e"]
---

> 本文是跨 vendor migration playbook、cross-link [Redis](/backend/02-cache-redis/vendors/redis/) 跟 [Memcached](/backend/02-cache-redis/vendors/memcached/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Paradigm = High（multi-paradigm → pure cache）→ Type E paradigm shift*；本文是 *paradigm reduction*（downgrade 方向）的 dogfood。

## Memcached 不是 simpler Redis、是 cache paradigm

把 Redis → Memcached 當「移除 Redis 功能」是最常見的誤判：

| 概念                  | Redis                                                                   | Memcached                                 |
| --------------------- | ----------------------------------------------------------------------- | ----------------------------------------- |
| 核心 paradigm         | Multi-paradigm（KV + 資料結構 + pub/sub + script）                      | Pure cache（KV + TTL）                    |
| Value 類型            | String / Hash / List / Set / Sorted Set / Stream / Bitmap / HyperLogLog | byte string only                          |
| Atomic operations     | 100+（INCR / LPUSH / ZADD / ...）                                       | INCR / DECR / APPEND / CAS                |
| Server-side scripting | Lua scripts (`EVAL`)                                                    | 無                                        |
| Pub/Sub               | Native                                                                  | 無                                        |
| Persistence           | RDB / AOF                                                               | 無（restart 全失）                        |
| Replication           | Async / sync replication                                                | 無                                        |
| Cluster               | Redis Cluster + Sentinel HA                                             | Memcached cluster（client-side sharding） |
| Eviction policy       | 8 種（LRU / LFU / random / ...）                                        | LRU only                                  |
| Expiration accuracy   | TTL 精確到 ms                                                           | TTL 精確到 second、lazy expiration        |

**核心差異不在「Memcached 少了 Redis 功能」、在「Memcached 是不同的 cache paradigm」。** Redis 的 features（hash / sorted set / pub/sub）多數 *不該移除*、是 *重新分配到對應 specialized service*：

- Hash / sorted set → application 端用 JSON + 自管 index
- Pub/Sub → message queue（NATS / Redis Streams / Kafka）
- Lua scripts → application code
- Persistence → 真正需要的 data 該存 DB、不是 cache
- Replication / cluster → Memcached 自己 cluster strategy

## 為什麼遷：simplification / cost / ops 三條 driver

- **Operational simplification**：Memcached 沒 persistence / replication / cluster mode、ops surface 縮小、團隊不用懂 Redis 25+ command family
- **Cost**：對 *純 cache use case* 而言、Memcached 每 GB 比 Redis 便宜（memory efficiency 略勝 + 無 persistence overhead）
- **Strict cache discipline**：Memcached *逼* application code 把「真正的 cache」跟「半 persistent state」分開、避免 Redis 變 *poor man's database*

反向 driver（Memcached → Redis）：

- Application 寫到 Memcached 後發現需要 *atomic counter / leaderboard / queue / lock*、應該升 Redis（不是繼續 wrap Memcached）

## 跑 6 維 audit

| 維度               | 評估                                                | 等級     |
| ------------------ | --------------------------------------------------- | -------- |
| Schema / API       | Redis 命令集 → Memcached 命令集、相容度 < 20%       | **High** |
| Operational model  | 兩者都簡單、Memcached 略簡單                        | Low      |
| Paradigm           | Multi-paradigm → pure cache                         | **High** |
| Components         | 同 1 個 cache service                               | Low      |
| Application change | 必改（任何 hash / list / sorted set / pubsub 用法） | **High** |
| Data topology      | 同 single instance / cluster                        | Low      |

3 維 High（Schema / Paradigm / Application change）多軸高、主導維度 = Paradigm → **Type E paradigm shift**；Schema + Application change 抽獨立段補充。

## 結構：類 Type E + paradigm reduction 分配路線

```text
1. Memcached 不是 simpler Redis（concept reverse 開頭）
2. 為什麼遷
3. 6 維 audit
4. Paradigm reduction 路線（Redis features 對應的 specialized service）
5. Schema 差段（Redis vs Memcached command set）
6. Application 重設計（per-call-site refactor）
7. Migration 流程（漸進、部分 use case 切）
8. Production 故障演練
9. Capacity / cost
10. 整合 / 下一步
```

10 章節、220-260 行。比 Type E（[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/)）多 *paradigm reduction 路線* 段。

## Paradigm reduction 路線

Redis features 對應的 specialized service：

```text
Redis Hash           → Application 端 JSON.stringify + Memcached SET
                       (or 直接存 DB + Memcached cache layer)

Redis List (queue)   → NATS / Kafka / RabbitMQ / SQS

Redis List (stack)   → Application 端用 array + 自管 LIFO

Redis Set            → Application 端用 array + dedup OR 用 DB unique index

Redis Sorted Set     → Application 端用 ordered list + comparator
                       OR PostgreSQL + index

Redis Stream         → Kafka / Redis Streams (保留) / NATS JetStream

Redis Pub/Sub        → NATS Core / Redis Streams / Kafka

Redis Lua script     → Application code（避免 atomic 假設）

Redis distributed lock → Consul / etcd / DB advisory lock / Redis (保留)

Redis Bitmap         → DB bit column / 應用端 bitset

Redis HyperLogLog    → DB approx_count_distinct / 應用端 cardinality estimator
```

Migration scope 包含 *每個 Redis-specific feature use case 對應的 service 評估*；不是「移除」、是「重新分配」。

## Application 重設計

```python
# Before: Redis hash
redis.hset('user:123', 'email', 'a@b.com')
redis.hset('user:123', 'name', 'Alice')
user = redis.hgetall('user:123')

# After: Memcached + JSON
import json
user_data = {'email': 'a@b.com', 'name': 'Alice'}
mc.set('user:123', json.dumps(user_data))
user = json.loads(mc.get('user:123') or '{}')
```

```python
# Before: Redis sorted set (leaderboard)
redis.zadd('leaderboard', {'alice': 100, 'bob': 95})
top_10 = redis.zrevrange('leaderboard', 0, 9, withscores=True)

# After: PostgreSQL + index + Memcached cache
# Persistent: write to DB
# Cache: pre-compute top 10 in DB query, cache in Memcached
mc.set('leaderboard:top10', json.dumps(db.query('SELECT user, score FROM scores ORDER BY score DESC LIMIT 10')))
```

```python
# Before: Redis distributed lock
with redis.lock('resource:1', timeout=10):
    process_resource()

# After: PostgreSQL advisory lock OR Consul session
with db.advisory_lock(resource_id):
    process_resource()
```

每個 Redis-specific pattern 都要 per-call-site refactor、不是 SDK 換。

## Migration 流程

跟 [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 同 *partial migration*：

```text
1. Audit application code、列所有 Redis call site + feature 使用
2. 按 feature 分類處理 plan:
   - Pure KV (GET/SET/DEL/TTL): 切 Memcached 直接
   - Hash → JSON + Memcached: per-call-site refactor
   - List/Sorted Set: 評估是 queue / leaderboard / 其他用途、對應 service
   - Pub/Sub: 移到 message queue
   - Lock: 移到 DB 或保留 Redis
3. 部分 application 先切（純 KV use case）
4. 複雜 use case 逐步 refactor 到對應 service
5. Memcached 跑 production 後、Redis 可降為 *narrow scope*（只跑剩餘 Redis-specific feature）
   或完全退役（如果 application 已 refactor 乾淨）
6. 長期混合架構：Memcached cache layer + DB persistent state + 可選的 Redis（locks / specialty）
```

整體 3-12 個月、依 Redis-specific feature 使用深度。

## Production 故障演練

### Case 1：Hash → JSON 後 GET/SET round-trip 變 N+1

**徵兆**：cutover 後 application latency p99 從 5ms 漲到 50ms；profiling 顯示「為了改 user.email、要先 GET user object → modify → SET」、原本 Redis `HSET` 1 個 round-trip 現在 2 個。

**根因**：JSON-encoded value 不能 partial update、每次改一欄都要 read-modify-write。

**修法**：

1. **Application 端 cache JSON object in memory**：read-modify-write 仍 1 個 SET、但 read 是 memory
2. **Compare-and-swap (CAS)**：Memcached CAS 防止 concurrent update lost
3. **Field-level cache key**：把 hash 拆成 N 個 Memcached key（`user:123:email` / `user:123:name`）、避開 JSON

### Case 2：Sorted set leaderboard 退化、recomputation cost 爆

**徵兆**：原本 Redis leaderboard `ZADD` + `ZREVRANGE` < 1ms；切 DB-backed leaderboard 後 `SELECT ... ORDER BY ... LIMIT 10` 在 1M+ row 跑 100-500ms。

**根因**：Memcached 不支援 sorted set、leaderboard 必須在 DB 算、N 大時 sort 慢。

**修法**：

1. **Cache pre-computed top N**：DB scheduled job 每分鐘算 top 100、寫 Memcached、application 讀 cache 不直查 DB
2. **Materialized view + index**：DB 端用 materialized view + index、毫秒級 query
3. **保留 Redis sorted set**：leaderboard 是 Redis 強項、不該退到 Memcached、走混合架構

### Case 3：Pub/Sub 移除、缺 fan-out 機制

**徵兆**：原本 Redis Pub/Sub 跑 cache invalidation broadcast、N 個 application instance 都收 invalidation msg；切 Memcached 後失去 broadcast、cache stale。

**根因**：Memcached 沒 Pub/Sub；application 需要外部 fan-out 機制。

**修法**：

1. **NATS / Redis Streams + consumer group**：each application instance 是 consumer、收 invalidation
2. **Database trigger + LISTEN/NOTIFY**：PostgreSQL `LISTEN/NOTIFY` 對中型 fan-out 足夠
3. **Architecture rethink**：是否真需要 broadcast invalidation？通常用 *TTL-based cache* + *cache key versioning* 就能 cover 多數 invalidation use case

### Case 4：Atomic INCR 沒對等、race condition

**徵兆**：rate limiter / counter pattern 切 Memcached、`mc.incr(key)` 在 key 不存在時 return None（不 auto-init 為 0）；application 端 `if None: mc.set(key, 1)` race condition、低機率 counter reset。

**根因**：Memcached INCR 對 missing key 不像 Redis 自動 init；application 端 init logic 容易 race。

**修法**：

```python
# 用 ADD（atomic put-if-absent）
mc.add(key, 0)  # only sets if missing
mc.incr(key)    # always works after add
```

`ADD` + `INCR` 兩個 atomic operation 合起來 race-free。

### Case 5：Eviction policy 差異、production cache hit rate 降

**徵兆**：cutover 後 cache hit rate 從 95% 降到 80%；profiling 發現「重要 key 沒在 cache」、新 key 一直擠走熱 key。

**根因**：Redis 預設 `allkeys-lfu` (least frequently used)、長期熱 key 不被擠；Memcached 只有 LRU、單純按 access time、burst access 的 cold key 擠走 long-tail hot key。

**修法**：

1. **Memory headroom**：Memcached memory 限制拉高 30-50%、避免 eviction pressure
2. **Application-side cache priority**：critical key 用 *no-expiration set* + 主動 refresh
3. **保留 Redis for LFU workload**：long-tail hot key 場景 Redis LFU 更合適、不該退 Memcached

## Capacity / cost

| 維度                   | Redis                     | Memcached                                         |
| ---------------------- | ------------------------- | ------------------------------------------------- |
| Memory efficiency      | baseline                  | +10-20%（無 metadata overhead）                   |
| Throughput             | ~100K ops/s single-thread | ~500K-1M ops/s multi-threaded                     |
| Latency p99            | 1-3ms                     | 0.5-1ms                                           |
| Persistence overhead   | 5-15% CPU                 | 0                                                 |
| Operational FTE        | 0.3-0.8                   | 0.1-0.3                                           |
| Application complexity | Low（feature 豐富）       | Higher（feature 移到 application）                |
| Cost per GB memory     | baseline                  | 略低（無 persistence I/O / replication overhead） |

**判讀**：純 cache use case 走 Memcached 省 ops + 略省 cost；application 已用 Redis-specific feature 不該切；混合架構是 long-term default。

## 整合 / 下一步

### 跟 [Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/) 對比

兩條路：

- DragonflyDB：保留 Redis paradigm、優化 throughput + memory；application 不用改
- Memcached：退到 pure cache paradigm、application 必須改、但 ops 簡化

選擇取決於 *是否真的需要 Redis multi-paradigm features*：用得到就 DragonflyDB / Redis、用不到就 Memcached。

### 跟 [NATS](/backend/03-message-queue/vendors/nats/) 整合

Redis Pub/Sub 移除後、應用端 fan-out / messaging 需求轉到 NATS / Redis Streams / Kafka；本文 cross-link migration playbook [Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) 有 paradigm shift 流程參考。

### 下一步議題

- **Memcached Cluster strategy**：client-side consistent hashing vs server-side cluster mode、ops 簡化 vs scalability 取捨
- **Long-term mixed architecture**：80% Memcached + 20% Redis 是常見 stable state、不一定要完全消除 Redis

## 相關連結

- Source vendor：[Redis](/backend/02-cache-redis/vendors/redis/)
- Target vendor：[Memcached](/backend/02-cache-redis/vendors/memcached/)
- 平行 migration playbook (Type E)：[Kafka ↔ NATS](/backend/03-message-queue/vendors/kafka/migrate-from-to-nats/) / [PostgreSQL → CockroachDB](/backend/01-database/vendors/postgresql/migrate-to-cockroachdb/)
- 平行 Type B 對照：[Redis → DragonflyDB](/backend/02-cache-redis/vendors/redis/migrate-to-dragonflydb/)（保留 paradigm）
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
