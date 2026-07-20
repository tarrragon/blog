---
title: "ECS"
date: 2026-06-26
description: "AWS Elastic Container Service — 受管的容器編排服務，用 task definition 描述容器配置、由平台負責排程與健康管理"
weight: 11
tags: ["infra", "knowledge-cards", "ecs", "compute"]
---

ECS（Elastic Container Service）的核心職責是把容器映像排程到運算資源上執行，並管理它們的生命週期 — 健康檢查、失敗重啟、滾動更新。它是 AWS 上容器工作負載的預設起點，心智負擔低於 Kubernetes（EKS），但編排彈性也較受限。執行單位可以是自管的 EC2 instance，也可以是免運維的 [Fargate](/infra/knowledge-cards/fargate/)。

## 概念位置

ECS 在核心服務層裡的角色是「應用程式的執行載體」。它跑在 VPC 的 private subnet 裡，用 IAM task role 存取其他 AWS 資源，前面掛 ALB 接收流量。IaC 描述 ECS 時，重點在「接線」（subnet、security group、IAM role、target group）而非容器映像版本 — 映像版本由 CI/CD 在部署期注入。

ECS 的執行模式分 [EC2](/infra/knowledge-cards/ec2/) launch type（自己管運算實例、要管 AMI 更新與 capacity provider）和 Fargate launch type（AWS 代管運算、不需管實例）。Fargate 進一步降低運維面，代價是單位成本較高（同規格約多 20-40%）且不支援 GPU workload。

## 可觀察訊號

以下狀況指向 ECS 相關問題：

- Task 頻繁被 kill 後重啟 — 健康檢查失敗或 OOM，先看 task 的 stopped reason 和 CloudWatch log
- 部署後新版本遲遲不上線 — rolling update 的 minimum healthy percent 設太高，新 task 啟動空間不足
- Task 無法拉到 ECR image — 通常是 private subnet 沒有 NAT 或 VPC Endpoint 到 ECR

## 設計責任

使用 ECS 時要決定：

- **Launch type**：Fargate（低運維、較高成本）還是 EC2（低成本、要管實例）。多數 web API 的初始選擇是 Fargate，流量穩定後再評估 EC2
- **Task IAM role**：task execution role（拉 image 和寫 log 用）和 task role（應用程式存取其他 AWS 資源用）是兩個不同的 role，不要混用
- **映像版本解耦**：task definition 裡的 image tag 由 CI/CD 部署期注入，infra code 不寫死版本號
- **Auto-scaling 指標**：用 CPU / memory 還是 ALB request count，取決於服務是計算密集還是 IO 密集

## 鄰卡

- [Subnet](/infra/knowledge-cards/subnet/) — ECS task 跑在 private subnet 裡
- [Security Group](/infra/knowledge-cards/security-group/) — ECS service 套用 security group 控制入站
- [IAM](/infra/knowledge-cards/iam/) — task role 與 execution role 是 ECS 的兩個身分接線
- [ALB](/infra/knowledge-cards/alb/) — 流量透過 ALB target group 導入 ECS task
