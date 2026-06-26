---
title: "Fargate"
date: 2026-06-26
description: "AWS ECS 的無伺服器執行模式，由 AWS 代管運算實例，不需要管 EC2 capacity 或 AMI 更新"
weight: 21
tags: ["infra", "knowledge-cards"]
---

Fargate 是 AWS [ECS](/infra/knowledge-cards/ecs/) 的一種 launch type，把容器的運算實例交給 AWS 代管。使用 Fargate 時不需要配 EC2 instance、不需要管 capacity provider 的 scaling、不需要更新 AMI——只描述 task 需要多少 vCPU 和記憶體，AWS 負責分配運算資源。

## 概念位置

ECS 有兩種 launch type，差別在運算層的管理責任：

| Launch type | 運算層管理    | 適用情境                           |
| ----------- | ------------- | ---------------------------------- |
| Fargate     | AWS 代管      | web API、微服務、批次任務          |
| EC2         | 自管 instance | GPU workload、高密度排程、成本敏感 |

Fargate 降低的是運維面（不用管 OS patch、不用管 instance 容量），代價是單位成本較高（同規格約比 EC2 高 20-40%）和啟動延遲（cold start 通常在 30-60 秒，EC2 上的 task 因為 instance 已在所以秒級啟動）。多數 web API 的初始選擇是 Fargate，流量穩定且成本壓力大時再切回 EC2 launch type。

## 可觀察訊號

評估是否從 Fargate 切到 EC2 的訊號是月費曲線。Fargate 按 vCPU-hour 和 memory-hour 計費，task 數量少時費用低、管理簡單。當 task 數量穩定在 10-20 個以上且流量模式可預測時，EC2 launch type 搭配 reserved instance 或 Savings Plans 的成本優勢開始顯著——但要承擔 instance 管理的運維負擔。詳細的成本分析見 [ECS Fargate 成本分析與優化](/infra/05-core-services/ecs-fargate-cost-optimization/)。

Fargate Spot 是介於兩者之間的選項：費用約為 on-demand Fargate 的 30%，但 AWS 可以隨時中斷 task（提前 2 分鐘通知）。適合可容忍中斷的 workload（批次處理、非即時的資料轉換），不適合面對使用者的即時 API。常見的混合策略是用 on-demand Fargate 跑基線流量、Fargate Spot 跑彈性擴張的部分。

## 設計責任

選 Fargate 時要決定三件事：task 的 vCPU / memory 規格（Fargate 的可選組合是固定的，不是任意搭配）、是否混用 Spot、以及 health check 的 grace period（Fargate 的 cold start 比 EC2 長，health check 太早判定失敗會讓 task 反覆重啟）。

task 規格的 rightsizing 靠 CloudWatch Container Insights 的 CPU / memory utilization 決定——p95 使用率低於 30% 代表規格過大、持續高於 80% 代表該升級。

## 鄰卡

- [ECS](/infra/knowledge-cards/ecs/) — Fargate 是 ECS 的 launch type 之一
- [ALB](/infra/knowledge-cards/alb/) — Fargate task 通常掛在 ALB 的 target group 後面
