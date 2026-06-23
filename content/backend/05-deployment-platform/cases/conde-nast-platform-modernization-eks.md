---
title: "5.C2 Condé Nast：EKS 平台整併與標準化"
date: 2026-05-07
description: "多地區異質 Kubernetes 平台整併為統一控制面的案例。"
weight: 2
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明平台整併常是組織治理問題，技術選型只是其中一層。

## 觀察

Condé Nast 旗下多個小團隊各自維護獨立的 Kubernetes 環境，各團隊使用不同的 Kubernetes 版本、操作模型、部署流程與存取模式。Self-managed Kubernetes 跑在 EC2 上，每個團隊自行維護 control plane、AMI、安全修補與 IAM credential 管理（使用 kube2iam 等開源工具）。

整併後成立一個 single global platform team，遷移到 Amazon EKS。技術棧標準化為 Bottlerocket OS、VPC CNI、AWS Load Balancer Controller、IRSA（IAM Roles for Service Accounts）。Multi-tenancy 用 Kubernetes namespace 隔離，搭配 resource quotas 與 limits 防止 noisy neighbor。

結果面：搭配 CloudFront 與 AWS Global Accelerator 後，end user latency 降低達 50%。團隊可以在 guardrails 內快速建立新叢集，operational overhead 顯著降低。

## 判讀

平台碎片化的代價分兩層。表面層是重工——每個團隊各自處理安全修補、版本升級、credential 管理，相同工作做了 N 遍。深層是一致性缺失——不同團隊的安全基線不同，某個團隊漏修的 CVE 可能成為整個組織的入口。

整併的工程價值在於把「每個團隊各自解決平台問題」變成「平台團隊解決一次、所有團隊共用」。這個轉換的前提是平台團隊能提供足夠彈性的 multi-tenancy 模型——resource quotas 防止資源搶占、namespace 隔離防止互相影響、IRSA 讓每個 workload 有獨立的 AWS 權限而非共用 node-level credential。

kube2iam → IRSA 的切換是這個案例中安全基線提升最顯著的一步。kube2iam 依賴 iptables 攔截 metadata endpoint，在多租戶環境下有 race condition 與 credential leak 風險。IRSA 用 OIDC federation 讓每個 service account 直接取得 scoped IAM role，消除了 node-level 的 credential 共用。

## 策略

1. **盤點既有叢集的差異維度**：Kubernetes 版本、CNI、ingress controller、credential 管理方式、部署流程、監控工具。差異清單是遷移計畫的輸入。
2. **定義統一平台基線**：選定 EKS + Bottlerocket + VPC CNI + IRSA 作為所有叢集的共通配置。基線要涵蓋安全（pod 唯讀 filesystem、禁 root）、資源（quotas、limits）、網路（CNI、LB controller）。
3. **用 namespace multi-tenancy 取代獨立叢集**：每個團隊一個 namespace，resource quotas 限制資源用量。這比一個團隊一個叢集的運維成本低，但需要在 namespace 層級做好隔離（NetworkPolicy、ResourceQuota、RBAC scope）。
4. **漸進切換業務流量**：按 region / 市場分批遷移，每批遷移後驗證 latency 與 error rate。搭配 CloudFront 做 edge 層的流量管理。

## 可回寫的章節段落

- [5.2 大規模 K8s 的設計取捨](/backend/05-deployment-platform/kubernetes-deployment/#大規模-k8s-的設計取捨)：single-cluster multi-namespace 的治理單位選擇
- [5.7 Managed 平台跟團隊職責邊界](/backend/05-deployment-platform/traffic-config-control-plane-boundary/#managed-平台跟團隊職責邊界)：global platform team 的職責重訂
- [5.3 Load Balancer Contract](/backend/05-deployment-platform/load-balancer-contract/)：AWS LB Controller + CloudFront 的流量入口配置

## 引用源

- [How Condé Nast modernized its container platform on Amazon EKS](https://aws.amazon.com/blogs/containers/how-conde-nast-modernized-its-container-platform-on-amazon-elastic-kubernetes-service/)
