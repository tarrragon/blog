---
title: "快取 Vendor 清單"
date: 2026-05-01
description: "規劃快取、Redis 相容服務與 managed cache 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "cache", "vendor"]
---

快取 Vendor 清單的核心責任是把 cache 服務名稱放回副本語意、資料新鮮度、回源保護與操作成本的判斷。每個服務頁先回答它承擔哪種暫存責任，再討論資料型別、失效策略、容量模型、HA / managed 邊界與案例回寫。在挑單一服務之前先有一個更上層的判斷：這塊快取能力該自管 Redis、用 managed cache（ElastiCache、MemoryDB）、還是用 serverless cache（Upstash）或含 cache 的 BaaS bundle — 逐能力的買 vs 建判讀見 [0.22 能力級買 vs 建](/backend/00-service-selection/capability-buy-vs-build/)。

## 讀法

快取服務要從資料生命週期進入。讀者如果要保護資料庫讀取壓力，先回到 [2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)；如果要判斷 TTL 與淘汰，先回到 [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)；如果服務已經把 cache 當主要 serving layer，先回到 [2.7 Cache Copy Boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)。

## 教學順序同步

快取服務頁的教學順序是先建立 Redis / Valkey baseline，再比較 Memcached、DragonflyDB 與 managed cache。這個順序對齊 checkout E2：讀者先理解可重建副本、新鮮度與回源保護，再比較同類服務如何改變相容性、memory model、failover 與 managed operation。

## T1 服務頁大綱

| 服務                                                                | 類型                 | 頁面要回答的核心問題                                    |
| ------------------------------------------------------------------- | -------------------- | ------------------------------------------------------- |
| [Redis](/backend/02-cache-redis/vendors/redis/)                     | Data structure cache | data types、persistence、cluster 與授權變動如何影響選型 |
| [Valkey](/backend/02-cache-redis/vendors/valkey/)                   | Redis-compatible     | Redis 相容性、開源治理與 managed ecosystem 如何取捨     |
| [Memcached](/backend/02-cache-redis/vendors/memcached/)             | Simple KV cache      | 純快取、低語意與水平擴張如何降低操作成本                |
| [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)         | Redis-compatible     | 多核心架構、相容性與高吞吐 cache workload 如何評估      |
| [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/) | Managed cache        | managed Redis / Valkey / Memcached 如何轉移維運責任     |

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、其他形式代表 same-vendor 的 topology / version / config 變動。

| Vendor                              | Deep article                                                                                                                                                                                                                                                                                      | Migration playbook                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| [Redis](redis/)                     | [memory-eviction-tuning](redis/memory-eviction-tuning/) / [persistence-fork-latency](redis/persistence-fork-latency/) / [sentinel-ha-failover](redis/sentinel-ha-failover/) / [connection-pipeline-latency](redis/connection-pipeline-latency/) / [cluster-resharding](redis/cluster-resharding/) | [→ Valkey](redis/migrate-to-valkey/) / [→ DragonflyDB](redis/migrate-to-dragonflydb/) / [→ Memcached](redis/migrate-to-memcached/) |
| [Valkey](valkey/)                   | [redis-compatibility-and-io-threads](valkey/redis-compatibility-and-io-threads/)                                                                                                                                                                                                                  | —                                                                                                                                  |
| [Memcached](memcached/)             | [slab-allocator-memory-economics](memcached/slab-allocator-memory-economics/)                                                                                                                                                                                                                     | —                                                                                                                                  |
| [DragonflyDB](dragonflydb/)         | [shared-nothing-multicore-architecture](dragonflydb/shared-nothing-multicore-architecture/)                                                                                                                                                                                                       | —                                                                                                                                  |
| [AWS ElastiCache](aws-elasticache/) | [managed-responsibility-boundary](aws-elasticache/managed-responsibility-boundary/)                                                                                                                                                                                                               | —                                                                                                                                  |
| [KeyDB](keydb/)                     | [active-active-replication](keydb/active-active-replication/)                                                                                                                                                                                                                                     | —                                                                                                                                  |
| [Momento](momento/)                 | overview-only（見下方註）                                                                                                                                                                                                                                                                         | —                                                                                                                                  |
| [Caffeine](caffeine/)               | [two-tier-cache-invalidation](caffeine/two-tier-cache-invalidation/)                                                                                                                                                                                                                              | —                                                                                                                                  |

備註：[cluster-resharding](redis/cluster-resharding/) 是同 cluster 的 topology 重劃（5 type migration 漏類驗證、形式上歸在 deep article 欄、不是跨 vendor 遷移）。

