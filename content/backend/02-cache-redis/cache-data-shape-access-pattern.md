---
title: "2.8 Cache Data Shape 與 Access Pattern"
date: 2026-05-11
description: "說明 cache value、key space、資料結構與存取型態如何反映服務語意。"
weight: 8
tags: ["backend", "cache", "redis", "data-shape"]
---

Cache data shape 與 access pattern 的核心責任是讓快取資料結構反映服務語意。進入 Redis command 或特定快取服務前，讀者需要先知道 key、value、hash、set、sorted set、stream 與多層 cache 各自適合承擔哪種讀取責任。

## Key Space

Key space 的責任是定義快取資料如何被定位、分組、失效與遷移。key 命名要包含資料責任、版本、租戶或區域等必要維度，讓失效與回退可控。

常見 key 維度包含：

1. 資料類型，例如 `product`、`user-permission`、`quota`。
2. 版本，例如 `v1`、`v2`。
3. 租戶或區域，例如 tenant、region、locale。
4. 實體識別，例如 product id、user id。

key 缺少版本時，cache migration 會變成破壞性替換。key 缺少租戶或區域時，失效範圍會被放大。

## Value Shape

Value shape 的責任是定義快取值的語意與演進方式。完整 JSON blob 適合一次讀取完整資料，但欄位更新與版本相容成本高；hash 適合欄位局部更新，但需要明確欄位責任；set 與 sorted set 適合集合與排名；counter 適合限流或計數。

| 資料形狀      | 適合場景                 | 主要風險                          |
| ------------- | ------------------------ | --------------------------------- |
| string / blob | 商品詳情、設定快照       | schema 變更容易破壞相容           |
| hash          | 使用者摘要、商品局部欄位 | 欄位責任不清會變成半正式狀態      |
| set           | membership、權限集合     | stale membership 可能造成越權     |
| sorted set    | 排名、時間排序、優先級   | score 語意錯誤會造成排序漂移      |
| counter       | rate limit、配額         | 原子性與過期窗口要對齊            |
| stream        | 輕量事件流               | 容易和正式 message queue 責任混淆 |

資料形狀的本質是服務責任選擇，Redis 語法是落地方式。

`string / blob` 的判讀重點是整包資料是否需要一起讀取與一起失效。`hash` 的判讀重點是欄位是否真的能獨立更新。`set` 與 `sorted set` 的判讀重點是 membership 或排序錯誤會造成什麼後果。`counter` 的判讀重點是原子性與過期窗口。`stream` 的判讀重點是這條路徑是否已經接近 message queue 責任。

## Access Pattern

Access pattern 的責任是定義快取面對的讀寫節奏。高讀低寫、熱點讀取、短期活動尖峰、租戶隔離與跨區讀取，都會影響 key 設計與容量策略。

高讀低寫適合長 TTL 與背景刷新；熱點讀取需要 [hot key](/backend/knowledge-cards/hot-key/) 保護；短期尖峰需要 warmup 與分散過期；多租戶場景需要避免單租戶 key 壓垮共享 cache。

## Multi-layer Cache

多層快取的責任是分散延遲與來源壓力。常見層次包含 process local cache、distributed cache、CDN 或 search/read model。每一層都需要定義 freshness、失效來源與 fallback。

多層 cache 的主要風險是 stale 疊加。local cache stale、distributed cache stale 與 CDN stale 缺少共同失效策略時，讀者看到的錯誤會很難追。

## 選型前判準

快取資料形狀選型前要先回答：

1. 讀取是單 key、批次 key、集合、排序還是計數。
2. 寫入是整體替換、局部更新、追加還是原子遞增。
3. 失效是單 key、群組、版本、租戶還是全域。
4. 資料結構是否會讓快取承擔正式狀態責任。

這些問題決定後續要比較 Redis data type、Memcached blob、CDN cache 或應用端 local cache。

## 實體服務討論承接點

實體快取服務文章要承接本篇的 data shape 與 access pattern。Redis/Valkey 的 hash、set、sorted set、stream 能表達多種資料形狀；Memcached 偏向簡單 key/value blob；CDN 與 local cache 則承擔不同層次的讀取加速。比較服務時要先問 access pattern，再問語法。

若讀取是單 key 或 blob，後續文章要比較 serialization、value size、TTL 與 eviction。若讀取是集合、排名或計數，後續文章要比較資料結構、原子性與容量行為。若讀取跨多層 cache，後續文章要比較失效傳播、stale 疊加與 observability。

## 下一步路由

要處理 TTL 與容量策略，接著讀 [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)。要處理 presence 類即時狀態，接著讀 [2.5 presence store 與即時狀態](/backend/02-cache-redis/presence-store/)。
