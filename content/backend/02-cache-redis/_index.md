---
title: "模組二：快取與 Redis"
date: 2026-04-22
description: "整理快取策略、Redis 資料型別與分散式狀態輔助能力"
weight: 2
tags: ["backend", "cache", "redis"]
---

快取模組的核心目標是說明暫存資料如何提升讀取效率，同時保護 [source of truth](/backend/knowledge-cards/source-of-truth/) 的正式判斷責任。語言教材會處理 cache port、資料複製邊界與 [TTL](/backend/knowledge-cards/ttl/) 的程式邊界；本模組負責 Redis 與快取策略的具體實作。

## Vendor / Platform 清單

實作時的常用選擇見 [vendors](/backend/02-cache-redis/vendors/) — T1 收錄 Redis / Valkey / Memcached / DragonflyDB / AWS ElastiCache，每個 vendor 有定位、適用場景、取捨與預計實作話題的骨架。

## 暫定分類

| 分類                                                                                 | 內容方向                                                                               |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| [Cache aside](/backend/knowledge-cards/cache-aside)                                  | read-through 思路、cache [miss](/backend/knowledge-cards/cache-hit-miss)、invalidation |
| [TTL](/backend/knowledge-cards/ttl) 與 [eviction](/backend/knowledge-cards/eviction) | 過期策略、容量控制、熱點資料                                                           |
| Redis data types                                                                     | string、hash、set、sorted set、stream 的適用場景                                       |
| Presence store                                                                       | 即時連線狀態、過期清理、跨節點查詢                                                     |
| Distributed lock                                                                     | lock 語意、租約、失效與風險                                                            |
| [Pub/Sub](/backend/knowledge-cards/pub-sub)                                          | 即時通知、跨節點 [fan-out](/backend/knowledge-cards/fan-out)、可靠性限制               |

## 選型入口

快取選型的核心判斷是資料是否可以重建，以及讀取壓力是否集中。當正式狀態已經存在於資料庫或下游服務，但熱門讀取造成延遲、成本或容量壓力時，快取與 Redis 值得優先評估。

Cache aside 適合商品詳情、權限摘要、[feature flag](/backend/knowledge-cards/feature-flag) 這類可重建讀取資料；[TTL](/backend/knowledge-cards/ttl/) 與 [eviction](/backend/knowledge-cards/eviction/) 用來控制資料新鮮度與容量；Redis data types 用來表達 set、sorted set、hash、stream 等不同資料形狀；presence store 適合即時連線狀態；distributed lock 適合需要短時間互斥的協調流程；pub/sub 適合即時 fan-out。

接近真實網路服務的例子包括熱門商品頁、會員 session、[WebSocket](/backend/knowledge-cards/websocket/) presence、[rate limit](/backend/knowledge-cards/rate-limit/) counter 與跨節點通知。這些場景的共同問題是讀取節奏、過期策略與資料一致性，因此本模組會先處理資料形狀、[hot key](/backend/knowledge-cards/hot-key/)、[cache stampede](/backend/knowledge-cards/cache-stampede/)、[thundering herd](/backend/knowledge-cards/thundering-herd/) 與失效邊界。

## 與語言教材的分工

語言教材處理 interface / [protocol](/backend/knowledge-cards/protocol/)、並發或非同步保護、[timeout](/backend/knowledge-cards/timeout) 與 cache 呼叫邊界。Backend cache 模組處理 Redis command、資料結構、失效策略、跨節點一致性與操作風險。

## 案例驅動讀法

快取案例的核心讀法是先看「一致性問題長什麼樣」，再決定要調策略還是調架構。

| 案例                                                                                               | 先看章節                                                                                                | 回寫目標                           |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| [2.C1 Meta：Cache Consistency 升級](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/) | [2.2](/backend/02-cache-redis/cache-aside/)、[2.3](/backend/02-cache-redis/ttl-eviction/)               | 把 invalidation 問題前移到訊號治理 |
| [2.C2 Meta：mcrouter 跨區路由](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)  | [2.1](/backend/02-cache-redis/high-concurrency-access/)、[2.5](/backend/02-cache-redis/presence-store/) | 把快取路由層納入可用性邊界         |
| [2.C3 Shopify：序列化遷移](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)   | [2.2](/backend/02-cache-redis/cache-aside/)                                                             | 把格式轉換做成雙軌相容與可回退流程 |

## 章節列表

| 章節                                                              | 主題                                          | 關鍵收穫                                                                                                                                  |
| ----------------------------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| [2.1](/backend/02-cache-redis/high-concurrency-access/)           | 高併發下的 Redis 讀寫邊界                     | 共用 client、控制 pipeline、避免 [hot key](/backend/knowledge-cards/hot-key) 與 [cache stampede](/backend/knowledge-cards/cache-stampede) |
| [2.2](/backend/02-cache-redis/cache-aside/)                       | cache aside 與失效策略                        | 寫出讀取優先的 cache 流程與失效方式                                                                                                       |
| [2.3](/backend/02-cache-redis/ttl-eviction/)                      | TTL 與 eviction                               | 規劃過期、淘汰與容量控制                                                                                                                  |
| [2.4](/backend/02-cache-redis/distributed-lock/)                  | distributed lock 與租約                       | 分辨鎖語意、租約風險與適用場景                                                                                                            |
| [2.5](/backend/02-cache-redis/presence-store/)                    | presence store 與即時狀態                     | 追蹤線上狀態、跨節點查詢與過期清理                                                                                                        |
| [2.6](/backend/02-cache-redis/attacker-view-cache-risks/)         | 攻擊者視角（紅隊）：快取弱點判讀              | 用一致性、污染與放大流量風險檢查快取設計                                                                                                  |
| [2.7](/backend/02-cache-redis/cache-copy-freshness-boundary/)     | Cache Copy Boundary 與 Freshness              | 分辨快取副本、正式狀態、新鮮度與回源保護                                                                                                  |
| [2.8](/backend/02-cache-redis/cache-data-shape-access-pattern/)   | Cache Data Shape 與 Access Pattern            | 用 key space、value shape 與 access pattern 判讀資料形狀                                                                                  |
| [2.9](/backend/02-cache-redis/cache-migration-stampede-rollback/) | Cache Migration 與 Stampede Rollback 實作示範 | 以商品詳情或價格快取示範 evidence、gate 與 rollback trigger                                                                               |
| [2.C](/backend/02-cache-redis/cases/)                             | 轉換案例正文                                  | 把快取策略、路由層與序列化遷移轉成可回寫實作                                                                                              |

