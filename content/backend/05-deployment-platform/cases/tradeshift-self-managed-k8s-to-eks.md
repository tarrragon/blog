---
title: "5.C1 Tradeshift：self-managed Kubernetes 遷移到 EKS"
date: 2026-05-07
description: "零停機平台遷移的分段策略案例。"
weight: 1
---

這個案例的核心責任是把平台遷移從「搬家」改寫成「流量與依賴分段切換」。

## 觀察

Tradeshift 從 self-hosted Kubernetes 遷移到 EKS，並以零停機為前提設計遷移策略。

## 判讀

這類遷移的難點通常在跨叢集服務依賴與流量切換，不在 Kubernetes API 本身。

## 策略

1. 先建立新叢集與共通配置基線。
2. 用可控流量策略分批切換服務。
3. 每批保留可回退路徑與驗證門檻。

## 下一步路由

回 [5.2 kubernetes deployment](/backend/05-deployment-platform/kubernetes-deployment/) 與 [6.8 release gate](/backend/06-reliability/release-gate/)。

## 引用源

- [Tradeshift migration to EKS](https://aws.amazon.com/blogs/containers/tradeshifts-migration-to-amazon-eks-without-downtime-using-linkerd/)
