---
title: "9.C7 Lyft：100+ 微服務在 8 倍峰值下的 Auto Scaling"
date: 2026-05-12
description: "Lyft 用 AWS Auto Scaling 跨 100+ 個微服務承載 8 倍峰值流量、跨 200+ 城市"
weight: 7
tags: ["backend", "performance", "capacity", "case-study", "compute", "aws", "event-peak"]
---

這個案例的核心責任是說明「微服務架構在事件型峰值下的容量治理」。共乘服務的負載形狀獨特 — 平日早晚通勤雙峰、週末晚間爆量、特殊事件（演唱會、球賽結束、機場）瞬間爆量、每個城市跟每個時段都不同。100+ 個微服務各自有不同的峰值時段、需要獨立擴容策略。

## 觀察

Lyft 在 AWS 的關鍵數字（引自 [Lyft case study](https://aws.amazon.com/solutions/case-studies/lyft/)）：

| 指標     | 數字         |
| -------- | ------------ |
| 峰值倍數 | 8x 平日基線  |
| 微服務數 | 100+ 個      |
| 月均搭乘 | 1400 萬 / 月 |
| 服務城市 | 200+         |

服務組合：Amazon DynamoDB（搭乘追蹤、GPS 座標）、Amazon Redshift（客戶洞察）、Amazon Kinesis（即時事件串流）、AWS Auto Scaling、Amazon EC2 Container Registry。

## 判讀

Lyft 的工程做法揭露三個微服務容量治理重點。

1. **微服務不是「全部 8x」、是「特定服務 8x」**：8x 是 *某些核心服務* 在週末爆量時刻的擴容比、不是 100 個服務全部 8x。對應 [9.5 瓶頸定位流程](/backend/09-performance-capacity/) 必須先做「哪個服務是熱點」的層次定位。
2. **微服務粒度 = 擴容粒度**：把 ride matching、payment、driver tracking、notification 切成獨立服務、每個服務的 autoscaling policy 可以獨立設計。對應 [03 訊息佇列模組](/backend/03-message-queue/) 跟 [05 部署平台模組](/backend/05-deployment-platform/) 的服務邊界。
3. **GPS 座標寫入 DynamoDB 是高頻 sustained workload**：每個 driver 每秒寫 1-2 次位置、200+ 城市 × 每個城市數萬司機 = 巨量持續寫入、跟峰值無關。對應 [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) 的 KV 高吞吐設計同類。

需要警惕：「8x 峰值」是 *峰值倍數*、不是 *尖峰持續時間*。週末晚間的尖峰可能持續 3-4 小時、機場特殊事件可能持續 30 分鐘、演唱會結束可能只有 10 分鐘瞬間。容量策略要按持續時間區分。

## 策略

可重用的工程做法：

1. **微服務粒度切到「同性質擴容單位」**：同步 vs async、stateful vs stateless、CPU-bound vs I/O-bound 不該混在同一服務、否則擴容邏輯互相衝突。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 service decomposition。
2. **預測式 + 反應式擴容混用**：可預測（早晚通勤）用 scheduled scaling、不可預測（演唱會散場）用 reactive autoscaling、兩者組合。
3. **GPS 類持續寫入適合 KV / time-series store**：不適合放 OLTP DB、會佔用 transaction 資源。對應 [01 資料庫模組](/backend/01-database/) 的 storage choice。

跨平台等效：GCP GKE + HPA / VPA / Karpenter、Azure AKS + KEDA、自建 Kubernetes + Cluster Autoscaler 都可以實作對等架構。

## 下一步路由

- 想做微服務容量治理 → [05 部署平台模組](/backend/05-deployment-platform/) + [9.6 容量規劃模型](/backend/09-performance-capacity/)
- 想規劃事件型峰值 → [9.11 高峰事件準備](/backend/09-performance-capacity/) + [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)
- 想設計高頻 sustained workload → [01 資料庫模組](/backend/01-database/) + [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)

## 引用源

- [Lyft Case Study](https://aws.amazon.com/solutions/case-studies/lyft/)
- [DynamoDB Customers](https://aws.amazon.com/dynamodb/customers/)
