---
title: "Histogram"
date: 2026-04-23
description: "說明 histogram 如何用分桶統計延遲、大小與分布"
weight: 98
---

Histogram 的核心概念是「把觀測值分到多個 bucket，記錄每個範圍的累積數量」。它常用來觀察 latency、request size、payload size、queue wait time 與處理耗時。

## 概念位置

Histogram 是 metrics 中描述分布的工具。平均值只能說明中心趨勢，histogram 可以支援 p95、p99、SLO 與 burn rate 判斷。

## 可觀察訊號與例子

系統需要 histogram 的訊號是少數慢 request 會影響使用者體驗。Checkout 平均延遲 100ms 可能看起來良好，但 p99 若超過 3 秒，仍代表部分使用者體驗很差。

## 設計責任

Histogram bucket 要依 SLO 與實際延遲範圍設計。Bucket 太粗會看不出差異，太細會增加時間序列成本。
