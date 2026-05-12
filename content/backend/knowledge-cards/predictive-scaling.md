---
title: "Predictive Scaling"
date: 2026-05-12
description: "說明用歷史模式或 ML 模型預測流量、提前擴容的 autoscaler 模式"
weight: 230
---

Predictive scaling 的核心概念是「不等流量上來、提前根據預測擴容」。跟 reactive scaling（觀察到指標飆才擴）相反、解決 reactive 在快速 burst 場景下「來不及」的問題。可先對照 [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)。

## 概念位置

Predictive scaling 用兩類預測：歷史模式（過去幾週同時段、同 day-of-week 的流量）跟 ML 模型（多 feature 模型、結合業務 schedule、新用戶獲取）。EC2 Auto Scaling、GCP Compute Engine Predictive Autoscaler、Azure VM Scale Sets 都支援。跟 scheduled scaling 互補 — scheduled 處理「已知時間點」、predictive 處理「常態 daily / weekly pattern」。可先對照 [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)。

## 可觀察訊號與例子

需要 predictive 的訊號是「reactive autoscaler 反應太慢、流量上升期 latency 飆」。對應案例：[GR8 Tech AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 賽事高潮預測模型、把擴容窗口縮到反應時間之內；[Prime Day pre-scaling](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — 結合 predictive + scheduled 兩種。

## 設計責任

Predictive scaling 預測錯了會浪費錢（預測過高、提前擴沒用到）或失效（預測過低、流量還是衝高）。要 monitor *預測準確度*、超過誤差門檻時 fallback 到 reactive。三層組合最穩：scheduled（已知大事件）+ predictive（daily pattern）+ reactive（unexpected burst）。
