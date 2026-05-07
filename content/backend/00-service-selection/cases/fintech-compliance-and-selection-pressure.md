---
title: "FinTech：合規壓力下的後端選型"
date: 2026-05-07
description: "在審計、留存與交易正確性要求下，如何平衡成本、風險與交付速度。"
weight: 1
---

這個案例的核心責任是把合規壓力轉成選型條件。FinTech 場景下，資料保留、審計追溯與交易一致性通常比純效能優先。

## 判讀訊號

| 訊號                       | 判讀重點                 | 對應章節                                                                    |
| -------------------------- | ------------------------ | --------------------------------------------------------------------------- |
| audit evidence gap         | 稽核證據是否連續         | [0.8](/backend/00-service-selection/security-data-protection-requirements/) |
| duplicate transaction risk | 重試是否可能造成雙重結果 | [0.2](/backend/00-service-selection/state-storage-selection/)               |
| release freeze frequency   | 發布是否常因風險臨時凍結 | [0.6](/backend/00-service-selection/cost-risk-tradeoffs/)                   |

## 風險與邊界

把合規當成部署後補強會抬高長期成本。較穩定的做法是在選型時就定義證據鏈、資料邊界與回復順序，避免後續跨模組反覆返工。

## 下一步路由

先補 [4.12](/backend/04-observability/audit-log-governance/) 的審計訊號，再用 [6.8](/backend/06-reliability/release-gate/) 定義合規變更門檻。
