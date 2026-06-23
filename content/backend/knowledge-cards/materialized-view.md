---
title: "Materialized View"
date: 2026-06-22
description: "說明預先計算並儲存查詢結果以加速讀取的資料結構"
weight: 327
tags: ["backend", "observability", "database"]
---

Materialized view 把查詢結果預先計算並持久儲存，是 [read model](/backend/knowledge-cards/read-model/) 的一種實作方式。它跟一般 view 的差別在於 materialized view 有實體儲存，查詢時讀取的是快照而非即時計算。

## 概念位置

Materialized view 是 [read model](/backend/knowledge-cards/read-model/) 的一種實作方式。在關聯式資料庫中它是 SQL-level 的物化查詢；在觀測領域，[recording rule](/backend/knowledge-cards/recording-rule/) 扮演類似角色 — 把聚合計算的結果寫成新的 time series。兩者的共同設計問題是更新頻率、一致性延遲與維護成本。

## 設計責任

設計 materialized view 時要定義刷新策略（定時 / 觸發 / 手動）、資料新鮮度容忍上限、儲存成本與失效重建流程。刷新頻率決定讀取的 freshness — 每分鐘刷新的 materialized view 最多落後一分鐘，對 dashboard 場景通常足夠，對即席事故診斷可能不夠。

## 使用情境

需要 materialized view 的訊號是同一個複雜查詢被多個消費者反覆執行（dashboard panel、定期報表、alert rule），而且每次查詢的計算成本高到影響原始資料源的效能。在觀測場景中，SLO burn rate、跨服務 error ratio、多維度 latency percentile 是常見的 materialization 候選。

在資料庫的應用見 [1.8 State Ownership](/backend/01-database/state-ownership-query-boundary/)。在觀測領域的應用見 [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)。
