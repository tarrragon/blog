---
title: "Cohort Analysis"
date: 2026-06-19
description: "按共同特徵分群、比較不同群體的留存率和行為差異 — 從「平均值」到「誰在用、誰離開了」"
weight: 3
tags: ["monitoring", "analytics", "cohort", "retention", "segmentation"]
---

[Cohort analysis](/monitoring/knowledge-cards/cohort-analysis/) 把使用者按共同特徵分群（cohort），比較不同群體在同一個指標上的表現差異。整體平均留存率 40% 可能隱藏了「1 月註冊的使用者留存 60%、3 月註冊的留存 20%」的差異。Cohort analysis 揭露平均值遮蔽的趨勢。

## Cohort 的定義方式

### 時間 cohort（最常用）

按使用者完成某個動作的時間分群。「1 月份註冊的使用者」「第 12 週 onboarding 完成的使用者」。

時間 cohort 回答的問題：產品的留存率是否隨時間改善？新版本上線後註冊的使用者留存是否比舊版本高？

### 行為 cohort

按使用者的行為特徵分群。「首次使用就完成購買的使用者」「使用過搜尋功能的使用者」「連續 3 天登入的使用者」。

行為 cohort 回答的問題：哪些行為和留存相關？做了 X 的使用者留存率是否比沒做 X 的高？

### 屬性 cohort

按使用者的固有屬性分群。「iOS 使用者」「企業方案使用者」「來自特定廣告渠道的使用者」。

屬性 cohort 回答的問題：不同平台/方案/來源的使用者行為是否不同？

## 留存率矩陣

留存率矩陣是 cohort analysis 最常見的呈現方式。每行代表一個 cohort（例如某月註冊的使用者），每列代表註冊後的第 N 天/週/月，格中的值是該 cohort 在第 N 期仍活躍的比例。

| Cohort | 第 0 週 | 第 1 週 | 第 2 週 | 第 4 週 | 第 8 週 |
| ------ | ------- | ------- | ------- | ------- | ------- |
| 1 月   | 100%    | 45%     | 32%     | 22%     | 18%     |
| 2 月   | 100%    | 48%     | 35%     | 25%     | 20%     |
| 3 月   | 100%    | 52%     | 40%     | 30%     | —       |

從這張矩陣可以看到：留存率逐月改善（1 月 → 3 月的第 1 週留存從 45% 升到 52%）。如果 2 月有產品改版，這個改善可能和改版相關。

## Cohort analysis 的判讀

### 自然衰減 vs 產品問題

所有產品都有自然衰減 — 使用者隨時間減少是正常的。Cohort analysis 的價值在於區分「正常衰減」和「異常衰減」。

如果所有 cohort 的衰減曲線形狀相似，衰減是產品層面的結構性問題（例如缺少持續使用的理由）。如果某個 cohort 的衰減明顯比其他 cohort 快，需要調查該 cohort 的特殊情況（當時的產品版本、市場環境、使用者來源）。

### 穩態留存

留存率通常在某個時間點後趨於穩定 — 留下來的使用者不再大量流失。穩態留存的百分比和到達穩態的時間是產品健康度的核心指標。

穩態留存高但到達時間長 = 產品有價值但 onboarding 需要改善。穩態留存低 = 產品的持續使用價值不足。

## 和 funnel 的關係

Funnel analysis 回答「使用者在哪一步流失」（單次流程），cohort analysis 回答「使用者是否持續回來」（長期行為）。兩者互補：funnel 改善單次流程的轉換率，cohort 追蹤改善是否帶來長期留存的變化。

## 下一步路由

- 使用者從哪來 → [Attribution](/monitoring/08-business-analytics/attribution/)
- 單次流程的流失分析 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 使用者分群的工程實作 → [RFM 分群](/monitoring/08-business-analytics/rfm-segmentation/)
