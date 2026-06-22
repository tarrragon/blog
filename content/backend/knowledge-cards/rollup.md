---
title: "Rollup / Downsampling"
date: 2026-06-22
description: "說明時間序列資料隨時間降低精度以控制儲存成本與查詢效能的機制"
weight: 325
tags: ["backend", "observability"]
---

Rollup 用降低時間精度換取儲存成本與查詢效能。原始資料以秒級或分鐘級採集，隨時間推移被聚合成更粗的粒度（5 分鐘、1 小時、1 天），舊的高精度資料可以刪除或歸檔。

## 概念位置

Rollup 是 [storage tiering](/backend/knowledge-cards/storage-tiering/) 在時間維度的具體實作。它跟 [recording rule](/backend/knowledge-cards/recording-rule/) 的差別在於：recording rule 是降維度（把多個 label 聚合成一條 series），rollup 是降時間精度（把 15 秒的點變成 5 分鐘的點）。兩者經常搭配使用。

## 設計責任

設計 rollup 時要定義每一層的精度、保留期、聚合函數與查詢路由規則。聚合函數的選擇影響查詢語意：對 counter 做 sum 跟對 gauge 做 average 是合理的；但對 histogram 做 average 會失去分布資訊。

查詢路由是 rollup 設計的關鍵配套。使用者查詢 7 天範圍時系統自動路由到 5 分鐘粒度、查詢 90 天範圍時路由到 1 小時粒度。若路由不透明，使用者會對精度差異產生困惑。

## 使用情境

需要 rollup 的訊號是 TSDB 儲存成本持續成長、長時間範圍的 dashboard panel 查詢逾時、或保留政策因為儲存限制被迫縮短。Thanos compactor、Cortex/Mimir compactor、VictoriaMetrics downsampling 都是常見實作。

在觀測領域的查詢設計見 [4.2 metrics 聚合查詢](/backend/04-observability/metrics-basics/) 跟 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
