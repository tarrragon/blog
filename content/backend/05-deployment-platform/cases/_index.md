---
title: "模組五案例正文"
date: 2026-05-07
description: "部署平台轉換案例入口。"
weight: 80
tags: ["backend", "deployment", "case-study"]
---

這個資料夾的核心責任是把平台遷移案例轉成部署策略、切流策略與回退策略的可操作內容。

## 案例列表

| 章節                                                                                       | 主題                                | 核心責任                           |
| ------------------------------------------------------------------------------------------ | ----------------------------------- | ---------------------------------- |
| [5.C1](/backend/05-deployment-platform/cases/tradeshift-self-managed-k8s-to-eks/)          | Tradeshift：self-managed K8s -> EKS | 把零停機平台遷移拆成可執行階段     |
| [5.C2](/backend/05-deployment-platform/cases/conde-nast-platform-modernization-eks/)       | Condé Nast：EKS 平台整併            | 把多團隊異質集群整併成單一治理面   |
| [5.C3](/backend/05-deployment-platform/cases/orbitera-managed-kubernetes-migration/)       | Orbitera：遷移到 managed Kubernetes | 把平台重置與產品不中斷目標對齊     |
| [5.C4](/backend/05-deployment-platform/cases/mobileye-workloads-to-eks/)                   | Mobileye：workloads -> EKS          | 把工作負載搬遷策略做成可回退階段   |
| [5.C5](/backend/05-deployment-platform/cases/miro-managed-eks-migration/)                  | Miro：managed EKS 遷移              | 把平台託管化與團隊維運模型對齊     |
| [5.C6](/backend/05-deployment-platform/cases/airbnb-kubernetes-cluster-scaling-evolution/) | Airbnb K8s 叢集演進                 | 把手動擴縮轉成自動化容量治理       |
| [5.C7](/backend/05-deployment-platform/cases/airbnb-istio-upgrade-governance/)             | Airbnb Istio 升級治理               | 把 service mesh 升級變成可重播流程 |
| [5.C9](/backend/05-deployment-platform/cases/failure-platform-cutover-without-drain/)      | 反例：切流未先 drain                | 平台切換忽略連線清退造成錯誤暴增   |
| [5.C10](/backend/05-deployment-platform/cases/contrast-platform-migration-by-scale/)       | 對照：規模差異下平台遷移            | 小中大型組織的平台遷移風險邊界不同 |
