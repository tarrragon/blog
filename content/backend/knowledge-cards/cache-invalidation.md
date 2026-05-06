---
title: "Cache Invalidation"
tags: ["快取失效策略", "Cache Invalidation"]
date: 2026-04-23
description: "說明快取資料何時更新、刪除或重建，以及失效策略如何影響一致性"
weight: 6
---


快取失效策略的核心概念是「定義快取資料何時離開可用狀態」。快取可以加速讀取與降低下游壓力，但資料來源更新後，快取需要透過 TTL、主動刪除、版本鍵、write-through、event invalidation 或重建流程維持合理一致性。 可先對照 [Cache Prefetching](/backend/knowledge-cards/cache-prefetching/)。

## 概念位置

快取失效是讀取效能與資料正確性的交界。失效太頻繁會降低快取命中率；失效太慢會讓使用者看到過期資料。多層快取還會增加判斷難度，因為 browser、CDN、application cache、Redis 與 local memory 可能各自保存不同版本。 可先對照 [Cache Prefetching](/backend/knowledge-cards/cache-prefetching/)。

## 可觀察訊號

系統需要整理失效策略的訊號是資料更新後，讀取結果在不同頁面、不同使用者或不同服務之間出現差異。常見場景包括商品價格、庫存、會員權限、設定檔、排行榜、熱門文章與 feature flag。

## 接近真實網路服務的例子

電商後台更新商品價格後，搜尋頁仍顯示舊價格，商品頁顯示新價格，結帳頁又重新查資料庫。這代表不同讀取路徑使用不同快取層，失效策略需要定義更新事件要清哪些 key、哪些頁面可接受短暫延遲、結帳是否必須讀正式來源。

## 設計責任

快取設計要把資料語意分級。價格、庫存、權限這類影響交易或安全的資料需要更短 TTL、版本控制或讀正式來源；排行榜、推薦與統計可以接受較長延遲。Runbook 應提供查 key、清 key、比對正式資料與追蹤失效事件的方法。
