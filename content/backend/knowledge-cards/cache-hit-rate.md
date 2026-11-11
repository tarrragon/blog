---
title: "Cache Hit Rate"
date: 2026-04-23
description: "說明快取命中比例如何衡量加速效果與下游保護"
weight: 90
---

Cache hit rate 的核心概念是「快取命中次數佔總讀取次數的比例」。它用來衡量快取是否真的承擔讀取流量。 可先對照 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/)。

## 跟其他概念的關係

Hit rate 是容量與成本指標。低 hit rate 可能代表快取資料不適合、key 太分散、TTL 太短、資料經常失效或工作負載不重複。 可先對照 [Cache Invalidation](/backend/knowledge-cards/cache-invalidation/)。

## 可觀察訊號與例子

系統需要 hit rate 的訊號是 Redis 成本上升但資料庫壓力仍高。若搜尋結果每次 query 都不同，快取命中率可能很低；商品詳情這類重複讀取則更適合快取。

## 判斷條件與後果

Hit rate 單獨看時，三種不同的狀態都顯示成命中率高。hit rate 高而下游 query count 沒有下降時，命中的是本來就便宜的讀取，成本高的查詢仍然打到資料庫；hit rate 上升伴隨 cache size 持續成長時，命中率是用記憶體換來的，快取的成本跟著上升；TTL 長而失效漏掉時，命中的是過期資料，使用者讀到舊價格或舊庫存。所以 hit rate 和下游 query count、cache size、資料新鮮度一起看，latency 則確認命中是否縮短了回應時間。
