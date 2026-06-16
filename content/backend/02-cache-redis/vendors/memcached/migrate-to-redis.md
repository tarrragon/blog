---
title: "Memcached → Redis：不搬資料、搬存取層的能力升級遷移"
date: 2026-06-16
description: "Memcached → Redis 跟一般 migration 最大的不同：cache 是可重建的，所以這個遷移不搬資料、讓新 cache 重新 warm 就好，真正的工作在存取層（client、協定）跟可選的能力升級（data types）。本文跑 6 維 diff audit、用兩階段（drop-in pure KV → 採用 data types）結構、5 個把『outgrew pure KV』寫成事故的踩坑"
weight: 21
tags: ["backend", "cache", "memcached", "redis", "migration", "capability-upgrade"]
---

> 本文是跨 vendor migration playbook、cross-link [Memcached](/backend/02-cache-redis/vendors/memcached/)（source）跟 [Redis](/backend/02-cache-redis/vendors/redis/)（target）。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 Schema/API + application change High、但 **data topology Low（cache 可重建）**——本文是「能力升級 + 資料層免遷」的 dogfood，跟反向的 [Redis → Memcached（Type E paradigm reduction）](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/) 對位。

## cache 遷移不搬資料、搬存取層

一般 migration 最重、最危險的部分是搬資料——schema 要對、一致性要保、cutover 要不丟。Memcached → Redis 把這塊幾乎拿掉了，因為 **cache 的資料本來就是可重建的副本**。你不需要把 Memcached 裡的東西搬到 Redis；你讓 Redis 空著上線、cache miss 自然回源、慢慢 warm 起來就好。Memcached 那邊在 warm-up 期間繼續服務，等 Redis 命中率追上來再切。

這個性質讓 Memcached → Redis 的工作重心完全不同：不在資料層，在**存取層**（換 client library、換協定）跟**可選的能力升級**。觸發這個遷移的通常是「outgrew pure KV」——本來只用 Memcached 存 string，後來需要 counter（用 application 層讀-改-寫硬湊、有 race）、需要 session 物件（serialize 整包 JSON、改一個欄位要全寫）、需要 leaderboard（在 app 排序、慢）。這些 Redis 用 INCR / Hash / Sorted Set 原生解，把 application 層硬湊的邏輯收回 cache 層。

本文跑 diff audit 確認這個形狀、用兩階段結構（先 drop-in、再升級能力）展開遷移與踩坑。

## 6 維 diff dimension audit

| 維度                   | 評估                                                         | 等級    |
| ---------------------- | ------------------------------------------------------------ | ------- |
| Schema / API           | Memcached 協定 → Redis RESP、純 string → 可選 data types     | High    |
| Operational model      | Redis 多了 eviction policy / persistence / cluster 決策      | Medium  |
| Abstraction / paradigm | pure cache → data structure store（但可先維持 pure KV 用法） | Medium  |
| Number of components   | 1 → 1                                                        | Low     |
| Application change     | client library 換、可選改用 data types                       | High    |
| **Data topology**      | **cache 可重建、不搬資料、re-warm**                          | **Low** |

主導維度是 Schema/API + application change（存取層），但這個 migration 的特徵是 **data topology Low**——這是 cache 類遷移獨有的性質，讓它比一般 Type A 簡單一截。結構上採兩階段：**Phase 1 drop-in 替換（維持 pure KV 用法、先把 client 換掉）**，**Phase 2 漸進採用 data types（把 application 層硬湊的邏輯收回 Redis）**。Phase 2 是可選的、可以慢慢來。

## Phase 1：drop-in 替換（pure KV、不搬資料）

第一階段把 Memcached 換成 Redis，但**只用 Redis 當 pure KV**（GET / SET / DEL + TTL），存取行為跟 Memcached 一樣。這一步風險最低，因為不碰 data model、不搬資料。

```text
存取層對應（Phase 1 維持 pure KV 語意）：
  Memcached set(key, val, ttl)   →  Redis SET key val EX ttl
  Memcached get(key)             →  Redis GET key
  Memcached delete(key)          →  Redis DEL key
  Memcached incr/decr            →  Redis INCR/DECR（Redis 原生原子、比 Memcached 更穩）
```

cutover 流程（cache 可重建、無資料遷移）：

