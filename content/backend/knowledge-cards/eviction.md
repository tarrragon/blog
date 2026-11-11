---
title: "Eviction"
date: 2026-04-23
description: "說明快取容量不足時哪些資料會被淘汰，以及淘汰如何影響服務"
weight: 20
---

Eviction 的核心概念是「容量不足時系統選擇移除哪些資料」。快取與記憶體型服務需要 eviction policy，因為可用容量有限，資料量與 hot key 會隨流量變化。 可先對照 [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)。

## 跟其他概念的關係

Eviction 處理的是容量控制，TTL 處理的是時間有效性。Redis、CDN、local cache 都可能在容量壓力下淘汰資料；被淘汰的資料若可重建，系統會承擔額外查詢成本。 可先對照 [Excessive Data Exposure](/backend/knowledge-cards/excessive-data-exposure/)。

## 可觀察訊號與例子

系統需要關注 eviction 的訊號是 cache hit rate 突然下降、Redis memory 接近上限、下游資料庫壓力升高。熱門商品活動可能讓大量 key 進入快取，造成原本常用資料被擠出。

## 判斷條件與後果

被淘汰的資料是否可以重建，決定 eviction 的代價是成本還是遺失。可重建的資料被淘汰時，代價是下一次讀取打到下游的額外查詢，熱門商品活動擠出常用資料時，cache hit rate 下降、資料庫壓力升高；難重建或只存在快取裡的資料被淘汰時，資料直接消失，原因是 eviction policy 只依容量與存取模式挑選要移除的 key，不知道哪一筆資料重要。所以只存在快取裡的高價值資料，要有快取以外的保存位置。可重建的資料也有容量面的判斷：容量規劃沒有算進流量高峰的 key 數量時，淘汰集中在高峰發生，下游在最忙的時候承受最多回源查詢；沒有記憶體用量與 hit rate 的告警時，這個情形要等下游變慢才被發現。
