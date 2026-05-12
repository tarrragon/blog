---
title: "SLO Baseline Drift"
date: 2026-05-12
description: "SLO baseline 因業務變化 / surge / 架構改動而需要重新校準的現象"
weight: 241
---

SLO baseline drift 的核心概念是「SLO 訂了不是永遠不動 — 業務變化、用戶習慣演變、架構升級都會讓 baseline 必須重新校準」。沒有 drift 意識、SLO 可能「太鬆失去意義」或「太緊每天 alert」。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 概念位置

SLO drift 來源：structural surge（COVID 類外部衝擊讓 baseline 永久上移）、product change（新 feature 改變用戶 journey）、architectural improvement（DB 換型、cache 加強、CDN 擴點）、user behavior（mobile share 上升、跨 region 比例變化）。drift 不是 anomaly、是 *新常態*。可先對照 [SLI / SLO](/backend/knowledge-cards/sli-slo/)。

## 可觀察訊號與例子

需要重新校準 SLO 的訊號是「最近 N 個月 burn rate 持續低於 baseline」或「持續高於 baseline 但無 incident」。對應案例：[Zoom 30x COVID surge](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) — baseline 從 1000 萬 DAU 永久升到 3 億、SLO threshold 跟著重新校準。

## 設計責任

SLO 必須每季 review、不是「設定後就忘」。review 流程：拉過去 90 天 SLI 分布、看 percentile 分布是否跟 SLO 對應、看是否需要調整。drift 確認後要更新：alert threshold、autoscaler trigger、performance budget 額度、容量規劃 baseline。對應 [error budget](/backend/knowledge-cards/error-budget/) 跟 [performance budget](/backend/knowledge-cards/performance-budget/)。
