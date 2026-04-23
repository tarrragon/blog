---
title: "Percentile"
date: 2026-04-23
description: "說明 p95 與 p99 如何描述長尾延遲與使用者體驗"
weight: 100
---

Percentile 的核心概念是「某比例的觀測值低於某個門檻」。p95 latency 表示 95% request 的延遲不高於該值；p99 則觀察更長尾的慢請求。

## 概念位置

Percentile 用來描述平均值看不到的使用者體驗。高流量服務中，少數慢 request 可能代表大量使用者受影響，因此 p95 / p99 常比平均值更有操作意義。

## 可觀察訊號與例子

系統需要 percentile 的訊號是平均 latency 穩定，但使用者仍回報卡頓。搜尋 API 平均 80ms，p99 2 秒，表示少數 request 走到慢查詢或下游 timeout。

## 設計責任

Percentile 要搭配 histogram、SLO 與流量基準解讀。低流量服務的高 percentile 容易受少量樣本影響，告警要避免過度敏感。
