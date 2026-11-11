---
title: "Histogram"
date: 2026-06-22
description: "說明 histogram 如何用分桶統計延遲、大小與分布"
weight: 99
tags: ["backend", "observability"]
---

Histogram 的核心概念是「把觀測值分到多個 bucket，記錄每個範圍的累積數量」。它是 [metrics](/backend/knowledge-cards/metrics/) 中描述分布的工具，常用來觀察 latency、request size、payload size、queue wait time 與處理耗時，支援 [percentile](/backend/knowledge-cards/percentile/) 計算。

## 跟其他概念的關係

Histogram 是 [metrics](/backend/knowledge-cards/metrics/) 中描述分布的工具，跟 counter（計數）跟 gauge（瞬間值）互補。Average 只能說明中心趨勢；histogram 可以支援 [percentile](/backend/knowledge-cards/percentile/)（p95 / p99）、[SLI](/backend/knowledge-cards/sli-slo/) 計算跟 [burn rate](/backend/knowledge-cards/burn-rate/) 判斷。

Prometheus 的 histogram 用累積 bucket（`le` label）實作 — 每個 bucket 記錄「值 <= le 的觀測次數」。PromQL 的 `histogram_quantile()` 從 bucket 資料估算 percentile。

## 使用情境

系統需要 histogram 的訊號是少數慢 request 會影響使用者體驗但 average 看不出來。Checkout 平均延遲 100ms 看起來良好，但 p99 若超過 3 秒，1% 的使用者體驗極差。Histogram 讓這個長尾可見。

## 判斷條件與後果

Histogram 的 bucket boundary 同時決定 percentile 估計的精度與 time series 的數量。bucket 太粗時（只有 100ms / 500ms / 1s），percentile 只能在同一個 bucket 的範圍內估算，估計值在 bucket 邊界之間跳躍式變化，SLO 閾值附近的變化看不出來；bucket 太細時，每個 bucket 是一條 time series，[cardinality](/backend/knowledge-cards/metric-cardinality/) 隨 bucket 數增加。兩種代價在 [SLO](/backend/knowledge-cards/sli-slo/) 閾值附近取捨最明顯，所以 boundary 依閾值與實際延遲範圍配置：閾值附近密集，判斷是否違反 SLO 的精度最高，兩端稀疏，time series 的數量受控。詳見 [4.2 metrics basics](/backend/04-observability/metrics-basics/)。
