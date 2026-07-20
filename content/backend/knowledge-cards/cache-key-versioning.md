---
title: "Cache Key Versioning"
date: 2026-07-20
description: "說明快取 key 結構本身版本化如何讓新舊值格式共存，用漸進收斂取代一次性替換"
weight: 391
tags: ["backend", "knowledge-card", "cache", "migration"]
---

Cache key versioning 的核心概念是「把 key 結構本身版本化——例如把 `product:{id}` 演進成 `product:v2:{region}:{id}`——讓新舊 value 格式在同一個快取裡共存」。它是快取層做 migration 時的核心修法，跟資料庫的 [expand-contract](/backend/knowledge-cards/expand-contract/) 策略同樣的動機：一次性替換 key 語意會讓所有讀取瞬間 miss，版本化 key 則讓收斂變成可控的漸進過程。

## 概念位置

Cache key versioning 位在 [schema migration](/backend/knowledge-cards/schema-migration/) 的快取對應層：資料庫 schema 改版有 expand-contract 分階段策略，快取層改版對應的是 dual-read 再 dual-write 再 single-read-v2 的三段收斂。讀取先查新 key、miss 再查舊 key、最後才回源；回填期間新舊 key 同時寫入，保留可回退窗口。它跟 [cache serialization migration](/backend/knowledge-cards/cache-serialization-migration/) 是同一次 migration 常見的兩個獨立維度——key versioning 處理 key 命名與結構是否共存，serialization migration 處理 value 的編碼格式是否共存，兩者可以同時發生但要分開判讀。

## 可觀察訊號與例子

需要 cache key versioning 的訊號是快取 value 的欄位結構要改變，但服務不能接受一次性全量 miss。電商商品快取從 `product:{id}` 演進到 `product:v2:{region}:{id}`，動機是拆分區域價格與促銷欄位，新舊值結構不同，若直接覆蓋舊 key 會讓同一商品在不同 API path 回傳不一致語意，必須先有轉換層或版本化並存期。

## 設計責任

版本化 key 的收斂要按固定順序推進、每步都有停損點：新 key 寫入啟用（停損點是雙寫失敗率）、新 key 命中觀察（停損點是 v2 命中率爬升曲線是否停滯）、舊 key 命中率穩定下降（確認新 key 已自然 warmup、不能只看 v2 命中率）、舊 key 停止寫入、最後移除舊 key 讀 fallback。常見誤判是同時改 key 結構跟 TTL 兩個維度，讓 stampede 或行為異常時無法定位是哪個變因造成的——每次切換應該只動一個維度，先在低流量 region 試跑再擴大。key 演進與相容窗口的完整分階段案例見 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。
