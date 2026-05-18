---
title: "Terraform / OpenTofu"
date: 2026-05-01
description: "Infrastructure as Code 主流工具"
weight: 7
tags: ["backend", "deployment", "vendor"]
---

Terraform 是 HashiCorp 出品的 IaC 工具、承擔三個責任：declarative infrastructure 配置（HCL）、state-based reconciliation（plan → apply）、跨 provider 抽象（AWS / GCP / Azure / K8s / SaaS）。設計取捨偏向「state-driven + declarative + multi-cloud」、provider 生態最廣。2023 改 BSL 授權、社群 fork OpenTofu（Linux Foundation 託管、MPL 2.0）。

對「跨雲基礎設施管理、團隊協作 IaC、需要 state + plan workflow」這條路徑、Terraform / OpenTofu 是首選。

## 本章目標

讀完本章後、你應該能：

1. 寫 HCL config（resource / variable / output / module）
2. 設定 remote state（S3 + DynamoDB lock / Terraform Cloud）
3. 設計 module + workspace 結構
4. 跑 plan / apply / destroy 工作流 + GitOps
5. 評估 Terraform vs OpenTofu vs Pulumi vs Crossplane

## 最短路徑：5 分鐘把 Terraform 跑起來

```bash
# 1. 安裝
# TODO: brew install terraform / opentofu

# 2. 寫 main.tf
# TODO: provider "aws" { region = "us-east-1" }
# TODO: resource "aws_s3_bucket" "demo" { bucket = "..." }

# 3. init + plan + apply
# TODO: terraform init
# TODO: terraform plan
# TODO: terraform apply
```

## 日常操作與決策形狀

### HCL config 結構

子議題：

- provider / resource / data source / variable / output / locals
- terraform block（required_version / required_providers / backend）
- Module（reusable group of resources）
- 對應指令：`terraform fmt`、`terraform validate`

### State 管理

子議題：

- Local state（terraform.tfstate）：dev / 學習用
- Remote state（S3 + DynamoDB lock / GCS / Terraform Cloud / Spacelift）
- State migration（terraform state mv / rm / import）
- State sensitive data 不入 git

### Plan / apply workflow

子議題：

- terraform plan -out=plan.tfplan（凍結結果）
- terraform apply plan.tfplan
- Auto-approve（CI / CD）vs manual approve（critical）
- 對應 GitOps：Atlantis / Terraform Cloud / Spacelift

## 進階主題（按需閱讀）

### Module 設計

子議題：

- Module input / output
- Module composition（root module → child module）
- Public module registry（Terraform Registry / OpenTofu Registry）
- Version pinning
- 對應 Terraform best practice

### Workspaces vs directory layout

子議題：

- Workspaces：同 module 多 instance（dev / staging / prod）
- Directory：每 env 一個 directory
- Workspaces 的局限（state 同 backend、env 共享 config）
- 選擇判讀：強隔離 → directory；快切換 → workspace

### Drift detection

子議題：

- Drift = 實際 infra ≠ Terraform state
- 偵測：`terraform plan` 跑出來有 diff
- 修法：Manual import / state pull / 修改 cloud directly + plan refresh
- 對應 自動化 drift detection（Atlantis / Driftctl）

### Terraform vs OpenTofu

子議題：

- 2023 Terraform 改 BSL：Linux Foundation fork OpenTofu
- OpenTofu 跟 Terraform 1.5 API 相容
- 之後分歧：OpenTofu 加 state encryption、provider iteration
- 遷移路徑：替換 binary、import 既有 state

### Provider 生態

子議題：

- AWS / Azure / GCP（cloud provider）
- Kubernetes / Helm（K8s provider）
- SaaS：Datadog / Pagerduty / Cloudflare / GitHub
- Community provider vs official provider 品質差距

### 跟 Crossplane / Pulumi 對比

子議題：

- Crossplane：K8s-native IaC（用 K8s CRD 管 cloud resource）
- Pulumi：用通用語言（TS / Python / Go / C#）寫 IaC
- 選擇判讀：純 cloud infra → Terraform / OpenTofu；K8s-heavy → Crossplane；developer-first → Pulumi

### Terraform Cloud / Spacelift / Atlantis

子議題：

- Terraform Cloud（HashiCorp managed）：remote state + run + policy
- Spacelift / env0：商業替代
- Atlantis：OSS Pull Request automation
- 對應 GitOps for IaC

## 排錯快速判讀

### State lock stuck

操作原則：DynamoDB lock 沒釋放（process killed）。判讀 + 修法：`terraform force-unlock <lock-id>`（小心）。

### Plan diff 過大

操作原則：drift 累積 / provider 升級 / config 改太多。判讀：先看 plan output、再決定要不要 apply。

### Provider auth fail

操作原則：AWS / GCP credentials 沒設、過期、權限不夠。判讀：`AWS_PROFILE` / IAM role / GCP ADC 配置。

### Module version 衝突

操作原則：root module 跟 child module 用不同 provider version。判讀：`terraform providers` 看 version constraint。

### Apply partial failure

操作原則：apply 中某 resource 失敗、state 一致性問題。判讀：state pull 看當前、可能要 import / state rm 修。

## 何時改走其他服務

| 需求形狀                         | 改走                                                  |
| -------------------------------- | ----------------------------------------------------- |
| OSI-licensed Terraform           | OpenTofu（同模組）                                    |
| Imperative API                   | Pulumi                                                |
| Cloud-specific（單一 cloud）     | CloudFormation / Azure Bicep / GCP Deployment Manager |
| K8s-native IaC                   | Crossplane                                            |
| Application config（不是 infra） | Helm / Kustomize / cdk8s                              |
| 極小場景                         | CLI / Cloud Shell（不用 IaC）                         |

## 不在本頁內的主題

- 完整 HCL syntax reference
- 各 provider 完整 resource list
- Terraform Cloud / Spacelift 商業 feature
- Drift detection 工具細節

## 案例回寫

### 跨 vendor 對照

| 案例                                                                                          | 對 Terraform 的對應       |
| --------------------------------------------------------------------------------------------- | ------------------------- |
| [5.C10 規模對照](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/) | 規模化 IaC 跟 GitOps 對接 |

**待補 Terraform 案例**：HashiCorp Cloud 大客戶案例、OpenTofu fork 後企業遷移案例、Drift detection 治理案例。

## 下一步路由

- 上游概念：[5 deployment platform](/backend/05-deployment-platform/)
- 平行 vendor：[Kubernetes](/backend/05-deployment-platform/vendors/kubernetes/)（K8s provider）
- 下游能力：[06 reliability](/backend/06-reliability/)（IaC GitOps + release gate）
