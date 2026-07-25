---
title: "Cache Serialization Migration"
date: 2026-07-20
description: "說明快取 value 編碼格式演進時如何用雙軌解碼避免舊資料變成無法讀取的錯誤"
weight: 392
tags: ["backend", "knowledge-card", "cache", "migration"]
---

Cache serialization migration 的核心責任是讓快取 value 的編碼格式（例如從 Marshal 換成 MessagePack）安全演進，不讓舊格式的快取資料在切換後變成無法解碼的錯誤。它跟 [cache key versioning](/backend/knowledge-cards/cache-key-versioning/) 是同一次 migration 常見的兩個獨立維度——key versioning 處理 key 結構是否共存，serialization migration 處理 value 的編碼格式是否共存。

## 概念位置

Cache serialization migration 位在 [schema migration](/backend/knowledge-cards/schema-migration/) 的快取層對應：資料庫欄位改型別要處理新舊 schema 相容，快取 value 換編碼器要處理新舊 decoder 相容。它跟訊息佇列的 [event schema compatibility](/backend/knowledge-cards/event-schema-compatibility/) 面對相同的核心問題（新舊格式互通），差別在事件 schema 相容通常靠 Schema Registry 或應用層約定，快取序列化遷移多半靠雙軌編碼器手動實作。

## 可觀察訊號與例子

需要 cache serialization migration 的訊號是 schema 變化讓現有序列化格式無法有效表達新欄位、或編碼效率成為瓶頸。序列化格式換的失敗模式是「舊格式無法用新 decoder 讀」——欄位重新命名或型別變更時，反序列化可能直接失敗（應用層視為 miss、全部回源），也可能反序列化成功但語意錯誤（型別從 int 換成 string，業務邏輯讀到錯誤值卻不報錯）。Shopify 把快取 payload 從 Marshal 轉 MessagePack 是這類遷移的代表案例。

## 設計責任

安全的序列化遷移用雙軌策略收斂：新格式可編碼就先寫新格式，編碼失敗回落舊格式保留服務可用性，維持一段雙軌期觀測命中率與錯誤率，確認新格式編碼成功率達標後才收斂到單一格式。這個切換要跟 key versioning 分開推進——序列化格式換跟 key 結構換若同時發生，出錯時無法定位是哪個維度造成的，應該分別驗證再疊加。序列化遷移跟 schema migration 同級——需要相容窗口與回退路徑、把它當純技術重構會漏掉這兩樣。完整雙軌策略與收斂節奏見 [2.C3 Shopify：快取序列化格式遷移](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/)，實作步驟見 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。
