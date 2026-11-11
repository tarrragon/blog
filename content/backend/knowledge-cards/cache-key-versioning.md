---
title: "Cache Key Versioning"
date: 2026-07-20
description: "說明快取 key 結構本身版本化如何讓新舊值格式共存，用漸進收斂取代一次性替換"
weight: 392
tags: ["backend", "knowledge-card", "cache", "migration"]
---

Cache key versioning 的核心概念是「把 key 結構本身版本化——例如把 `product:{id}` 演進成 `product:v2:{region}:{id}`——讓新舊 value 格式在同一個快取裡共存」。它是快取層做 migration 時的核心修法，跟資料庫的 [expand-contract](/backend/knowledge-cards/expand-contract/) 策略同樣的動機：一次性替換 key 語意會讓所有讀取瞬間 miss，版本化 key 則讓收斂變成可控的漸進過程。

## 跟其他概念的關係

Cache key versioning 位在 [schema migration](/backend/knowledge-cards/schema-migration/) 的快取對應層：資料庫 schema 改版有 expand-contract 分階段策略，快取層改版對應的是 dual-read 再 dual-write 再 single-read-v2 的三段收斂。讀取先查新 key、miss 再查舊 key、最後才回源；回填期間新舊 key 同時寫入，保留可回退窗口。它跟 [cache serialization migration](/backend/knowledge-cards/cache-serialization-migration/) 是同一次 migration 常見的兩個獨立維度——key versioning 處理 key 命名與結構是否共存，serialization migration 處理 value 的編碼格式是否共存，兩者可以同時發生但要分開判讀。

## 可觀察訊號與例子

需要 cache key versioning 的訊號是快取 value 的欄位結構要改變，但服務不能接受一次性全量 miss。電商商品快取從 `product:{id}` 演進到 `product:v2:{region}:{id}`，動機是拆分區域價格與促銷欄位，新舊值結構不同，若直接覆蓋舊 key 會讓同一商品在不同 API path 回傳不一致語意，必須先有轉換層或版本化並存期。

## 判斷條件與後果

版本化 key 的收斂分成五個階段，每一階段的停損點是能否進入下一階段的條件。新 key 開始寫入時看雙寫失敗率，失敗率升高代表新 key 的寫入路徑本身有錯；新 key 命中觀察期看 v2 命中率的爬升曲線，曲線停滯代表仍有讀取路徑沒有改讀新 key；舊 key 命中率穩定下降，才代表新 key 已經自然 warmup，只看 v2 命中率會漏掉還在讀舊 key 的路徑。這三項都成立之後才停止寫入舊 key，最後移除讀舊 key 的 fallback；舊 key 提早停寫時，回退到舊 key 讀到的是停寫之後沒有更新的值，回退窗口就沒有了。同時改 key 結構與 TTL 兩個維度時，stampede 或行為異常出現後無法定位是哪個維度造成的，所以每次切換只動一個維度，並先在低流量 region 試跑再擴大。key 演進與相容窗口的完整分階段案例見 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。