反例與規模對照入口： [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) / [2.C10 對照](/backend/02-cache-redis/cases/contrast-cache-strategy-by-scale/)。

回退判讀寫法見 [0.C4 回退判讀寫法](/backend/00-service-selection/cases/post-scale-migration-language-tool-architecture/#回退判讀寫法)，快取案例要優先保留回源壓力、資料新鮮度與熱門 key 行為。

## 觀念網路補完方向

快取章節下一輪的核心責任是把「暫存副本」和「正式狀態」的界線寫清楚。現有章節已經有 cache aside、TTL、distributed lock 與 presence store，但還需要補上資料新鮮度、失效語意、回源保護與快取遷移之間的引用關係，讓讀者知道快取策略何時只是加速，何時已經變成服務正確性風險。

| 補完方向            | 需要回答的問題                                       | 主要路由                                                                                                                                          |
| ------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cache copy boundary | cache value 是否只是可重建副本，還是被誤用成正式狀態 | [source of truth](/backend/knowledge-cards/source-of-truth/)、[1.1](/backend/01-database/high-concurrency-access/)                                |
| Freshness window    | stale data 在產品上可接受多久，誰承擔錯誤後果        | [stale data](/backend/knowledge-cards/stale-data/)、[4.17](/backend/04-observability/telemetry-data-quality/)                                     |
| Invalidation model  | 更新、刪除、TTL、event invalidation 是否互相對齊     | [cache invalidation](/backend/knowledge-cards/cache-invalidation/)、[2.2](/backend/02-cache-redis/cache-aside/)                                   |
| Origin protection   | miss、hot key、stampede 是否會把壓力打回資料庫       | [cache stampede](/backend/knowledge-cards/cache-stampede/)、[6.20](/backend/06-reliability/experiment-safety-boundary/)                           |
| Cache migration     | key format、value schema、TTL 策略是否能分批回退     | [2.C3](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)、[8.22](/backend/08-incident-response/incident-evidence-write-back/) |

這些方向要用快取自己的服務壓力展開。商品詳情、價格、權限摘要、presence 與 rate limit 的失敗代價不同，寫作時要分別處理它們的新鮮度與回源壓力。

## 知識卡補強方向

快取模組的 knowledge card 缺口集中在「新鮮度」與「回源保護」。已有 [cache hit rate](/backend/knowledge-cards/cache-hit-rate/)、[cache warmup](/backend/knowledge-cards/cache-warmup/)、[cache prefetching](/backend/knowledge-cards/cache-prefetching/) 與 [stale data](/backend/knowledge-cards/stale-data/) 可以先引用。

下一批候選卡片包括 freshness window、origin protection、request coalescing、negative cache、cache key versioning 與 cache serialization migration。這些卡片要讓讀者能分辨「可短暫不新鮮」和「錯誤會直接影響交易或權限」的差異。

## 實作探討入口

快取的第一條實作路徑是 [2.9 Cache Migration 與 Stampede Rollback（實作示範）](/backend/02-cache-redis/cache-migration-stampede-rollback/)。這篇以商品詳情或價格快取為例，說明 cache evidence package、origin protection gate、warmup plan 與 rollback trigger 如何一起成立。

這條路徑的前置引用應該是 2.2 cache aside、2.3 TTL / eviction、[2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)、[4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/) 與 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。完成後再回寫 [0.15 後端實作教學大綱](/backend/00-service-selection/implementation-teaching-outline/)。

快取路徑的 artifact 對齊重點是「先證明回源壓力受控，再擴大快取覆蓋率」。對 [4.17](/backend/04-observability/telemetry-data-quality/) / [4.20](/backend/04-observability/observability-evidence-package/) 要交 `Source/Time range/Query link/Owner/Data quality`，並覆蓋 hit/miss、origin QPS、stale read 與 hot key 分布；對 [6.20](/backend/06-reliability/experiment-safety-boundary/) / [6.8](/backend/06-reliability/release-gate/) 要交 `Gate decision/Checks/Stop condition/Rollback window/Owner`，呈現 warmup 演練與 stampede 停損門檻；對 [8.22](/backend/08-incident-response/incident-evidence-write-back/) / [8.19](/backend/08-incident-response/incident-decision-log/) 要交 `Timestamp/Decision/Context/Evidence/Owner/Expected effect/Rollback condition`，記錄 key pattern、影響範圍與修復後追蹤信號。

## 跨語言適配評估

快取與 Redis 的使用方式會受語言的資料複製模型、client lifecycle、序列化成本與並發模型影響。同步 runtime 要避免每個 request 建立連線；async runtime 要避免 blocking Redis client 卡住 event loop；輕量並發 runtime 要用 timeout、[rate limit](/backend/knowledge-cards/rate-limit) 與 pipeline 邊界保護 Redis。動態語言要特別留意 cache value schema 演進；強型別語言則要避免把內部型別直接當成跨服務快取 [contract](/backend/knowledge-cards/contract/)。
