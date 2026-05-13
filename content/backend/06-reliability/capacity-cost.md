---
title: "6.9 容量與成本邊界"
date: 2026-05-01
description: "把容量規劃跟成本約束變成驗證輸入"
weight: 9
tags: ["backend", "reliability"]
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

## 高峰型容量治理：Game Day + Capacity Planning

高峰型容量治理是把「可預期的非典型流量」當獨立治理面操作的能力。涵蓋 baseline 預估、邊界隔離、game day 驗證跟 resiliency matrix 對齊四個面向。日常擴容靠 autoscaling、高峰需要的是預先驗證跟邊界控制 — 峰值期間擴容延遲跟依賴抖動會疊加放大成事故。

對應 [H1 Shopify BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)：揭露四個機制對應上述四個面向 — capacity planning baseline（高峰前可承受上限是多少）、pod/isolation boundary（故障影響如何限制在局部）、game day（高峰前如何驗證假設）、resiliency matrix（服務與失效模式如何對齊）。

可重複套用的做法：

三個治理面性質不同、不是同一個時間軸的三步驟：

- **Capacity planning**（forecast + headroom 模型）：高峰前 N 週開始、整合 forecast、headroom、依賴 quota — 不只看單一 CPU 數字、要看整條依賴鏈的瓶頸層
- **Game day**（production-like 假設驗證）：高峰前 N 天執行、把 runbook、matrix、驗證腳本、放行門檻當固定資產輸出、不是「跑完就好」
- **Isolation boundary**（runtime 故障擴散控制）：高峰當下持續運作、cell 邊界跟 graceful degradation 把故障限制在最小可影響範圍、補強 autoscaling 來不及的延遲段

把每輪活動輸出的缺口回寫成固定資產（不只是「一次性專案」），下一輪準備就能從更高基準開始。

## 容量跟值班分層的協同

容量跟值班分層的綁定責任是讓「容量門檻」跟「升級路徑」在同一個 trigger 觸發：接近 headroom 限制時值班自動分層、避免事故發生才升級。這個綁定需要三件事配合：runtime 訊號（headroom 預算）、接手機制（三層值班）、模型校準（壓測驗證）。

對應 [L1 LinkedIn Capacity Headroom 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)：揭露三個機制對應上述三件事 — headroom 預算（何時進入風險區）、primary/secondary/SME 三層值班（何時由誰接手）、自動化壓測（模型是否貼近現況）。前兩個是 runtime 治理、後者是 model 校準、屬於不同邏輯位階。

容量規劃要回答「擴容門檻是多少」、值班分層要回答「接近門檻時誰接手」。兩者綁定後、高峰期值班分層自動觸發、不需等事故發生才升級。詳見 [8.12 IC handoff for long incident](/backend/08-incident-response/ic-handoff-long-incident/)。

## 快取容量的特殊性

快取容量治理的核心責任是失溫時資料層仍可承受。headroom 不是看快取 QPS、是看命中率下滑後的回源放大係數 — 快取本身可能耐 10x 流量、資料層可能撐不到 1.5x。

對應 [P1 Pinterest 快取可靠性與容量驚奇治理](/backend/06-reliability/cases/pinterest/cache-reliability-and-capacity-surprises/)：揭露三個機制 — cache headroom（命中率下滑能承受多久）、graceful degradation（快取失效時如何降級）、rewarm strategy（熱資料如何有序回填）。

快取容量規劃的核心問題是失溫時資料層能承受的回源放大係數。命中率從 95% 掉到 80% 意味資料層流量 4x、能否承受決定快取退化會不會升級為事故。預先設計 graceful degradation 路徑跟 rewarm 節奏、能避免快取失溫變成連鎖退化。詳見 [2.9 cache stampede rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。

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
