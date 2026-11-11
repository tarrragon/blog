---
title: "Cohort Analysis"
date: 2026-06-19
description: "說明把使用者按共同特徵分群、比較不同群組行為差異的分析方法"
weight: 3
tags: ["monitoring", "analytics", "cohort", "knowledge-card"]
aliases: ["/monitoring/knowledge-cards/cohort-analysis/"]
---

Cohort analysis 的核心概念是「把使用者按共同特徵分群，比較不同群組的行為差異」。Cohort 通常按時間（註冊月份）、行為（首次使用的功能）、或屬性（付費方案）分群。可先對照 [funnel analysis](/devops/monitoring/knowledge-cards/funnel-analysis/)（追蹤單一流程的每步轉換）和 [RFM](/devops/monitoring/knowledge-cards/rfm/)（按行為指標分群）。

## 跟其他概念的關係

Cohort analysis 位在 [funnel analysis](/devops/monitoring/knowledge-cards/funnel-analysis/) 之後、策略制定之前。Funnel analysis 回答「使用者在哪一步流失」，cohort analysis 回答「哪種使用者流失率高」。兩者搭配使用：funnel 找到流失步驟，cohort 找到流失群組，策略針對特定群組的流失步驟設計。

## 可觀察訊號與例子

產品需要 cohort analysis 的訊號是「整體留存率或轉換率的平均值遮蔽了群組差異」。整體 30 天留存率 40%，但按註冊來源拆分後發現自然搜尋來的使用者留存 60%、廣告來的使用者留存 20% — 平均值沒有揭露這個差異。

## 判斷條件與後果

分群維度決定一次 cohort analysis 看得到哪一種差異：按註冊來源分群時，看到的是獲客通路帶來的使用者品質差異；按首次使用的功能分群時，看到的是功能黏著度的差異；選了跟流失原因無關的維度時，各群的曲線幾乎重疊，平均值遮蔽的那個差異仍然藏著。觀察指標（留存率、活躍度、付費率）在看資料之前沒有定下時，同一份資料可以挑出對某個結論有利的那一個指標，群組之間的比較失去共同的依據。觀察時間窗口（7 天、30 天、90 天）比使用者實際的使用週期短時，使用週期長的那一群在窗口內看起來已經流失。群組人數少時，兩群留存率的差距可能只是抽樣波動、統計上不顯著，所以人數低於最小群組大小的群不拿來下結論。
