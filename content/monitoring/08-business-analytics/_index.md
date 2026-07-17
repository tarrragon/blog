---
title: "模組八：行為資料的商業利用"
date: 2026-06-19
description: "Funnel / Cohort / Attribution / A/B test / 推薦系統 / RFM — 從 debug 工具到商業資產的翻轉"
weight: 8
tags: ["monitoring", "analytics", "funnel", "ab-test", "recommendation", "marketing"]
---

回答「蒐集到的行為資料除了 debug，還能做什麼」。前提：[模組七](/monitoring/07-security-privacy/) 的去識別化是本模組的入場條件。

## 章節

- [行為事件設計](/monitoring/08-business-analytics/behavior-event-design/) — 事件命名規範、屬性設計、funnel 定義
- [Funnel Analysis](/monitoring/08-business-analytics/funnel-analysis/) — 使用者在哪一步流失的分析方法
- [Cohort Analysis](/monitoring/08-business-analytics/cohort-analysis/) — 不同族群的留存率差異分析
- [Attribution](/monitoring/08-business-analytics/attribution/) — 使用者從哪來、哪個廣告帶來轉換
- [A/B Test 的統計基礎](/monitoring/08-business-analytics/ab-test-statistics/) — 假設檢定、樣本量、多重比較的統計基礎
- [推薦系統概論](/monitoring/08-business-analytics/recommendation-overview/) — collaborative filtering / content-based / 混合方法概論
- [RFM 分群](/monitoring/08-business-analytics/rfm-segmentation/) — Recency / Frequency / Monetary 的工程實作
- [從 collector 資料做基礎 funnel 分析](/monitoring/08-business-analytics/self-hosted-funnel/) — 自架方案能做到哪裡的 funnel 分析

## 跨分類引用

- ← [monitoring 模組七 資安](/monitoring/07-security-privacy/)：去識別化是入場條件
- ← [monitoring 模組一 心智模型](/monitoring/01-mental-model/)：event 類事件是行為分析的原料
- ← [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)：狀態轉換事件 → funnel 分析
- 待建連結 → `data-engineering/`（資料管線設計）
- 待建連結 → `statistics/`（A/B test 統計基礎）
- 待建連結 → `machine-learning/`（推薦系統架構）
- 待建連結 → `compliance/`（GDPR / CCPA / 個資法）