```text
1. 部署 Redis（空的）、設 maxmemory + eviction policy（見記憶體調校）
2. application 改用 Redis client（雙寫期：同時寫 Memcached + Redis，讀仍走 Memcached）
3. 讀切到 Redis（cache miss 回源 + 寫回 Redis、命中率逐步 warm up）
4. 觀察 Redis 命中率追上 Memcached、origin 壓力無異常
5. 停止寫 Memcached、下線 Memcached
```

判讀：

- 不需要資料遷移工具——Redis 空上線、靠 cache-aside 自然 warm（見 [2.2 cache aside](/backend/02-cache-redis/cache-aside/)）
- warm-up 期 origin 壓力會短暫上升（命中率從 0 爬升），低流量時段切、或預熱熱 key
- Phase 1 完成後 application 行為跟用 Memcached 時一致，只是底層換 Redis
- 想保留開源 OSI 授權，target 直接選 [Valkey](/backend/02-cache-redis/vendors/valkey/)（Redis 相容、BSD）

## Phase 2：漸進採用 data types（可選）

Phase 1 上線穩定後，再把 application 層硬湊的邏輯逐步收回 Redis 的原生 data types。這一階段是能力升級、不是遷移必需，可以一個場景一個場景來。

```text
application 硬湊 → Redis 原生：
  讀 JSON → 改欄位 → 寫回整包    →  Redis Hash（HSET/HGET 單欄位、免全寫）
  app 端計數 + CAS 重試           →  Redis INCR（原子、無 race）
  app 端排序 leaderboard          →  Redis Sorted Set（ZADD/ZRANGE）
  app 端 set 去重                 →  Redis Set（SADD/SISMEMBER）
  多 key 操作要原子               →  Redis MULTI / Lua（Memcached 只有 CAS）
```

判讀：

- Phase 2 每個改動是獨立的小重構，不必一次到位
- 收回 data types 的收益是「消除 application 層的 read-modify-write race + 減少網路往返」
- 不是所有東西都要升級——純 string cache 留在 GET/SET 就好，別為了用而用

## Production 故障演練

### Case 1：warm-up 期 origin 被打爆

**徵兆**：切讀到 Redis 的瞬間，origin（DB）QPS 暴增、延遲升高，因為 Redis 還是空的、大量 cache miss 同時回源。

**根因**：Redis 空上線、命中率從 0 開始，warm-up 期所有讀都 miss 回源。沒有控制就是一次 origin 衝擊（類似冷啟動 stampede）。

**修法**：

1. 低流量時段切讀、讓命中率平緩爬升
2. 預熱熱 key（migration 前先把已知熱 key 灌進 Redis）
3. cache miss 回源加 singleflight / jitter，避免同 key 並發回源（見 [2.9 stampede rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)）
4. 雙寫期先讓 Redis 被寫入 warm 一段時間，再切讀

### Case 2：把 Memcached 的 multi-get 行為直接搬、效能不如預期

**徵兆**：Memcached 的 batch get（一次拿多 key）搬到 Redis 後延遲沒改善甚至更差。

**根因**：Memcached client 的 multi-get 跟 Redis 的 MGET / pipeline 行為不同。直接一個 key 一個 GET（N 次往返）會比 Memcached 的 batch 慢——Redis 要用 MGET 或 pipeline 才能合併往返（見 [Redis 連線 / pipeline](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)）。

**修法**：

1. Memcached multi-get → Redis MGET（同 slot）或 pipeline
2. 不要把「N 次獨立 GET」當成 multi-get 的等價
3. cluster 模式下 MGET 跨 slot 會失敗，用 hash tag 或 pipeline 分組
4. 量測往返次數，存取層遷移要保持「一次互動的往返數」不退化

### Case 3：TTL 精度與 eviction 行為差異造成命中率變化

**徵兆**：遷到 Redis 後命中率跟 Memcached 時期不一樣（可能更高或更低），cache 行為不如預期。

**根因**：Memcached 是 LRU + 秒級 lazy expiration + slab 限制；Redis 有 8 種 eviction policy + ms 級 TTL + 不同記憶體模型。沿用 Memcached 的 TTL 與容量設定不會得到一樣的淘汰行為。

**修法**：

1. 明確設 Redis 的 `maxmemory-policy`（純 cache 用 allkeys-lru / allkeys-lfu，見 [記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)）
2. 不要假設 Memcached 的容量設定直接套用——Redis 記憶體模型不同（無 slab calcification、但有自己的 fragmentation）
3. 觀察 `evicted_keys` 與命中率，對齊預期 working set
4. Memcached 的 slab 浪費 vs Redis 的編碼，記憶體佔用會不同，重新算容量

