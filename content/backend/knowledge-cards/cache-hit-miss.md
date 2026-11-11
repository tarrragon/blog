---
title: "Cache Hit / Miss"
date: 2026-04-23
description: "說明快取命中與未命中如何影響讀取成本與下游壓力"
weight: 89
---

Cache hit / miss 的核心概念是「讀取是否在快取中找到可用資料」。Hit 表示快取提供結果；miss 表示 application 需要回到正式來源或其他資料路徑。 可先對照 [Cache Hit Rate](/backend/knowledge-cards/cache-hit-rate/)。

## 跟其他概念的關係

Hit / miss 是快取效益的基礎訊號。Hit 越高，通常表示下游讀取壓力越低；miss 上升可能來自 TTL 太短、eviction、key 設計錯誤、流量型態改變或資料剛被清除。 可先對照 [Cache Hit Rate](/backend/knowledge-cards/cache-hit-rate/)。

## 可觀察訊號與例子

系統需要觀察 hit / miss 的訊號是快取導入後仍然沒有降低資料庫壓力。熱門商品頁若 miss rate 高，資料庫仍會承受大量查詢。

## 判斷條件與後果

Hit / miss 只看全域總數時，一個熱門 key pattern 的 miss 上升會被其他路徑的 hit 平均掉，資料庫壓力升高卻對不回是哪一類請求；按 key pattern、endpoint、tenant 或資料類型切分時，miss 上升能對回具體的資料路徑。miss 上升的成因各自代表不同的狀態：TTL 太短是資料過期得太快，eviction 增加是快取容量放不下工作集，cache invalidation 是資料剛被清除，cache stampede 是熱門 key 失效後大量請求同時回源。runbook 沒有列出這幾種成因的檢查方式時，值班工程師只看得到 miss 上升，分不出該調 TTL、加容量還是追查失效事件。
