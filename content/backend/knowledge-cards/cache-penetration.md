---
title: "Cache Penetration"
date: 2026-06-16
description: "說明查詢必定不存在的 key 繞過快取直接打向 origin 的弱點與防護"
weight: 385
---

Cache penetration 的核心概念是「查詢必定不存在的 key，讓請求全部 miss 並穿透到資料庫，把快取的保護作用繞過」。它跟 [cache stampede](/backend/knowledge-cards/cache-stampede/) 不同：stampede 是同一個熱門 key 同時失效，penetration 是大量不同的不存在 key 從不命中。 可先對照 [Cache Stampede](/backend/knowledge-cards/cache-stampede/)。

## 跟其他概念的關係

Cache penetration 是快取放大面的攻擊向量，與 [cache stampede](/backend/knowledge-cards/cache-stampede/)、[thundering herd](/backend/knowledge-cards/thundering-herd/) 並列「快取從保護層變成放大層」的失效模式。它的觸發源是惡意或意外的不存在 key 枚舉，主要防護是 [negative cache](/backend/knowledge-cards/negative-cache/) 與回源 [rate limit](/backend/knowledge-cards/rate-limit/)，與 stampede 的 soft-TTL / single-flight 防護路徑不同。 可先對照 [Negative Cache](/backend/knowledge-cards/negative-cache/)。

## 可觀察訊號與例子

判讀訊號是「大量查詢不存在的 key、回源 QPS 飆但 cache 命中率不變」。攻擊者用不連續的 id、構造的非法 slug 枚舉，每個查詢都 miss、穿透到資料庫。電商商品頁被查詢大量不存在的商品 id，資料庫被迫對每個都做一次「查無此商品」的查詢，快取完全沒擋住。

## 判斷條件與後果

快取只存查得到的結果時，查詢不存在的 key 永遠 miss，每一個請求都打到資料庫。不存在的結果也寫進快取（[negative cache](/backend/knowledge-cards/negative-cache/)）時，同一個不存在的 key 第二次查詢就被快取擋下；攻擊者每次換一個新的 key 時 negative cache 擋不到，回源路徑的 rate limit 與請求來源限制決定資料庫最多承受多少這類查詢。penetration 與 stampede 都表現為回源 QPS 上升，分界在 key：大量不同、不存在的 key 是 penetration，同一個熱門 key 同時失效是 stampede。stampede 的 soft TTL 與 single-flight 套在 penetration 上沒有效果，原因是每個不存在的 key 只被查一次，沒有可以合併的重建或可以延後的過期。
