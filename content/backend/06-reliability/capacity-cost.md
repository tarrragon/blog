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

## 概念定位

Capacity 與成本邊界是把容量規劃跟成本約束一起看，責任是讓系統能承載預期負載，同時不把成本曲線推到不可接受區域。

這一頁處理的是規模化之後的 trade-off。容量不是越高越好，真正的目標是找到能維持 SLO、又不浪費資源的區間。

## 核心判讀

判讀 capacity 時，先看 saturation 點，再看成本曲線是不是隨之失控。

重點訊號包括：

- autoscaling 是否有清楚上限與成本門檻
- 依賴層是否先於應用層成為瓶頸
- peak forecast 是否涵蓋活動、季節性與推廣事件
- 降級是否被當成例外策略，而不是常態容量替代

## 案例對照

- [Shopify](/backend/06-reliability/cases/shopify/_index.md)：高峰型流量把容量與成本的邊界推得很清楚。
- [LinkedIn](/backend/06-reliability/cases/linkedin/_index.md)：互動型服務常先在某個依賴層出現瓶頸。
- [Amazon](/backend/06-reliability/cases/amazon/_index.md)：大規模系統常把成本與可靠性一起做優化。

## 下一步路由

- 06.2 load testing：capacity 輸入來自 workload model
- 06.9 reliability metrics：容量與成本要有量測口徑
- 06.13 perf regression gate：效能退化通常伴隨成本上升

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
