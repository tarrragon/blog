---
title: "Cohort Analysis"
date: 2026-06-19
description: "說明把使用者按共同特徵分群、比較不同群組行為差異的分析方法"
weight: 3
tags: ["monitoring", "analytics", "cohort", "knowledge-card"]
---

Cohort analysis 的核心概念是「把使用者按共同特徵分群，比較不同群組的行為差異」。Cohort 通常按時間（註冊月份）、行為（首次使用的功能）、或屬性（付費方案）分群。可先對照 [funnel analysis](/monitoring/knowledge-cards/funnel-analysis/)（追蹤單一流程的每步轉換）和 [RFM](/monitoring/knowledge-cards/rfm/)（按行為指標分群）。

## 概念位置

Cohort analysis 位在 funnel analysis 之後、策略制定之前。Funnel analysis 回答「使用者在哪一步流失」，cohort analysis 回答「哪種使用者流失率高」。兩者搭配使用：funnel 找到流失步驟，cohort 找到流失群組，策略針對特定群組的流失步驟設計。

## 可觀察訊號與例子

產品需要 cohort analysis 的訊號是「整體留存率或轉換率的平均值遮蔽了群組差異」。整體 30 天留存率 40%，但按註冊來源拆分後發現自然搜尋來的使用者留存 60%、廣告來的使用者留存 20% — 平均值沒有揭露這個差異。

## 設計責任

Cohort analysis 要定義分群維度（按什麼特徵分）、觀察指標（留存率、活躍度、付費率）、觀察時間窗口（7 天、30 天、90 天）、以及最小群組大小（群組太小時統計不顯著）。分群維度的選擇決定了分析能揭露什麼 — 按「註冊來源」分群能看到獲客通路的品質差異，按「使用的功能」分群能看到功能黏著度差異。
