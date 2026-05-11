---
title: "5.C2 Condé Nast：EKS 平台整併與標準化"
date: 2026-05-07
description: "多地區異質 Kubernetes 平台整併為統一控制面的案例。"
weight: 2
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明平台轉換常是組織治理問題，不只是技術選型問題。

## 觀察

Condé Nast 原先各團隊維護不同自管集群與流程，後續以 EKS 與統一策略做平台整併。

## 判讀

當平台碎片化，重工成本與安全風險會升高，平台整併的價值在一致性與可維運性。

## 策略

1. 先盤點既有集群與差異策略。
2. 建立統一平台基線與部署流程。
3. 以藍綠或漸進切換把業務流量搬遷到新平台。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 與 [5.3 load balancer contract](/backend/05-deployment-platform/load-balancer-contract/)。

## 引用源

- [Condé Nast modernized on EKS](https://aws.amazon.com/blogs/containers/how-conde-nast-modernized-its-container-platform-on-amazon-elastic-kubernetes-service/)
