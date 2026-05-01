---
title: "Terraform / OpenTofu"
date: 2026-05-01
description: "Infrastructure as Code 主流工具"
weight: 7
---

Terraform 是 HashiCorp 出品的 IaC 工具、HCL 配置語言、provider 生態最廣（AWS / GCP / Azure / Kubernetes 等）。2023 授權變動為 BSL、社群 fork OpenTofu（Linux Foundation 託管、MPL 2.0）。

## 適用場景

- 跨雲 / 多 provider 基礎設施管理
- 需要 declarative state 管理
- 團隊協作的 IaC（remote state / workspaces）
- Module 復用

## 不適用場景

- 想要 imperative API（用 Pulumi）
- 純 Kubernetes 配置（用 Helm / kustomize / cdk8s）
- 極小場景（直接 CLI 命令更快）

## 跟其他 vendor 的取捨

- vs `opentofu`：Terraform fork、解決授權問題、API 相容
- vs Pulumi：Pulumi 用通用語言（TS / Python / Go）、Terraform 用 HCL
- vs CloudFormation / CDK / Bicep：cloud-specific IaC
- vs Crossplane：k8s-native IaC

## 預計實作話題

- State 管理（local / remote / S3 + DynamoDB lock）
- Module 設計
- Workspaces vs directory layout
- Plan / apply workflow + GitOps
- Terraform vs OpenTofu 遷移
- Drift detection
