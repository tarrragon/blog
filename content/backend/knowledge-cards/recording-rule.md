---
title: "Recording Rule"
date: 2026-06-22
description: "說明把 query-time 聚合計算推到寫入時的 pre-aggregation 機制"
weight: 324
tags: ["backend", "observability"]
---

Recording rule 把重複的聚合計算從查詢時推到寫入時。當 dashboard 或 alert 反覆對同一組 raw series 做 rate / sum / histogram_quantile，每次查詢都重新掃描原始資料；recording rule 把計算結果預先寫成新的 time series，查詢時直接讀取結果。

## 概念位置

Recording rule 是 [metrics](/backend/knowledge-cards/metrics/) 讀取路徑的效能工具。它在 TSDB 層（如 Prometheus、Thanos、Mimir）定期執行 query expression，把結果作為新 series 寫入儲存。概念上類似 OLAP 的 [materialized view](/backend/knowledge-cards/materialized-view/)，但作用在時間序列而非關聯式資料。

## 設計責任

設計 recording rule 時要定義計算表達式、執行間隔、命名慣例與維護責任。命名慣例通常遵循 `level:metric:operations` 格式（如 `job:http_requests_total:rate5m`），讓讀者從名稱判斷來源、粒度與計算方式。

Recording rule 產生的 series 本身也佔儲存空間與 [cardinality](/backend/knowledge-cards/metric-cardinality/)。規則數量增長時，要監控 rule evaluation duration 跟 rule group lag，避免 rule 跑不完的情況讓 dashboard 看到過期資料。

## 使用情境

需要 recording rule 的訊號是 dashboard panel 載入時間持續退化、或 alert rule 因為 query timeout 而漏發。把 SLO burn rate 計算、高流量 endpoint 的 rate 與 error ratio 預先聚合成 recording rule，是最常見的起點。

Recording rule 與 raw query 的分工：高頻讀取（dashboard 自動刷新、alert 每分鐘 evaluate）適合 recording rule；低頻即席查詢（事故時的 ad-hoc 切片）直接查 raw series，保留完整維度。

在觀測領域的應用見 [4.2 metrics 聚合查詢](/backend/04-observability/metrics-basics/) 跟 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
