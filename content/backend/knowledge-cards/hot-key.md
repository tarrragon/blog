---
title: "Hot Key"
date: 2026-04-23
description: "說明單一 key 承受大量讀寫時如何形成容量瓶頸"
weight: 22
---

Hot key 的核心概念是「少數 key 承受遠高於平均值的流量」。快取、資料庫、broker partition、rate limit counter 與排行榜都可能因 hot key 形成單點瓶頸。熱點集中在儲存層的單一分區時，見 [Hot Partition](/backend/knowledge-cards/hot-partition/)。

## 跟其他概念的關係

Hot key 是流量分布問題。總 QPS 看起來可承受時，單一商品、直播間、明星帳號、熱門活動或全域 counter 仍可能把某個 shard、partition 或 Redis node 打滿。同一個熱門 key 的快取同時過期時，大量請求一起回源，那是 [Cache Stampede](/backend/knowledge-cards/cache-stampede/)。

## 可觀察訊號與例子

系統需要 hot key 分析的訊號是整體容量尚可，但特定頁面、特定商品或特定 tenant 延遲異常。大型促銷活動中，熱門商品庫存 key 可能比其他商品多出數百倍讀寫。

## 判斷條件與後果

Hot key 的判斷條件是集中的流量是讀還是寫。熱點是讀時，local cache 或讀寫分離把讀取分散到多個副本，代價是副本的資料比正式狀態舊；熱點是寫時（熱門商品的庫存、全域 counter），副本分擔不了寫入，分散的方式是把一個 key 拆成多個分片或改成批次更新，代價是讀取時要合併分片或接受批次之間的延遲。分散的做法都來不及生效時，限流與降級把超出的流量擋在那個 key 之外，同一個 node 上的其他 key 照常服務。觀測只看總 QPS 時，整體容量尚可而單一 shard 已經打滿，所以流量要能按 key pattern、tenant、topic 或 partition 拆開看集中度。
