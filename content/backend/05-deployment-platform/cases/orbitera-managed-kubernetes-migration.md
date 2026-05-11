---
title: "5.C3 Orbitera：遷移到 Managed Kubernetes"
date: 2026-05-07
description: "平台重置時如何讓產品不中斷地完成編排層轉換。"
weight: 3
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明平台遷移的關鍵在服務連續性，而非單次替換完成。

## 觀察

Orbitera 在產品持續運作下，完成從既有雲環境到 managed Kubernetes 的遷移。

## 判讀

跨平台遷移本質是能力遷移：部署、觀測、恢復與團隊流程都需要同步重建。

## 策略

1. 先用最小可行服務驗證新平台。
2. 逐步搬遷核心工作負載，保留回切策略。
3. 把平台能力（升級、修補、擴容）納入日常治理節奏。

## 下一步路由

回 [5.1 container runtime](/backend/05-deployment-platform/container-runtime/) 與 [6.7 DR/rollback rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)。

## 引用源

- [Orbitera migrated to managed Kubernetes](https://cloud.google.com/blog/products/gcp/why-we-migrated-orbitera-to-managed-kubernetes-on-google-cloud-platform/)
