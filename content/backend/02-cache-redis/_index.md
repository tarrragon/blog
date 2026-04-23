---
title: "模組二：快取與 Redis"
date: 2026-04-22
description: "整理快取策略、Redis 資料型別與分散式狀態輔助能力"
weight: 2
---

快取模組的核心目標是說明暫存資料如何提升讀取效率，同時保護 [source of truth](../knowledge-cards/source-of-truth/) 的正式判斷責任。語言教材會處理 cache port、資料複製邊界與 [TTL](../knowledge-cards/ttl/) 的程式邊界；本模組負責 Redis 與快取策略的具體實作。

## 暫定分類

| 分類             | 內容方向                                         |
| ---------------- | ------------------------------------------------ |
| [Cache aside](../knowledge-cards/cache-aside)      | read-through 思路、cache [miss](../knowledge-cards/cache-hit-miss)、invalidation      |
| [TTL](../knowledge-cards/ttl) 與 [eviction](../knowledge-cards/eviction)  | 過期策略、容量控制、熱點資料                     |
| Redis data types | string、hash、set、sorted set、stream 的適用場景 |
| Presence store   | 即時連線狀態、過期清理、跨節點查詢               |
| Distributed lock | lock 語意、租約、失效與風險                      |
| [Pub/Sub](../knowledge-cards/pub-sub)          | 即時通知、跨節點 [fan-out](../knowledge-cards/fan-out)、可靠性限制             |

## 選型入口

快取選型的核心判斷是資料是否可以重建，以及讀取壓力是否集中。當正式狀態已經存在於資料庫或下游服務，但熱門讀取造成延遲、成本或容量壓力時，快取與 Redis 值得優先評估。

Cache aside 適合商品詳情、權限摘要、[feature flag](../knowledge-cards/feature-flag) 這類可重建讀取資料；[TTL](../knowledge-cards/ttl/) 與 [eviction](../knowledge-cards/eviction/) 用來控制資料新鮮度與容量；Redis data types 用來表達 set、sorted set、hash、stream 等不同資料形狀；presence store 適合即時連線狀態；distributed lock 適合需要短時間互斥的協調流程；pub/sub 適合即時 fan-out。

接近真實網路服務的例子包括熱門商品頁、會員 session、[WebSocket](../knowledge-cards/websocket/) presence、[rate limit](../knowledge-cards/rate-limit/) counter 與跨節點通知。這些場景的共同問題是讀取節奏、過期策略與資料一致性，因此本模組會先處理資料形狀、[hot key](../knowledge-cards/hot-key/)、[cache stampede](../knowledge-cards/cache-stampede/)、[thundering herd](../knowledge-cards/thundering-herd/) 與失效邊界。

## 與語言教材的分工

語言教材處理 interface / [protocol](../knowledge-cards/protocol/)、並發或非同步保護、[timeout](../knowledge-cards/timeout) 與 cache 呼叫邊界。Backend cache 模組處理 Redis command、資料結構、失效策略、跨節點一致性與操作風險。

## 章節列表

| 章節                            | 主題                      | 關鍵收穫                                                   |
| ------------------------------- | ------------------------- | ---------------------------------------------------------- |
| [2.1](high-concurrency-access/) | 高併發下的 Redis 讀寫邊界 | 共用 client、控制 pipeline、避免 [hot key](../knowledge-cards/hot-key) 與 [cache stampede](../knowledge-cards/cache-stampede) |
| [2.2](cache-aside/)             | cache aside 與失效策略    | 寫出讀取優先的 cache 流程與失效方式                        |
| [2.3](ttl-eviction/)            | TTL 與 eviction           | 規劃過期、淘汰與容量控制                                   |
| [2.4](distributed-lock/)        | distributed lock 與租約   | 分辨鎖語意、租約風險與適用場景                             |
| [2.5](presence-store/)          | presence store 與即時狀態 | 追蹤線上狀態、跨節點查詢與過期清理                         |

## 跨語言適配評估

快取與 Redis 的使用方式會受語言的資料複製模型、client lifecycle、序列化成本與並發模型影響。同步 runtime 要避免每個 request 建立連線；async runtime 要避免 blocking Redis client 卡住 event loop；輕量並發 runtime 要用 timeout、[rate limit](../knowledge-cards/rate-limit) 與 pipeline 邊界保護 Redis。動態語言要特別留意 cache value schema 演進；強型別語言則要避免把內部型別直接當成跨服務快取 [contract](../knowledge-cards/contract/)。
