---
title: "LinkedIn：Automated Load Testing 與 Capacity Forecasting"
date: 2026-06-23
description: "持續壓測驅動容量預測：用自動化回饋取代一次性壓測的容量規劃。"
weight: 32
tags: ["backend", "reliability", "case-study"]
---

Automated load testing 的核心責任是把壓測從一次性活動變成持續回饋的工程流程。Capacity forecasting 的責任是用歷史流量趨勢加上壓測結果，預測什麼時候需要擴容、什麼時候可以縮減。

## 問題場景

大型社交平台的流量增長是漸進的，但容量不足是突然的。超過 saturation point 後 latency 會非線性惡化，從可接受的排隊延遲快速轉成級聯超時。若靠一次性壓測做容量規劃，規劃結論會隨時間漂移：流量結構改變、功能上線帶進新 workload、依賴服務的回應時間波動，都會讓上一次壓測的 saturation point 不再準確。

LinkedIn 的做法是把壓測自動化並跑在定期排程中，讓容量預測的輸入持續更新。壓測結果直接餵給 forecasting 模型，forecasting 輸出接到 headroom alert，headroom alert 觸發擴容 review。這條鏈路讓容量決策從「每季做一次人工判斷」變成「每週自動更新、異常時才需要人介入」。

## 決策機制

| 機制                | 核心問題                             | 交付結果           |
| ------------------- | ------------------------------------ | ------------------ |
| Automated load test | saturation point 是否仍準確          | 更新後的容量基準   |
| Traffic forecasting | 未來 N 天的 peak load 是否會逼近上限 | 擴容時間窗預測     |
| Headroom alert      | forecast / ceiling 比值是否超過門檻  | 自動擴容 review    |
| Capacity budget     | 每個服務的容量開銷是否在預算內       | 超支 justification |

Automated load test 用 production traffic replay 而非固定 scenario，讓壓測的 workload model 跟真實流量保持同步。Traffic forecasting 結合歷史流量趨勢與產品 launch 日曆，把可預期的流量事件（功能上線、促銷、季節性增長）納入預測。Headroom alert 在 forecast peak / capacity ceiling 比值超過 70-80% 時觸發，讓團隊在容量耗盡前有足夠反應窗口。

## 可觀測訊號

| 訊號                   | 判讀重點                           | 對應章節                                                     |
| ---------------------- | ---------------------------------- | ------------------------------------------------------------ |
| saturation point drift | 壓測結果是否隨時間漂移             | [6.2](/backend/06-reliability/load-testing/)                 |
| headroom ratio         | peak load 與 capacity ceiling 比值 | [6.9](/backend/06-reliability/capacity-cost/)                |
| forecast accuracy      | 預測與實際 peak 的偏差             | [6.13](/backend/06-reliability/performance-regression-gate/) |
| capacity spend trend   | 容量成本是否超出預算               | [6.9](/backend/06-reliability/capacity-cost/)                |

## 常見陷阱

自動化壓測最常見的失真來源是 workload model 僵化。若自動化跑的是建立時的固定 scenario 而非持續更新的 traffic replay，時間一長模型就跟 production 脫鉤。脫鉤的訊號是壓測結果與 production 同時段的 latency distribution 開始偏離 — p50 / p95 / p99 的比率差異超過 20% 時，模型已需要校準。

另一個陷阱是把 forecast 當成精確預測。Forecasting 的價值在於提早觸發 review，讓團隊有時間做擴容決策。若團隊把 forecast 當成精確數字做自動擴容，預測偏差會直接變成過度擴容或擴容不足。forecast 輸出應該驅動人工 review，而非直接觸發資源變更。

## 下一步路由

先把壓測結果接到 [6.2 load testing](/backend/06-reliability/load-testing/) 的 workload model 校準流程，再用 headroom ratio 餵給 [6.9 容量與成本邊界](/backend/06-reliability/capacity-cost/) 做容量預算。forecast 準確度的追蹤連到 [6.13 performance regression gate](/backend/06-reliability/performance-regression-gate/) 的 baseline 校準。

## 引用源

- [Eliminating toil with fully automated load testing](https://engineering.linkedin.com/content/engineering/en-us/blog/2019/eliminating-toil-with-fully-automated-load-testing)
- （背景脈絡）[Taming Database Replication Latency by Capacity Planning](https://engineering.linkedin.com/performance/taming-database-replication-latency-capacity-planning)
