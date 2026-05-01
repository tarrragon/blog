---
title: "6.9 容量與成本邊界"
date: 2026-05-01
description: "把容量規劃跟成本約束變成驗證輸入"
weight: 9
---

## 大綱

- 容量規劃的核心：peak demand × headroom × growth curve
- headroom 訂定：成本 vs 突發承載 tradeoff
- capacity test 跟 [6.2 load test](/backend/06-reliability/load-testing/) 的差異：load 看 throughput、capacity 看 saturation 與 cost curve
- 成本作為驗證輸入：autoscaling 上限、預算告警、queue lag 跟成本的關係
- 跨層容量：DB connection、queue、cache、CDN、第三方 API rate limit
- 跟 [6.6 SLO](/backend/06-reliability/slo-error-budget/) 的耦合：SLO 達成的容量代價
- 反模式：容量規劃只看 CPU、autoscaling 無上限、成本失控用降級掩蓋

## 判讀訊號

- autoscaling max 設無限大、或長期未觸碰
- 容量規劃只看 CPU、忽略 connection pool / queue / 第三方 quota
- peak 流量 forecast 是直線外推、未考慮 promo / seasonal / 行銷事件
- 成本告警觸發後才回頭討論容量
- 降級邏輯被當成常態容量緩衝、而非例外保護

## 交接路由

- 04 觀測：saturation metric、cost dashboard
- 05 部署：HPA / autoscaling policy
- 06.6 SLO：容量不足導致 SLO 風險
- 04.15 cost attribution：observability 成本作為總體成本一部分
