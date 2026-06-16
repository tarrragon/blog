---
title: "Caffeine"
date: 2026-06-16
description: "JVM process-local cache、Window TinyLFU、Guava Cache 後繼"
weight: 8
tags: ["backend", "cache", "vendor"]
---

Caffeine 是 JVM 上的 high-performance process-local cache library、承擔三個責任：在 application 進程內（on-heap）提供奈秒到微秒級的 cache（沒有網路往返）、用 Window TinyLFU 淘汰演算法逼近最佳命中率（優於傳統 LRU）、提供 expire / refresh / size-based eviction 等完整 cache 語意。設計取捨偏向「最低延遲 + 最高命中率 + 嵌進 application」、是 Redis 之外的另一層 cache，不是 Redis 的替代。

對「每個請求重複讀同一份小資料、Redis 的網路往返都嫌慢、資料可在每個實例各存一份」這條路徑、Caffeine 是 process-local 層的標準選擇。它常跟 Redis 組成兩層 cache（Caffeine L1 + Redis L2）、不是二選一。Caffeine 是 [Guava Cache](https://github.com/google/guava) 的後繼、由同作者重寫、Spring Boot 等框架的預設 local cache。

## 本章目標

讀完本章後、你應該能：

1. 用 Maven / Gradle 引入 Caffeine、寫出基本 cache
2. 理解 Window TinyLFU 為何命中率優於 LRU
3. 設計 expire-after-write / refresh-after-write / 容量上限
4. 判斷 process-local cache 跟 Redis 的兩層 cache 分工
5. 評估跨實例 invalidation 的限制與 GC 壓力

## 最短路徑：引入 Caffeine 寫一個 cache

```xml
<!-- Maven 依賴（version 為範例、實際以 Maven Central 最新為準、最後檢查日 2026-06-16）-->
<dependency>
  <groupId>com.github.ben-manes.caffeine</groupId>
  <artifactId>caffeine</artifactId>
  <version>3.2.4</version>
</dependency>
```

```java
// 基本 cache：容量上限 10000、寫入後 5 分鐘過期
Cache<String, User> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofMinutes(5))
    .build();

cache.put("user:123", user);
User u = cache.getIfPresent("user:123");

// loading cache：miss 時自動回源（取代手寫 cache-aside）
LoadingCache<String, User> loading = Caffeine.newBuilder()
    .maximumSize(10_000)
    .refreshAfterWrite(Duration.ofMinutes(1))   // 背景非同步 refresh、不阻塞讀
    .build(key -> userRepository.findById(key)); // miss / refresh 時呼叫
User u2 = loading.get("user:123");
```

Caffeine 是 library 不是 server、跑在 application JVM 內、無法 docker 獨立驗證；上面是依官方 API 的範例（API 以 [Caffeine wiki](https://github.com/ben-manes/caffeine/wiki) 為準）。

## 日常操作與決策形狀

### 淘汰與過期策略

Caffeine 把 cache 行為拆成幾個正交的旋鈕。子議題：

- `maximumSize` / `maximumWeight`：容量上限（筆數或加權大小）、超過用 W-TinyLFU 淘汰
- `expireAfterWrite`：寫入後固定時間過期（資料新鮮度上限）
- `expireAfterAccess`：最後存取後過期（淘汰冷資料）
- `refreshAfterWrite`：到期後背景 refresh、舊值先服務、不阻塞（跟 expire 不同）

### Window TinyLFU 淘汰

子議題：

- W-TinyLFU 結合 recency（window）+ frequency（TinyLFU sketch）、命中率逼近最佳
- 比 LRU 更抗一次性掃描污染（scan resistance）、跟 [Redis LFU](/backend/02-cache-redis/vendors/redis/memory-eviction-tuning/) 的動機類似但演算法更先進
- frequency 用 count-min sketch 近似、記憶體開銷小

### 兩層 cache（L1 Caffeine + L2 Redis）

子議題：

- L1 Caffeine（process-local、奈秒級、每實例一份）擋掉大部分讀
- L2 Redis（共享、毫秒級、跨實例一致）擋掉 L1 miss
- 對應 [2.6 high concurrency 的 hot key 兩層解法](/backend/02-cache-redis/high-concurrency-access/)

## 進階主題（按需閱讀）

### 跨實例 invalidation 的根本限制

子議題：

- 每個 JVM 實例有自己的 Caffeine 副本、一個實例更新不會通知其他實例
- 解法：短 TTL 容忍 stale、或用 Redis pub/sub 廣播 invalidation 訊息給各實例
- 這是 process-local cache 的固有取捨：最低延遲換來最弱的跨實例一致性

### GC 壓力與 on-heap vs off-heap

子議題：

- Caffeine 預設 on-heap、大 cache 會增加 JVM heap 與 GC 壓力
- 容量上限要對齊 heap 預算、避免 cache 把 heap 撐爆觸發 full GC
- 極大 local cache 考慮 off-heap 方案（如 Ehcache 的 off-heap tier），但 Caffeine 本身專注 on-heap

### async 與 refresh 語意

子議題：

- `AsyncCache` / `AsyncLoadingCache`：回傳 CompletableFuture、不阻塞 caller
- `refreshAfterWrite`：到期後第一個讀觸發背景 refresh、舊值立即回、避免 [stampede](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)
- refresh vs expire 的差異是「舊值能不能先服務」

## 排錯快速判讀

### 跨實例讀到舊值

操作原則：process-local cache 各實例獨立、更新不傳播。判讀：縮短 TTL 容忍 stale、或加 Redis pub/sub 廣播 invalidation；強一致需求不該用 process-local cache。

### 命中率低 / cache 沒效果

操作原則：先看 `maximumSize` 是否太小（working set 放不下）、再看 TTL 是否太短。判讀：用 `recordStats()` 看 hit rate / eviction count、對齊 working set。

### Full GC 頻繁

操作原則：on-heap cache 太大撐爆 heap。判讀：降 `maximumSize` 或用 `maximumWeight` 控制實際記憶體、對齊 JVM heap 預算。

## 何時改走其他服務

| 需求形狀                | 改走                                                                            |
| ----------------------- | ------------------------------------------------------------------------------- |
| 需要跨實例共享 / 一致   | [Redis / Valkey](/backend/02-cache-redis/vendors/redis/)（共享 cache 層）       |
| 非 JVM 語言             | 該語言的 process-local cache（Go ristretto、Python cachetools 等）              |
| 需要持久化 / durable    | Redis with AOF / AWS MemoryDB                                                   |
| 極大 cache 超過 heap    | off-heap cache（Ehcache off-heap）或外部 cache（Redis）                         |
| 不想管容量 / serverless | [Momento](/backend/02-cache-redis/vendors/momento/)（serverless、但有網路延遲） |

## 不在本頁內的主題

- Caffeine 完整 API（以官方 wiki 為準）
- 各 JVM 框架（Spring Cache abstraction）的整合細節
- Guava Cache 到 Caffeine 的完整 API 對照
- off-heap cache 方案比較

## 案例回寫

### 跨 vendor 對照（本模組 case 庫暫無 Caffeine-specific case）

Caffeine 是 library 層元件、本 blog cache case 庫（Meta / Shopify / Netflix / Cloudflare / Tinder / Tubi / Snap）暫無 Caffeine-specific case。以下用 process-local 的角度對照。

| 案例                                                                                                | 對 Caffeine 的對應                                                                     |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [2.C4 Meta CacheLib + Kangaroo](/backend/02-cache-redis/cases/meta-cachelib-kangaroo-tiered-cache/) | CacheLib 是 C++ 的 process-local + flash 分層 library、Caffeine 是 JVM 的 on-heap 對應 |
| [2.C8 Meta TAO](/backend/02-cache-redis/cases/meta-tao-social-graph-cache-evolution/)               | TAO 有 application-tier local cache、process-local 擋掉大部分讀的思路一致              |
| [9.C6 Tinder](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/)           | 每次互動查多個 cache、process-local L1 可擋掉重複讀、降低 L2（Redis）的 RTT 壓力       |

**待補 Caffeine-specific 案例**：L1 Caffeine + L2 Redis 兩層 cache 的 production 命中率分層數據、跨實例 invalidation 的 Redis pub/sub 廣播實作、W-TinyLFU vs LRU 的實測命中率對照。

## 下一步路由

- 上游概念：[2.6 high concurrency](/backend/02-cache-redis/high-concurrency-access/)（hot key 兩層解法）、[2.3 TTL eviction](/backend/02-cache-redis/ttl-eviction/)
- 平行 vendor：[Redis](/backend/02-cache-redis/vendors/redis/)（兩層 cache 的 L2）、[Momento](/backend/02-cache-redis/vendors/momento/)（另一端：serverless）
- 下游能力：[2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)（跨實例一致性窗口）