Momento overview-only 的理由：Momento 是 serverless cache、實作面（無 server 參數、無容量規劃、無 cluster topology）相對薄；本 blog case 庫無 Momento production case、且 SaaS 無法本機驗證。依 [deep article 方法論](/posts/vendor-deep-article-methodology/) 反向判準（無 production 經驗 / case 支撐的純 spec 復述不該寫 deep article），Momento 維持 overview-only、待有 case 或 serverless cost 實證再評估。

進度（2026-06-16）：8 個 vendor 的 deep-article 層收尾完成。5 個 T1 vendor（批次 C1-C5、共 8 篇）+ C4 三個新 vendor 補覆蓋缺口（overview）+ KeyDB / Caffeine 各補 1 篇 deep article（Momento 依方法論維持 overview-only）。剩餘獨立 track：各 vendor 的 migration playbook（Valkey / Memcached / DragonflyDB / ElastiCache 的 migration 欄仍是「—」、走 [migration-playbook-methodology](/posts/migration-playbook-methodology/) 6-type 結構）、各 T1 vendor 進階主題的更多 deep article（Redis distributed lock / modules、Memcached CAS、ElastiCache Global Datastore DR）、後續候選的 Garnet / Hazelcast / Aerospike / Varnish edge cache。

## 服務頁撰寫欄位

| 欄位     | 快取服務頁要保留的問題                                                            |
| -------- | --------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 cache copy、data structure、presence、counter 還是 managed operation       |
| 適用壓力 | hot key、read QPS、origin cost、latency、multi-region、memory cost 哪個壓力最明顯 |
| 替代邊界 | 同類 Redis 相容服務、Memcached、managed cache、local cache 的機會成本             |
| 操作成本 | memory sizing、eviction、backup、failover、cluster upgrade、client compatibility  |
| Evidence | hit rate、miss rate、origin QPS、stale read、eviction、hot key、replication lag   |
| 案例回寫 | Meta、Shopify、Netflix、Cloudflare、Tinder、Tubi、Snap 案例如何提供判準           |

服務責任段要先分辨副本與正式狀態。Redis、Valkey、DragonflyDB 與 ElastiCache 都可能承擔 cache serving layer，但資料是否可重建、stale window 多長、回源壓力是否受控，才是選型判斷的起點。

適用壓力段要保留 workload 語言。商品詳情、session、presence、rate limit、leaderboard、ML feature store 與 edge cache 的資料形狀不同，服務頁要用各自的 freshness、memory、QPS 與回退條件寫。

## 服務頁標準章節

| 章節                 | 快取服務頁要補的內容                                                             |
| -------------------- | -------------------------------------------------------------------------------- |
| 服務定位             | 它是 data structure cache、simple KV、managed cache、local cache 還是 HTTP cache |
| 本章目標             | 讀者能判斷資料是否可重建、stale window、origin protection 與 memory cost         |
| 最短判讀路徑         | 用「miss 打回 origin 是否可承受」快速判斷是否能引入或擴大快取                    |
| 日常操作與決策形狀   | key design、TTL、eviction、warmup、failover、client timeout                      |
| 核心取捨表           | Redis 相容服務、Memcached、managed cache、local cache 的機會成本                 |
| 進階主題             | cluster、persistence、multi-region、serverless cache、module / data type         |
| 排錯與失敗快速判讀   | hit rate、miss rate、origin QPS、hot key、eviction、replication lag              |
| 何時改走其他服務     | durable workflow 轉 queue、正式狀態轉 database、全文查詢轉 search                |
| 不在本頁內的主題     | Redis command 百科、語言 client API 細節、完整調參手冊                           |
| 案例回寫與下一步路由 | 回到 2.C cases、9.C cache capacity cases、4.20 evidence package                  |

## 跨 vendor 議題對照

橫向議題在不同 vendor 用不同 mechanism 達成。本表列同一議題在 5 個 vendor 的對應位置、確保大綱不缺漏、讀者跨 vendor 查找時有索引。

