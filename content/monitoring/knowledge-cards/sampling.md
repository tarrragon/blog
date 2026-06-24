---
title: "Sampling"
date: 2026-06-24
description: "在事件產生階段按比例丟棄部分事件降低管線負載 — 分靜態取樣（config 固定比例）和動態取樣（背壓觸發自動降低）"
weight: 7
tags: ["monitoring", "sampling", "sdk", "knowledge-card"]
---

取樣（sampling）的通用概念見 [Backend 知識卡：Sampling](/backend/knowledge-cards/sampling/) — 只保留部分觀測資料以控制成本。本卡聚焦監控 SDK 中的具體實作：在事件產生階段按比例丟棄部分事件，降低後續管線（buffer → transport → collector → storage）的負載。取樣是設計內的損失 — 取樣率是明確的 config 參數，損失量可預測。可先對照 [backpressure](/monitoring/knowledge-cards/backpressure/)（觸發動態取樣的訊號來源）和 [rate limiting](/monitoring/knowledge-cards/rate-limiting/)（collector 端的 per-client 限制）。

## 兩種取樣

**靜態取樣**：SDK config 中設定固定比例（例如 metric 類 0.1 = 每 10 筆只收 1 筆），在 SDK 整個生命週期保持不變。適合已知高頻但單筆 debug 價值低的事件（render.frame_time、scroll.position）。

**動態取樣**：SDK 在收到 collector 的 HTTP 429 後自動降低取樣率，collector 恢復正常後逐步回升。動態取樣在正常情況下不生效（取樣率 = 1.0），只在 collector 過載時啟用。和靜態取樣互補 — 靜態控制基線負載，動態應對突發。

## 取樣校正

分析時用取樣率還原原始量級。取樣率 0.1 時收到 100 筆事件，推估原始量為 100 / 0.1 = 1000 筆。SDK 端的 `sdk.sampling.rate` 指標記錄當前取樣率，讓下游分析知道如何校正。取樣校正對 funnel 和 cohort 分析有效（趨勢和比例不變），對個別事件追蹤無效（被丟棄的事件無法回復）。

## 設計責任

取樣承擔的設計責任是「在可觀測性覆蓋率和系統負載之間找到平衡」。Error 類事件不做取樣（每筆都可能是需要修的 bug），metric 類事件適合高比例取樣（丟幾筆不影響趨勢），event 類和 lifecycle 類取決於分析需求。

## 完整章節

靜態取樣率的設定 → [感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/)。動態取樣在四層防線中的位置 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)。取樣造成的損失量化和控制 → [端到端資料完整性](/monitoring/04-collector/data-integrity/)。
