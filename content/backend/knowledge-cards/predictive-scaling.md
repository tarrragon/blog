---
title: "Predictive Scaling"
date: 2026-05-12
description: "說明用歷史模式或 ML 模型預測流量、提前擴容的 autoscaler 模式"
weight: 231
---

Predictive scaling 的核心概念是「不等流量上來、提前根據預測擴容」。跟 reactive scaling（觀察到指標飆才擴）相反、解決 reactive 在快速 burst 場景下「來不及」的問題。可先對照 [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)。

## 跟其他概念的關係

Predictive scaling 用兩類預測：歷史模式（過去幾週同時段、同 day-of-week 的流量）跟 ML 模型（多 feature 模型、結合業務 schedule、新用戶獲取）。EC2 Auto Scaling、GCP Compute Engine Predictive Autoscaler、Azure VM Scale Sets 都支援。跟 scheduled scaling 互補 — scheduled 處理「已知時間點」、predictive 處理「常態 daily / weekly pattern」。可先對照 [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/)。

## 可觀察訊號與例子

需要 predictive 的訊號是「reactive autoscaler 反應太慢、流量上升期 latency 飆」。對應案例：[GR8 Tech AI 預測](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — 賽事高潮預測模型、把擴容窗口縮到反應時間之內；[Prime Day pre-scaling](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) — 結合 predictive + scheduled 兩種。

## 判斷條件與後果

Predictive scaling 的效果取決於預測準確度。預測過高時，提前擴出的容量沒有用到，多付了費用；預測過低時，擴出的容量不足以處理上升的流量，latency 照樣上升，回到導入它之前 reactive 來不及的情形。準確度沒有被監控時，這兩種失準要等帳單或延遲變差才被發現，所以預測誤差超過門檻時退回 reactive scaling。三種擴容方式各自對應一類流量：scheduled 對應已知時間點的大事件，predictive 對應日常的 daily / weekly pattern，reactive 對應預測不到的 burst；只用其中一種時，另外兩類流量沒有對應的擴容方式，所以三者組合使用。
