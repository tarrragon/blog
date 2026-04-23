---
title: "Cache Hit / Miss"
date: 2026-04-23
description: "說明快取命中與未命中如何影響讀取成本與下游壓力"
weight: 88
---

Cache hit / miss 的核心概念是「讀取是否在快取中找到可用資料」。Hit 表示快取提供結果；miss 表示 application 需要回到正式來源或其他資料路徑。

## 概念位置

Hit / miss 是快取效益的基礎訊號。Hit 越高，通常表示下游讀取壓力越低；miss 上升可能來自 TTL 太短、eviction、key 設計錯誤、流量型態改變或資料剛被清除。

## 可觀察訊號與例子

系統需要觀察 hit / miss 的訊號是快取導入後仍然沒有降低資料庫壓力。熱門商品頁若 miss rate 高，資料庫仍會承受大量查詢。

## 設計責任

Hit / miss 指標要按 key pattern、endpoint、tenant 或資料類型切分。Runbook 應說明 miss 上升時如何檢查 TTL、eviction、cache invalidation 與 cache stampede。
