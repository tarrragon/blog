---
title: "Backpressure"
date: 2026-06-24
description: "下游處理能力不足時向上游回傳「慢下來」訊號的流量控制機制 — 監控系統中 collector 用 HTTP 429 向 SDK 傳遞背壓"
weight: 6
tags: ["monitoring", "backpressure", "flow-control", "knowledge-card"]
---

背壓（backpressure）的通用概念見 [Backend 知識卡：Backpressure](/backend/knowledge-cards/backpressure/) — 下游處理能力不足時向上游回傳「慢下來」訊號。本卡聚焦監控系統中的具體實作：collector 是下游、SDK 是上游，collector 的寫入 channel 滿時回 HTTP 429（Too Many Requests），SDK 收到 429 後自動降低[取樣](/monitoring/knowledge-cards/sampling/)率。可先對照 [rate limiting](/monitoring/knowledge-cards/rate-limiting/)（per-client 的配額限制）。

## 概念位置

背壓位在 SDK 和 collector 之間的 HTTP 通訊層。觸發順序：collector 的寫入 channel 容量耗盡 → HTTP handler 無法送入事件 → 回 429 → SDK 收到 429 → SDK 降低取樣率（從 1.0 → 0.5 → 0.1）。背壓是全域的容量訊號 — 所有 SDK 同時收到，所有 SDK 同時降速。

## 可觀察訊號與例子

需要關注背壓的訊號是 collector 端的 `collector.events.backpressure` 計數器持續上升、或 SDK 端的 `sdk.sampling.rate` 低於 1.0。典型場景：行銷活動導致同時在線使用者暴增 → 所有 SDK 同時 flush → collector channel 瞬間填滿 → 全域 429 → 所有 SDK 動態降採樣。

## 和 DevOps 背壓的關係

[DevOps 流量管控](/devops/03-traffic-management/)討論通用的背壓概念（TCP flow control、message queue consumer lag、circuit breaker）。本系列聚焦 SDK ↔ collector 之間的具體實作 — HTTP 429 是訊號、動態取樣是回應、Go channel 容量是觸發條件。通用概念在 DevOps 模組，監控場景的具體機制在本系列。

## 完整章節

背壓在四層防線中的位置（第二層 collector 單機防護）→ [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)。背壓造成的資料損失和控制策略 → [端到端資料完整性](/monitoring/04-collector/data-integrity/)。
