---
title: "Load Shedding"
tags: ["負載削峰", "Load Shedding"]
date: 2026-04-23
description: "說明服務過載時如何主動拒絕低優先工作以保護核心能力"
weight: 52
---

Load shedding 的核心概念是「在過載時主動丟棄或拒絕部分工作」。它用有限失敗保護核心能力，避免所有工作一起排隊到超時。

## 概念位置

Load shedding 是過載保護工具。它和 rate limit、backpressure、degradation、priority queue 與 admission control 相關；重點是先定義哪些工作可以被拒絕，哪些工作需要保留。

## 可觀察訊號與例子

系統需要 load shedding 的訊號是流量尖峰超過服務容量。活動期間可以拒絕低優先的推薦刷新、延後報表產生，保留下單、付款與資料保存。

## 設計責任

Load shedding 要定義優先級、拒絕回應、重試建議、告警與使用者體驗。觀測上要記錄 shed count、原因、受影響 endpoint 與核心路徑是否恢復。

