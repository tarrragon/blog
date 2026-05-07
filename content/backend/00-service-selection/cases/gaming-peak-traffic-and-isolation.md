---
title: "Gaming：高峰流量與隔離邊界選型"
date: 2026-05-07
description: "大型活動流量下，如何在低延遲與穩定性之間做可持續取捨。"
weight: 2
---

這個案例的核心責任是把活動高峰轉成預先可驗證的容量與隔離決策。Gaming 場景的失效通常來自瞬間峰值與連線風暴疊加。

## 判讀訊號

| 訊號                      | 判讀重點             | 對應章節                                                           |
| ------------------------- | -------------------- | ------------------------------------------------------------------ |
| peak burst ratio          | 尖峰是否超過模型緩衝 | [0.5](/backend/00-service-selection/traffic-data-scale/)           |
| matchmaking queue lag     | 非同步鏈路是否壅塞   | [0.3](/backend/00-service-selection/async-delivery-selection/)     |
| reconnect storm indicator | 回復是否放大負載     | [0.7](/backend/00-service-selection/failure-observability-design/) |

## 風險與邊界

只追求低延遲而忽略隔離邊界，會在高峰時把單一熱點擴散成全域事故。選型時需要同時定義分流邏輯與分批恢復策略。

## 下一步路由

把容量假設回寫 [6.9](/backend/06-reliability/capacity-cost/)，並在 [8.14](/backend/08-incident-response/multi-incident-coordination/) 補多事故協調規則。
