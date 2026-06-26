---
title: "checkov"
date: 2026-06-26
description: "開源的 IaC 靜態安全掃描工具，在不建立資源的前提下比對已知的壞寫法與安全反模式"
weight: 20
tags: ["infra", "knowledge-cards"]
---

checkov 是一個開源的靜態分析工具，掃描 Terraform / CloudFormation / Kubernetes 等 IaC 程式碼，比對內建的規則庫找出安全漏洞與合規違規。它在 `plan` 之前或之後執行、不建立任何雲端資源，所以是 CI pipeline 裡最便宜的安全檢查之一。

## 概念位置

checkov 在 [infra PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)裡的位置是 `fmt` → `validate` → **checkov / tfsec** → `plan`。前兩步檢查語法正確，checkov 檢查語意安全，plan 檢查實際差異。checkov 補的是 reviewer 肉眼容易漏的盲區——一條 [security group](/infra/knowledge-cards/security-group/) 規則寫成 `0.0.0.0/0` 在 HCL 裡只是一行字串，人會看漏，規則不會。

三個常見的 IaC 掃描工具各有側重：

| 工具    | 側重            | 維護方                   |
| ------- | --------------- | ------------------------ |
| checkov | 安全 + 合規     | Prisma Cloud (Palo Alto) |
| tfsec   | 安全            | Aqua Security            |
| tflint  | provider 正確性 | 社群                     |

checkov 的規則庫最廣（涵蓋 CIS Benchmark、SOC 2、PCI DSS 等合規框架），tfsec 的規則更聚焦安全面，tflint 偏向「這個 instance type 在這個 region 存不存在」的 provider 正確性。三者可疊加使用。

## 可觀察訊號

需要引入 checkov 的訊號是 PR review 開始漏掉安全問題——S3 bucket 缺 public access block、RDS 沒開加密、IAM policy 過寬。這些問題的 pattern 是固定的、可以用規則比對，不應該靠人記憶來擋。

checkov 命中後要區分「真漏洞」和「情境合理的例外」。ALB 的 HTTPS listener 在 port 443 開 `0.0.0.0/0` 是設計本意，不是漏洞。豁免用行內註解標記並寫理由：`#checkov:skip=CKV_AWS_260:ALB public HTTPS listener`。詳細的規則配置與豁免管理見 [checkov 與 tfsec 規則配置](/infra/07-infra-as-pr/checkov-tfsec-rule-customization/)。

## 設計責任

引入 checkov 時要決定兩件事：啟用哪些規則（全部 vs 漸進啟用），以及命中時 CI 要不要擋（hard fail vs warning）。常見的漸進策略是先從高嚴重度規則開始、設為 hard fail，中低嚴重度設為 warning，隨團隊習慣逐步收緊。

## 鄰卡

- [IaC](/infra/knowledge-cards/iac/) — checkov 掃描的對象
- [Security Group](/infra/knowledge-cards/security-group/) — checkov 最常攔截的 `0.0.0.0/0` 全開規則
