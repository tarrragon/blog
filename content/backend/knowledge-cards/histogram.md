---
title: "Histogram"
date: 2026-06-22
description: "說明 histogram 如何用分桶統計延遲、大小與分布"
weight: 98
tags: ["backend", "observability"]
---

Histogram 的核心概念是「把觀測值分到多個 bucket，記錄每個範圍的累積數量」。它是 [metrics](/backend/knowledge-cards/metrics/) 中描述分布的工具，常用來觀察 latency、request size、payload size、queue wait time 與處理耗時，支援 [percentile](/backend/knowledge-cards/percentile/) 計算。

## 概念位置

Histogram 是 [metrics](/backend/knowledge-cards/metrics/) 中描述分布的工具，跟 counter（計數）跟 gauge（瞬間值）互補。Average 只能說明中心趨勢；histogram 可以支援 [percentile](/backend/knowledge-cards/percentile/)（p95 / p99）、[SLI](/backend/knowledge-cards/sli-slo/) 計算跟 [burn rate](/backend/knowledge-cards/burn-rate/) 判斷。

Prometheus 的 histogram 用累積 bucket（`le` label）實作 — 每個 bucket 記錄「值 <= le 的觀測次數」。PromQL 的 `histogram_quantile()` 從 bucket 資料估算 percentile。

## 使用情境

系統需要 histogram 的訊號是少數慢 request 會影響使用者體驗但 average 看不出來。Checkout 平均延遲 100ms 看起來良好，但 p99 若超過 3 秒，1% 的使用者體驗極差。Histogram 讓這個長尾可見。

## 設計責任

Histogram bucket boundary 要依 [SLO](/backend/knowledge-cards/sli-slo/) 閾值跟實際延遲範圍設計。Bucket 太粗（只有 100ms / 500ms / 1s）會讓 percentile 估計跳躍式變化；太細會增加 [cardinality](/backend/knowledge-cards/metric-cardinality/)（每個 bucket 是一條 time series）。常見做法是在 SLO 閾值附近密集、在兩端稀疏。詳見 [4.2 metrics basics](/backend/04-observability/metrics-basics/)。
