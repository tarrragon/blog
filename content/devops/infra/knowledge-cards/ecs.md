---
title: "ECS"
date: 2026-06-26
description: "AWS Elastic Container Service — 受管的容器編排服務，用 task definition 描述容器配置、由平台負責排程與健康管理"
weight: 11
tags: ["infra", "knowledge-cards", "ecs", "compute"]
aliases: ["/infra/knowledge-cards/ecs/"]
---

ECS（Elastic Container Service）的核心職責是把容器映像排程到運算資源上執行，並管理它們的生命週期 — 健康檢查、失敗重啟、滾動更新。它是 AWS 上容器工作負載的預設起點，心智負擔低於 Kubernetes（EKS），但編排彈性也較受限。執行單位可以是自管的 EC2 instance，也可以是免運維的 [Fargate](/devops/infra/knowledge-cards/fargate/)。

## 跟其他概念的關係

ECS 在核心服務層裡的角色是「應用程式的執行載體」。它跑在 VPC 的 private subnet 裡，用 IAM task role 存取其他 AWS 資源，前面掛 ALB 接收流量。IaC 描述 ECS 時，重點在「接線」（subnet、security group、IAM role、target group）而非容器映像版本 — 映像版本由 CI/CD 在部署期注入。

ECS 的執行模式分 [EC2](/devops/infra/knowledge-cards/ec2/) launch type（自己管運算實例、要管 AMI 更新與 capacity provider）和 Fargate launch type（AWS 代管運算、不需管實例）。Fargate 進一步降低運維面，代價是單位成本較高（同規格約多 20-40%）且不支援 GPU workload。

## 可觀察訊號

以下狀況指向 ECS 相關問題：

- Task 頻繁被 kill 後重啟 — 健康檢查失敗或 OOM，先看 task 的 stopped reason 和 CloudWatch log
- 部署後新版本遲遲不上線 — rolling update 的 minimum healthy percent 設太高，新 task 啟動空間不足
- Task 無法拉到 ECR image — 通常是 private subnet 沒有 NAT 或 VPC Endpoint 到 ECR

## 判斷條件與後果

ECS 的設定多半在劃責任交界：運算實例歸 AWS 還是團隊、權限歸哪個 role、映像版本歸 infra code 還是 CI/CD，以及擴容看哪一個指標。每一條交界劃錯的代價不同：

- **Launch type**：選 Fargate 時 AMI 與容量由 AWS 管理，代價是同規格的單位成本較高；選 EC2 時單位成本較低，AMI 更新與 capacity provider 回到團隊身上。task 數量少時兩者的成本差額小，所以多數 web API 從 Fargate 起步，流量穩定、task 數量變多之後再評估 EC2
- **Task IAM role**：task execution role 給 ECS 拉 image 與寫 log，task role 給應用程式存取其他 AWS 資源。兩者合成同一個 role 時，應用程式多拿到拉 image 的權限，ECS 拉 image 時也帶著應用程式的資料權限；這個 role 的憑證不論從哪一個用途外洩，拉 image 與存取資料兩組權限都一起交出去
- **映像版本**：image tag 寫死在 infra code 時，每次發版都要改 infra code 並跑 apply，部署與基礎設施變更綁在同一個流程；tag 由 CI/CD 在部署期注入時，infra code 只描述接線，發版不動 infra
- **Auto-scaling 指標**：計算密集的服務先在 CPU 上飽和，CPU 或 memory 的使用率對得上它的瓶頸；IO 密集的服務在等外部回應，CPU 還不高時請求已經在累積，用 CPU 觸發擴容會太晚，ALB request count 比較早反映負載

## 鄰卡

- [Subnet](/devops/infra/knowledge-cards/subnet/) — ECS task 跑在 private subnet 裡
- [Security Group](/devops/infra/knowledge-cards/security-group/) — ECS service 套用 security group 控制入站
- [IAM](/devops/infra/knowledge-cards/iam/) — task role 與 execution role 是 ECS 的兩個身分接線
- [ALB](/devops/infra/knowledge-cards/alb/) — 流量透過 ALB target group 導入 ECS task