### Case 4：以為 Redis 一定比 Memcached 快 / 省

**徵兆**：遷到 Redis 後純 string cache 的記憶體佔用或延遲沒有改善，甚至 Redis 單執行緒在高並發純 GET 下不如 Memcached 多執行緒。

**根因**：對「純 string KV、高並發」這個 Memcached 的本場，Memcached 的多執行緒可能比 Redis 單執行緒（命令層）更適合。遷 Redis 的收益在 data types / persistence / 生態，不是純 KV 效能。

**修法**：

1. 釐清遷移動機——是要 data types / persistence（Redis 解）還是純 KV 效能（Memcached 可能更好）
2. 純 KV 高並發要 Redis 的多核走 [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/) / [KeyDB](/backend/02-cache-redis/vendors/keydb/) 或 Redis I/O threads
3. 純 cache 紀律本來就是 Memcached 的優勢，遷 Redis 要小心別把 cache 用成 database
4. 沒有 data types / persistence 需求的純 KV，留 Memcached 可能更對

### Case 5：把可重建的 cache 當成要搬的資料、白做遷移工具

**徵兆**：團隊花時間寫 Memcached → Redis 的資料遷移腳本、做一致性校驗，結果發現 cache 切換後這些資料本來就會被新值覆蓋。

**根因**：用一般 migration 的思維（搬資料 + 校驗）處理 cache 遷移，沒意識到 cache 是可重建副本——搬過去的舊值很快被回源的新值取代，搬資料是白工且可能搬到 stale 值。

**修法**：

1. cache 遷移預設不搬資料、靠 re-warm（這是 cache 類遷移的核心簡化）
2. 只有「重建成本極高的 cache」（昂貴計算結果）才考慮搬，且要評估 stale 風險
3. 把精力放在存取層正確性與 warm-up 控制，不是資料搬遷
4. 對照 [cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)：cache 是副本、不是 source-of-truth

## Capacity / cost 對照

| 維度             | Memcached（source） | Redis / Valkey（target）              |
| ---------------- | ------------------- | ------------------------------------- |
| 資料遷移         | —                   | 不需要（cache 可重建、re-warm）       |
| data types       | 純 string KV        | 6 大 + Stream / Geo                   |
| 原子操作         | INCR / DECR / CAS   | 100+（INCR / HSET / ZADD / Lua）      |
| persistence      | 無                  | RDB / AOF（可選）                     |
| 多執行緒         | 原生多執行緒        | 單執行緒命令 + I/O threads            |
| eviction         | LRU only            | 8 種 policy                           |
| 純 KV 高並發效能 | 多執行緒、本場強    | 單執行緒命令可能略遜（要多核走 fork） |
| 遷移風險         | —                   | 低（無資料遷移、存取層 + warm-up）    |

**判讀**：要 data types / persistence / 原子操作 → 遷 Redis（兩階段、低風險）；純 KV + 高並發 + 嚴格 cache 紀律 → 留 Memcached。

## 整合 / 下一步

Memcached → Redis 是能力升級，它跟 Redis 的調校與選型交織：

- **跟 [Redis 記憶體與淘汰調校](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/)**：遷過去要設對 maxmemory-policy，Redis 記憶體模型跟 Memcached slab 不同。
- **跟 [Redis 連線 / pipeline](/backend/02-cache-redis/vendors/redis/connection-pipeline-latency/)**：Memcached multi-get → Redis MGET / pipeline，存取層遷移要保持往返數。
- **跟反向 [Redis → Memcached](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)**：反向是 Type E paradigm reduction（downgrade）；本文是能力升級（upgrade），兩者對位看 cache paradigm 的兩個方向。
- **跟 [Valkey](/backend/02-cache-redis/vendors/valkey/)**：要開源 OSI 授權，target 選 Valkey（Redis 相容、BSD），遷移流程一致。

## 相關連結

- Source vendor：[Memcached](/backend/02-cache-redis/vendors/memcached/)
- Target vendor：[Redis](/backend/02-cache-redis/vendors/redis/) / [Valkey](/backend/02-cache-redis/vendors/valkey/)
- 反向 migration：[Redis → Memcached（Type E paradigm reduction）](/backend/02-cache-redis/vendors/redis/migrate-to-memcached/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