| 議題              | Redis                                  | Valkey                                          | Memcached                    | DragonflyDB                            | AWS ElastiCache                                    |
| ----------------- | -------------------------------------- | ----------------------------------------------- | ---------------------------- | -------------------------------------- | -------------------------------------------------- |
| Redis API 相容度  | 原生（最高）                           | 100%（fork 7.2.4）                              | 不相容（純 KV）              | 高（少數 commands 不支援）             | Engine 決定（Redis/Valkey 100%、Memcached 不適用） |
| Data types        | 6 大 + Stream / Geo                    | 跟 Redis 一致                                   | 純 string KV                 | 跟 Redis 一致                          | 跟 engine 一致                                     |
| 多核 / 多執行緒   | I/O threads（main 仍單線）             | Valkey 8 強化 async I/O threading（超出 Redis） | 原生多執行緒                 | 完全 shared-nothing 多核               | 跟 engine 一致                                     |
| Cluster mode      | Cluster + Sentinel                     | 跟 Redis 一致                                   | Client-side ketama hashing   | Single instance scale-up（無 Cluster） | Cluster mode enabled/disabled                      |
| 持久化策略        | AOF + RDB                              | 跟 Redis 一致                                   | 無持久化                     | Fork-less snapshot                     | Automatic + manual snapshot                        |
| 跨 AZ / 多 region | Sentinel + replication / Cluster geo   | 跟 Redis 一致                                   | 需 Mcrouter / EVCache 等代理 | Replica 模式                           | Multi-AZ + Global Datastore                        |
| 授權模式          | RSALv2 / SSPL（非 OSI）                | BSD 3-clause（OSI）                             | BSD（OSI）                   | BSL（4 年後轉 Apache 2.0）             | AWS managed pricing                                |
| Managed level     | 自管                                   | 自管 / managed Valkey 可選                      | 自管                         | 自管（無 Dragonfly managed）           | Fully managed                                      |
| 主討論案例        | 2.C1-C8（跨 Meta / Netflix / Shopify） | 待補（fork 較新）                               | 2.C4 Mcrouter / 2.C5 EVCache | 待補（採用較新）                       | 2.C5 EVCache / 2.C8 Shopify                        |

對照表的用途有三：

- 寫某 vendor 頁時、檢查橫向議題是否都有對應的進階主題子段
- 讀者在 vendor 間遷移時、知道對應 mechanism 在另一個 vendor 叫什麼
- 評估遷移風險：相容度 + 授權 + 生態三維度合併判讀

下面 8 段把對照表的每行展開、避免裸表格成為終點。

### Redis API 相容度

API 相容度決定 client / 工具 / module 是否能直接遷移。**Redis** 是 reference 實作；**Valkey** 100% 相容（直接 drop-in、所有 client library 可用）；**DragonflyDB** 相容核心 commands 但部分 module / Lua 行為差異、不支援 Redis Cluster mode；**Memcached** 跟 Redis 完全不相容（protocol 不同、無 data types）；**ElastiCache** 取決於 engine（Redis / Valkey 100%、Memcached 是另一條線）。

選型判讀：既有 Redis 部署遷移 → Valkey 最低風險；要 scale up single instance → DragonflyDB 可評估但確認 module 跟 Cluster mode 影響；純 KV 從 Redis 改 Memcached → 等同重寫（不是相容問題、是 capability 差異）。

### Data types

Data types 影響可用場景。**Redis / Valkey** 提供 string / hash / list / set / sorted set / stream / hyperloglog / geo — leaderboard / session / counter / distributed lock 等都有原生支援；**Memcached** 純 string KV — 任何複雜結構要在 application 層自己處理（serialize JSON 等）；**DragonflyDB** 跟 Redis 一致；**ElastiCache** 取決於 engine。

選型判讀：需要 sorted set / streams / hash → Redis 系列；純 cache GET/SET → Memcached 更輕；想用 Redis data types 但要極高 throughput → DragonflyDB。

### 多核 / 多執行緒

多核利用度差異大。**Redis** 主執行緒 + I/O threads（Redis 6+）— main thread 仍處理所有 command；**Valkey** 8.x 強化 async I/O threading、把更多 I/O 路徑非同步化、多核吞吐超出 Redis（這是 Valkey fork 後第一個實質技術分歧、見 [Valkey deep article](/backend/02-cache-redis/vendors/valkey/redis-compatibility-and-io-threads/)）；**Memcached** 原生 multi-threaded（`-t` 指定 thread 數）— 適合多核機器；**DragonflyDB** 完全 shared-nothing 多核 — 官方宣稱比 Redis 高 25× throughput（依 workload、以官方 benchmark 為準）；**ElastiCache** 取決於 engine、不能改變。

選型判讀：單 instance 想充分利用 16+ core → DragonflyDB / Memcached；4-8 core 中等場景 → Redis 加 I/O threads 已夠；需要 Redis API + 高 throughput → DragonflyDB 是 sweet spot。

### Cluster mode

擴展拓樸不同。**Redis** Cluster mode（16384 hash slot、可加減 shard）跟 Sentinel mode（HA 無 sharding）；**Valkey** 跟 Redis 一致；**Memcached** 沒有 server-side cluster、靠 client-side consistent hashing（ketama）；**DragonflyDB** 完全沒有 Cluster mode — 哲學是「single instance 撐到很大規模」；**ElastiCache** 提供 Cluster mode enabled / disabled 兩選項、disabled 上限 ~340GB。

選型判讀：超 single instance 容量 → Redis Cluster / ElastiCache Cluster enabled；HA 但容量在單 master → Redis Sentinel / ElastiCache disabled；scale up 機制 → DragonflyDB；極簡 client-side sharding → Memcached。

### 持久化策略

