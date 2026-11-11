---
title: "Cache Prefetching"
date: 2026-04-23
description: "說明系統如何在資料被需要前預先載入快取"
weight: 92
---

Cache prefetching 的核心概念是「根據預期需求提前載入資料」。它讓 request 到來時更可能命中快取，降低使用者等待時間。 可先對照 [Cache Stampede](/backend/knowledge-cards/cache-stampede/)。

## 跟其他概念的關係

Prefetching 是預測型快取策略。它適合可預期的讀取，例如下一頁資料、熱門商品、使用者登入後常用設定或活動頁資源。 可先對照 [Cache Stampede](/backend/knowledge-cards/cache-stampede/)。

## 可觀察訊號與例子

系統需要 prefetching 的訊號是使用者行為有穩定下一步。影片平台可以在使用者接近播放結束時預載下一集資訊；電商可以在活動頁預載熱門商品摘要。

## 判斷條件與後果

Prefetching 的效益取決於預測的準確率：預載的資料越常被讀取，使用者的等待時間降得越多；預測錯的資料佔住快取空間，卻沒有 request 讀它。預載量超過快取容量時，eviction 把真正熱門的資料擠出去，命中率不升反降。預載發生在讀取之前，資料從預載到被讀取的間隔越長，讀到過期資料的機會越大。預載本身也是對下游的讀取，大量預載集中在同一時間（活動開始前）時，下游先承受一波由預載造成的尖峰。
