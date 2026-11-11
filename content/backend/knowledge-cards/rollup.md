---
title: "Rollup / Downsampling"
date: 2026-06-22
description: "說明時間序列資料隨時間降低精度以控制儲存成本與查詢效能的機制"
weight: 326
tags: ["backend", "observability"]
---

Rollup 用降低時間精度換取儲存成本與查詢效能。原始資料以秒級或分鐘級採集，隨時間推移被聚合成更粗的粒度（5 分鐘、1 小時、1 天），舊的高精度資料可以刪除或歸檔。它是 [storage tiering](/backend/knowledge-cards/storage-tiering/) 在時間維度的具體實作，跟 [recording rule](/backend/knowledge-cards/recording-rule/) 分工互補。

## 跟其他概念的關係

Rollup 是 [storage tiering](/backend/knowledge-cards/storage-tiering/) 在時間維度的具體實作。它跟 [recording rule](/backend/knowledge-cards/recording-rule/) 的差別在於：recording rule 是降維度（把多個 label 聚合成一條 series），rollup 是降時間精度（把 15 秒的點變成 5 分鐘的點）。兩者經常搭配使用。

## 判斷條件與後果

Rollup 每一層的精度與保留期決定能回看多遠、多細，聚合函數則決定聚合後的資料還能回答哪些查詢。對 counter 做 sum、對 gauge 做 average 時，聚合後的值保有原本的語意；對 histogram 做 average 時，分布資訊在聚合那一刻就消失，粗粒度那一層再也算不出百分位數，而原始資料已經過了保留期，無法重算。

查詢路由決定使用者拿到哪一層的資料：查詢 7 天範圍時系統路由到 5 分鐘粒度，查詢 90 天範圍時路由到 1 小時粒度。路由規則沒有讓使用者看見時，同一張 panel 換了時間範圍之後曲線的形狀改變，使用者分不出是資料本身變了還是精度變了。

## 使用情境

需要 rollup 的訊號是 TSDB 儲存成本持續成長、長時間範圍的 dashboard panel 查詢逾時、或保留政策因為儲存限制被迫縮短。Thanos compactor、Cortex/Mimir compactor、VictoriaMetrics downsampling 都是常見實作。

彙總用累加還是重算、重算的範圍怎麼取才不漏掉晚到的事件，見 [1.18 高頻計數的寫入與彙總：熱點列的鎖、只新增的事件、可以重跑的彙總與重送的事件](/backend/01-database/high-frequency-counting/)〈彙總的兩種寫法：累加新的事件，或重算一段時間〉。

在觀測領域的查詢設計見 [4.2 metrics 聚合查詢](/backend/04-observability/metrics-basics/) 跟 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
