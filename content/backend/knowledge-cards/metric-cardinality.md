---
title: "Metric Cardinality"
date: 2026-04-23
description: "說明 metric label 組合數量如何影響觀測成本與查詢穩定性"
weight: 37
---

Metric cardinality 的核心概念是「指標 label 組合會產生多少條時間序列」。Label 越多、值越分散，時間序列越多，儲存、查詢與告警成本越高。 可先對照 [Metrics](/backend/knowledge-cards/metrics/)。在讀取或寫入之前丟掉標籤與指標的規則見 [Relabeling](/backend/knowledge-cards/relabeling/)。

## 跟其他概念的關係

Cardinality 是 metrics 設計的成本邊界。`status`、`method`、`endpoint` 常可接受；`user_id`、`order_id`、`request_id` 通常會讓時間序列爆炸，應放進 log 或 trace。 可先對照 [Metrics](/backend/knowledge-cards/metrics/)。

## 可觀察訊號與例子

系統需要檢查 cardinality 的訊號是 metrics 儲存成本上升、查詢變慢、Prometheus 或後端儲存壓力升高。把 tenant_id 放進每個高流量指標前，要先評估 tenant 數量與查詢目的。

## 判斷條件與後果

一個 label 是否進指標，取決於這個指標的查詢是否依它分組。每個 label 的值數相乘就是時間序列數，`user_id`、`request_id` 這類每個請求都不同的值放進 label 時，時間序列數隨使用者或請求數成長，儲存、查詢與告警成本跟著上升，而指標的聚合查詢用不到單一使用者這一層。高基數的資訊另有更便宜的位置：要追到單一使用者或請求時，抽樣 log 或 trace attribute 查得到；只要知道最大的幾個值時，用 top-N 指標；要完整分布時，用離線分析。`tenant_id` 這類值數有限而依租戶數成長的 label，加進高流量指標之前，先拿租戶數乘上其他 label 的組合數估一次時間序列數。