cache 是否需要持久化、view 不一。**Redis** AOF（append-only）+ RDB（snapshot）+ 混合模式；**Valkey** 跟 Redis 一致；**Memcached** 無持久化 — 重啟即 cold cache（嚴格 cache 哲學）；**DragonflyDB** fork-less snapshot（大記憶體場景比 Redis fork 高效）；**ElastiCache** 自動 snapshot + manual snapshot、跨 region 複製。

選型判讀：cache warmup 後不想全失 → Redis AOF / Valkey；純 cache 接受 cold start → Memcached；大記憶體 + snapshot 頻繁 → DragonflyDB fork-less；managed snapshot 不想處理 → ElastiCache。

### 跨 AZ / 多 region

HA 拓樸三類。**Redis** Sentinel + replication（單 region 多 AZ）/ Cluster geo replication（規劃中）；**Valkey** 跟 Redis 一致；**Memcached** 沒有原生 — 靠 Mcrouter / EVCache 等代理做跨 AZ；**DragonflyDB** Replica 模式（primary-replica）跨 AZ 可行、跨 region 需自建；**ElastiCache** Multi-AZ replica（內建）+ Global Datastore（跨 region active-passive）。

選型判讀：自管跨 AZ → Redis Sentinel / Valkey；自管跨 region → Mcrouter 或自建；不想處理跨區 → ElastiCache Multi-AZ + Global Datastore。

### 授權模式

授權直接影響商業使用權利。**Redis** 2024 起 RSALv2 / SSPL（非 OSI 認可）— SaaS 提供 Redis-as-service 受限；**Valkey** BSD 3-clause（OSI 認可）— 商業使用無限制；**Memcached** BSD（OSI）— 開源無限制；**DragonflyDB** BSL（Business Source License）— 4 年後轉 Apache 2.0、目前商業 managed service 提供受限；**ElastiCache** AWS managed pricing — 跟 license 無關（你付的是 AWS 服務費）。

選型判讀：開源合規敏感（公部門 / 企業政策）→ Valkey / Memcached；新部署不在乎 license → Redis / DragonflyDB；不想處理 license → ElastiCache（AWS 處理）。

### Managed level

運維責任轉移程度。**Redis / Valkey** 自管或選 managed（ElastiCache / Memorystore / Azure Cache）；**Memcached** 自管或 ElastiCache；**DragonflyDB** 目前只能自管（無 fully managed offering）；**ElastiCache** 完全 managed（auto failover / snapshot / patching）— 付 managed premium。

選型判讀：team 沒運維 Redis 經驗 → managed（ElastiCache / Memorystore）；要極致控制 → 自管；DragonflyDB 必自管（無 managed）。

## 撰寫批次

| 批次 | 服務頁                        | 撰寫目的                                                                               |
| ---- | ----------------------------- | -------------------------------------------------------------------------------------- |
| C1   | Redis / Valkey                | 建立 Redis baseline、開源治理與相容性判準                                              |
| C2   | Memcached                     | 建立 simple KV cache、低語意副本與水平擴張邊界                                         |
| C3   | DragonflyDB / AWS ElastiCache | 建立高吞吐 Redis-compatible 與 managed cache 的操作取捨                                |
| C4   | KeyDB / Momento / Caffeine    | 補 multi-threaded fork、serverless cache、local cache 對照（overview 完成 2026-06-16） |

## 後續候選

C4 已建立 [KeyDB](keydb/) / [Momento](momento/) / [Caffeine](caffeine/) overview。剩餘候選：

| 類型                | 候選服務                                      | 寫作重點                                           |
| ------------------- | --------------------------------------------- | -------------------------------------------------- |
| Redis fork / compat | Garnet（Microsoft）                           | 相容性、multi-threading、client behavior           |
| Managed cache       | Azure Cache for Redis、GCP Memorystore        | managed SLA、vendor boundary                       |
| Distributed cache   | Hazelcast、Aerospike                          | cluster memory、near-cache、durability boundary    |
| Local cache         | Guava Cache、Ehcache（off-heap）              | process-local cache、invalidation、memory pressure |
| HTTP / edge cache   | Varnish、Cloudflare Cache、Fastly、CloudFront | edge TTL、origin protection、purge workflow        |

主流覆蓋檢查的重點是把 cache 分成 process-local、service-local、distributed 與 edge 四層。Redis 系列 / KeyDB / DragonflyDB 解 service-local / distributed data structure cache；[Caffeine](caffeine/) 解 process-local、[Momento](momento/) 解 serverless cache；Varnish、Cloudflare、Fastly、CloudFront 解 HTTP / edge cache；Hazelcast、Aerospike 解更重的 distributed data / cache 邊界。

## 下一步路由

- 上游：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)
- 上游：[2.7 Cache Copy Boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- 案例：[2.C 快取案例正文](/backend/02-cache-redis/cases/)
- 服務路徑：[2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)
