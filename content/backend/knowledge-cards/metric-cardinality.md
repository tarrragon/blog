---
title: "Metric Cardinality"
date: 2026-04-23
description: "說明 metric label 組合數量如何影響觀測成本與查詢穩定性"
weight: 36
---

Metric cardinality 的核心概念是「指標 label 組合會產生多少條時間序列」。Label 越多、值越分散，時間序列越多，儲存、查詢與告警成本越高。

## 概念位置

Cardinality 是 metrics 設計的成本邊界。`status`、`method`、`endpoint` 常可接受；`user_id`、`order_id`、`request_id` 通常會讓時間序列爆炸，應放進 log 或 trace。

## 可觀察訊號與例子

系統需要檢查 cardinality 的訊號是 metrics 儲存成本上升、查詢變慢、Prometheus 或後端儲存壓力升高。把 tenant_id 放進每個高流量指標前，要先評估 tenant 數量與查詢目的。

## 設計責任

Metrics 設計要先定義問題，再選 label。高基數資訊可以改用抽樣 log、trace attribute、top-N 指標或離線分析。
