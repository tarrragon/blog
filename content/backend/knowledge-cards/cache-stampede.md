---
title: "Cache Stampede"
date: 2026-04-23
description: "說明快取同時失效時大量 request 如何壓垮正式來源"
weight: 23
---

Cache stampede 的核心概念是「大量 request 在同一時間遇到 cache miss，並同時打向正式來源」。這個現象常出現在熱門 key 過期、服務重啟、快取清空或活動流量尖峰。 可先對照 [Cache Warmup](/backend/knowledge-cards/cache-warmup/)。

## 跟其他概念的關係

Cache stampede 是快取失效與下游保護的交界。快取原本用來保護資料庫；若熱門資料同時過期，快取反而會把大量請求集中送到資料庫。 可先對照 [Cache Warmup](/backend/knowledge-cards/cache-warmup/)。

## 可觀察訊號與例子

系統需要處理 stampede 的訊號是 cache miss rate 突然升高，同時資料庫查詢數、latency 與 timeout 上升。熱門文章榜每分鐘整點過期，可能讓所有 request 在同一秒重建同一份資料。

## 判斷條件與後果

Stampede 打到正式來源的查詢數，等於同一時刻 miss 而自己去重建的 request 數。只讓少數 request 重建、其餘 request 使用既有資料或等待有界時間時，正式來源只承受一次重建的查詢；其餘 request 等待沒有上限時，重建一變慢，等待中的請求就累積成大量 timeout。常見策略各自處理重建過程中的一個環節：singleflight 與 lock 把同一個 key 的重建合併成一次，soft TTL 與 background refresh 讓資料在過期前就更新、request 不必等，jitter 把同一批 key 的過期時間錯開，fallback stale data 讓重建失敗時仍有舊值可以回傳。
