---
title: "Percentile"
date: 2026-06-22
description: "說明 p95 與 p99 如何描述長尾延遲與使用者體驗"
weight: 100
tags: ["backend", "observability"]
---

Percentile 的核心概念是「某比例的觀測值低於某個門檻」。p95 latency 表示 95% 的 request 延遲低於該值；p99 觀察更長尾的慢請求。Percentile 描述的是分布的尾端，從 [histogram](/backend/knowledge-cards/histogram/) 資料計算而來，用來捕捉 average 掩蓋的使用者體驗問題。

## 概念位置

Percentile 跟 [histogram](/backend/knowledge-cards/histogram/) 搭配使用。Histogram 記錄延遲分布（哪些 bucket 收到多少 request），percentile 從 histogram 資料計算（`histogram_quantile` in PromQL）。Average latency 看不到長尾 — 平均 80ms 但 p99 是 2 秒，代表 1% 的使用者體驗極差。

Percentile 是 [SLI](/backend/knowledge-cards/sli-slo/) 的常見型別 — latency SLI 用「p99 < 500ms 的 request 佔比」量化使用者體驗。

## 使用情境

系統需要 percentile 的訊號是 average latency 穩定但使用者仍回報卡頓。搜尋 API 平均 80ms、p99 2 秒，表示少數 request 走到慢查詢或下游 timeout。高流量服務的 1%（p99 以外）可能代表數千個使用者。

## 設計責任

Percentile 要搭配 histogram bucket 設計 — bucket boundary 決定 percentile 計算的精度。Bucket 太少（只有 100ms / 500ms / 1s）會讓 p99 的估計跳躍式變化。Bucket 太多會增加 [cardinality](/backend/knowledge-cards/metric-cardinality/)。低流量服務的高 percentile 容易受少量樣本影響，alert 閾值要考慮統計穩定性。詳見 [4.2 metrics basics](/backend/04-observability/metrics-basics/) 跟 [4.6 SLI/SLO 訊號設計](/backend/04-observability/sli-slo-signal/)。
