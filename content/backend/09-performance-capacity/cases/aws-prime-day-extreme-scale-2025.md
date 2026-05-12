---
title: "9.C1 AWS Prime Day 2025：可預期極端峰值的 dogfood"
date: 2026-05-12
description: "Amazon 自家服務在 Prime Day 2025 的峰值數字 — 一年一次可預期峰值的容量設計參考"
weight: 1
tags: ["backend", "performance", "capacity", "case-study"]
---

這個案例的核心責任是提供「極端可預期峰值」的容量設計參考點。Prime Day 是 Amazon 每年最大的單一行銷事件、發生時間提前數月公告、所有相依服務都能進入準備階段、是最接近「教科書版本的容量規劃」的真實場景。

## 觀察

2025 年 Prime Day 期間 AWS 主要服務的峰值數字（引自 [AWS News Blog](https://aws.amazon.com/blogs/aws/aws-services-scale-to-new-heights-for-prime-day-2025-key-metrics-and-milestones/)）：

| 服務                   | 峰值                       | 年增率      |
| ---------------------- | -------------------------- | ----------- |
| Amazon SQS             | 1.66 億訊息 / 秒（新紀錄） | -           |
| AWS Lambda             | 每日 1.7 兆次呼叫          | -           |
| Amazon API Gateway     | 1 兆次內部請求             | +30%        |
| Amazon DynamoDB        | 1.51 億 RPS、毫秒級回應    | -           |
| Amazon ElastiCache     | 每日 1.5 quadrillion 請求  | -           |
| Amazon CloudFront      | 3 兆次 HTTP 請求           | +43%        |
| Amazon Kinesis Streams | 8.07 億 records / 秒峰值   | -           |
| Amazon EBS             | 20.3 兆次 I/O              | -           |
| Amazon Aurora          | 5000 億次 transaction      | -           |
| Amazon SageMaker AI    | 6260 億次推論請求          | -           |
| Amazon ECS on Fargate  | 每日 1840 萬個 task        | +77%        |
| AWS FIS（混沌實驗）    | 6800+ 次彈性測試           | 8 倍於 2024 |

基礎設施層面：AWS Graviton 處理器承擔超過 40% 的 EC2 compute、部署超過 87,000 顆 Inferentia / Trainium AI 晶片、AWS Outposts 對機器人下達 5.24 億條指令（年增 160%）。

## 判讀

Prime Day 是「可預期極端峰值」的標竿。它的容量問題不是「會不會撐住」、而是「準備到什麼程度才划算」。對應主章問題節點：

1. **Capacity Planning**（[9.6](/backend/09-performance-capacity/)）：年度活動的容量計算可以用歷史 baseline × 預期成長 × headroom 三項相乘、但 Prime Day 規模下、每一項的不確定性放大都會變成數百萬美金成本差異。Amazon 公開的年增率（API Gateway +30%、CloudFront +43%、ECS on Fargate +77%）顯示連 Amazon 自己每年的成長預測都不能直線外推。
2. **Performance Observability**（[9.8](/backend/09-performance-capacity/)）：DynamoDB 「1.51 億 RPS、毫秒級回應」這種敘述同時包含吞吐與延遲、是 production-grade 容量地圖的最小單位。只說吞吐不說延伸分布、容量資訊不完整。
3. **Improvement Loop**（[9.9](/backend/09-performance-capacity/)）：FIS 混沌實驗 8 倍於 2024 顯示 Amazon 把「在 Prime Day 之前主動製造失敗」當成必修課、不是事後檢討。這層投資跟容量規劃同等重要。

## 策略

這個案例可以抽出三個跨平台可重用的工程做法。

1. **把可預期峰值寫進服務級 SLO**：Prime Day 在 SQS / Lambda / DynamoDB / Aurora 都建立了內部 SLO baseline、平日跑在 baseline 之下、峰值是擴張到「設計容量」而不是「實驗容量」。這跟 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) 直接對齊。
2. **pre-scaling + scheduled capacity**：CloudFront 43%、API Gateway 30% 的年增率都是 *提前算進* 容量計畫、不是當天 reactive 擴容。對應 EC2 Auto Scaling 的 [predictive / scheduled scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-predictive-scaling.html) 模式。
3. **事前主動製造失敗、不靠當天 reactive**：FIS 8x 成長代表「在 Prime Day 之前 6800 次 chaos test」、把驗證成本前置到容量規劃階段。這條跟 [06.4 Chaos Testing](/backend/06-reliability/chaos-testing/) 形成閉環 — 06 講失敗模式驗證、09 講容量地圖、兩者在 Prime Day 級別的事件上必須一起做。

跨平台等效：GCP 的 Compute Engine MIG + Predictive Autoscaler、Azure 的 VM Scale Sets + Predictive Autoscale、Kubernetes 生態的 KEDA + Karpenter 都可以實作同樣的 pre-scaling 策略。差異是 vendor 整合度、不是工程概念。

## 下一步路由

- 想規劃年度活動容量 → [9.6 容量規劃模型](/backend/09-performance-capacity/) + [9.11 高峰事件準備](/backend/09-performance-capacity/)
- 想設計可預期峰值的 SLO → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/) + [06.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/)
- 想做事前混沌驗證 → [06.4 Chaos Testing](/backend/06-reliability/chaos-testing/) + [06.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)
- 對照不同形狀的峰值 → [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)（事件型不可預期峰值）/ [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/)（無峰值低延遲）

## 引用源

- [AWS services scale to new heights for Prime Day 2025: key metrics and milestones](https://aws.amazon.com/blogs/aws/aws-services-scale-to-new-heights-for-prime-day-2025-key-metrics-and-milestones/)
- [Conquering Peak Retail Events with AWS](https://aws.amazon.com/blogs/industries/conquering-peak-retail-events-with-aws/)
- [Predictive scaling for Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-predictive-scaling.html)
