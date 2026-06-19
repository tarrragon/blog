---
title: "模組八：行為資料的商業利用"
date: 2026-06-19
description: "Funnel / Cohort / Attribution / A/B test / 推薦系統 / RFM — 從 debug 工具到商業資產的翻轉"
weight: 8
tags: ["monitoring", "analytics", "funnel", "ab-test", "recommendation", "marketing"]
---

回答「蒐集到的行為資料除了 debug，還能做什麼」。前提：[模組七](/monitoring/07-security-privacy/) 的去識別化是本模組的入場條件。

## 待寫章節

- [x] 行為事件設計（事件命名規範 / 屬性設計 / funnel 定義）
- [x] Funnel analysis（使用者在哪一步流失）
- [x] Cohort analysis（不同族群的留存率差異）
- [x] Attribution（使用者從哪來、哪個廣告帶來轉換）
- [x] A/B test 的統計基礎（假設檢定 / 樣本量 / 多重比較）
- [x] 推薦系統概論（collaborative filtering / content-based / 混合）
- [x] RFM 分群（Recency / Frequency / Monetary 的工程實作）
- [x] 從 collector 資料做基礎 funnel 分析（自架方案能做到哪裡）

## 跨分類引用

- ← [monitoring 模組七 資安](/monitoring/07-security-privacy/)：去識別化是入場條件
- ← [monitoring 模組一 心智模型](/monitoring/01-mental-model/)：event 類事件是行為分析的原料
- ← [ux-design 模組一 畫面狀態機](/ux-design/01-screen-state-machine/)：狀態轉換事件 → funnel 分析
- 待建連結 → `data-engineering/`（資料管線設計）
- 待建連結 → `statistics/`（A/B test 統計基礎）
- 待建連結 → `machine-learning/`（推薦系統架構）
- 待建連結 → `compliance/`（GDPR / CCPA / 個資法）
