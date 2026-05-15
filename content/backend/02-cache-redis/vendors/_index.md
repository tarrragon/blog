---
title: "快取 Vendor 清單"
date: 2026-05-01
description: "規劃快取、Redis 相容服務與 managed cache 的服務頁撰寫順序與判準"
weight: 90
tags: ["backend", "cache", "vendor"]
---

快取 Vendor 清單的核心責任是把 cache 服務名稱放回副本語意、資料新鮮度、回源保護與操作成本的判斷。每個服務頁先回答它承擔哪種暫存責任，再討論資料型別、失效策略、容量模型、HA / managed 邊界與案例回寫。

## 讀法

快取服務要從資料生命週期進入。讀者如果要保護資料庫讀取壓力，先回到 [2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)；如果要判斷 TTL 與淘汰，先回到 [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)；如果服務已經把 cache 當主要 serving layer，先回到 [2.7 Cache Copy Boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)。

## T1 服務頁大綱

| 服務                                                                | 類型                 | 頁面要回答的核心問題                                    |
| ------------------------------------------------------------------- | -------------------- | ------------------------------------------------------- |
| [Redis](/backend/02-cache-redis/vendors/redis/)                     | Data structure cache | data types、persistence、cluster 與授權變動如何影響選型 |
| [Valkey](/backend/02-cache-redis/vendors/valkey/)                   | Redis-compatible     | Redis 相容性、開源治理與 managed ecosystem 如何取捨     |
| [Memcached](/backend/02-cache-redis/vendors/memcached/)             | Simple KV cache      | 純快取、低語意與水平擴張如何降低操作成本                |
| [DragonflyDB](/backend/02-cache-redis/vendors/dragonflydb/)         | Redis-compatible     | 多核心架構、相容性與高吞吐 cache workload 如何評估      |
| [AWS ElastiCache](/backend/02-cache-redis/vendors/aws-elasticache/) | Managed cache        | managed Redis / Valkey / Memcached 如何轉移維運責任     |

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

## 撰寫批次

| 批次 | 服務頁                     | 撰寫目的                                                   |
| ---- | -------------------------- | ---------------------------------------------------------- |
| C1   | Redis / Valkey             | 建立 Redis baseline、授權治理與相容性判準                  |
| C2   | Memcached / DragonflyDB    | 建立低語意 KV cache 與高吞吐相容替代的取捨                 |
| C3   | AWS ElastiCache            | 建立 managed cache、failover、upgrade 與成本邊界           |
| C4   | KeyDB / Momento / Caffeine | 補 multi-threaded fork、serverless cache、local cache 對照 |

## 後續候選

| 類型                | 候選服務                                        | 寫作重點                                           |
| ------------------- | ----------------------------------------------- | -------------------------------------------------- |
| Redis fork / compat | KeyDB、Garnet                                   | 相容性、multi-threading、client behavior           |
| Managed cache       | Momento、Azure Cache for Redis、GCP Memorystore | serverless cost、managed SLA、vendor boundary      |
| Distributed cache   | Hazelcast、Aerospike                            | cluster memory、near-cache、durability boundary    |
| Local cache         | Caffeine、Guava Cache                           | process-local cache、invalidation、memory pressure |
| HTTP / edge cache   | Varnish、Cloudflare Cache、Fastly、CloudFront   | edge TTL、origin protection、purge workflow        |

主流覆蓋檢查的重點是把 cache 分成 process-local、service-local、distributed 與 edge 四層。Redis 系列解 service-local / distributed data structure cache；Caffeine / Guava 解 process-local；Varnish、Cloudflare、Fastly、CloudFront 解 HTTP / edge cache；Hazelcast、Aerospike 解更重的 distributed data / cache 邊界。

## 下一步路由

- 上游：[2.2 Cache Aside](/backend/02-cache-redis/cache-aside/)
- 上游：[2.7 Cache Copy Boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/)
- 案例：[2.C 快取案例正文](/backend/02-cache-redis/cases/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
