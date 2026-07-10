---
title: "4.C16 Cardinality 事故爆炸：被觀測系統的異常把觀測後端打爆"
date: 2026-07-04
description: "事故時 error / user / request-id 維度從低基數 spike 成高基數、每個 unique 值生一條新 series、TSDB 在你最需要查詢時 crash"
weight: 16
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是提供共命運最具體的技術路徑：被觀測系統的異常行為透過 label 把觀測後端打爆。

## 觀察

Prometheus 官方 naming 實踐文件：「every unique combination of key-value label pairs represents a new time series, which can dramatically increase the amount of data stored」；「Do not use labels to store dimensions with high cardinality (many different label values), such as user IDs, email addresses, or other unbounded sets of values」。Grafana Labs 官方部落格定義 cardinality spike：「a metric with medium or lower cardinality suddenly transforms into a metric with high cardinality」、後果「you begin to use too many resources, which can then lead to memory errors and system crashes」。

## 判讀

事故當下 error / user / request-id 這類維度突然從低基數變高基數（spike）、每個 unique 值生一條新 series、觀測後端資源耗盡並 crash —— 正好在你最需要下 query 排障的時刻。拖垮觀測後端的是被觀測系統自身的異常行為——它透過 label 把爆炸的維度值灌進 metric，外部依賴全程健康。設計含義：高基數維度（尤其事故時會爆的 error 細節）要進 label 白名單管理（治理在 [4.7](/backend/04-observability/cardinality-cost-governance/)）、或改走 exemplar / 高基數專用後端、而非無界塞進 metric label。

## 對應大綱

觀測共命運章「cardinality / 查詢崩潰」段。

## 引用源

- [Metric and label naming（Prometheus 官方 docs）](https://prometheus.io/docs/practices/naming/) — 一手。已 WebFetch 驗證。
- [What are cardinality spikes and why do they matter（Grafana Labs）](https://grafana.com/blog/2022/02/15/what-are-cardinality-spikes-and-why-do-they-matter/) — vendor 一手。已 WebFetch 驗證。

## 二手來源與狀態標注

Grafana 文未細分 ingestion vs query 的退化差異（自陳不提具體數字）——「query 比 ingestion 先垮」若正文要用需另找 TSDB 內部文件或標推導。
