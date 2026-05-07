---
title: "5.C4 Mobileye：Workloads 遷移到 EKS"
date: 2026-05-07
description: "大規模工作負載遷移到 managed Kubernetes 的分段治理案例。"
weight: 4
---

這個案例的核心責任是把 workload 遷移從基礎設施作業改成服務可用性作業。

## 觀察

Mobileye 將工作負載遷移到 EKS，重點在治理可用性與運維一致性，而非單純換平台。

## 判讀

工作負載遷移若缺乏分段驗證，容易在切流時放大依賴與資源風險。

## 策略

1. 分批遷移 workload，保留觀測對照。
2. 明確定義每批次切換與回退條件。
3. 在新平台上先驗證容量與恢復節奏。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 與 [6.19 reliability readiness review](/backend/06-reliability/reliability-readiness-review/)。

## 引用源

- [Mobileye migration to Amazon EKS](https://aws.amazon.com/solutions/case-studies/mobileye-amazon-eks/)
