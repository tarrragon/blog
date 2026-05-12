---
title: "RED Method"
date: 2026-05-12
description: "Tom Wilkie 提出的請求層 Rate / Errors / Duration 三維度量測法"
weight: 224
---

RED method 的核心概念是「對每個 service / endpoint 量測 Rate、Errors、Duration 三個維度」。Rate 是 RPS、Errors 是錯誤率、Duration 是 latency 分布（p50 / p95 / p99 / p999）。可先對照 [USE Method](/backend/knowledge-cards/use-method/)。

## 概念位置

RED 是 request-oriented 觀察法、跟 resource-oriented 的 [USE method](/backend/knowledge-cards/use-method/) 互補。USE 看「資源層」、RED 看「業務層」。Duration 變差通常先於 Errors 出現 — 是 capacity 接近 saturation 的早期警訊。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 可觀察訊號與例子

RED 三維度的典型訊號：Rate 上升、Errors 維持低、但 Duration p99 飆升 → 接近 saturation；Rate 維持、Errors 飆升 → downstream 出問題（不是容量議題）。對應案例：[GR8 Tech 25ms p95](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 把 p95 變業務 KPI 而非技術指標。

## 設計責任

每個 service / endpoint 必須有獨立 RED dashboard、不能只看全站 average。Duration 必須記錄分布（histogram）而非單一 percentile、否則無法做 long-tail 分析。RED metrics 通常驅動 SLO；duration 跟 [latency budget](/backend/knowledge-cards/latency-budget/) 對接。
