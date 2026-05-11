---
title: "5.C6 Airbnb：Kubernetes 叢集擴縮演進"
date: 2026-05-07
description: "從手動擴縮走向自動化容量治理的部署平台案例。"
weight: 6
tags: ["backend", "deployment", "case-study"]
---

這個案例的核心責任是說明部署平台演進常來自容量治理需求。

## 觀察

Airbnb 的叢集演進從手動擴縮到多階段自動化，並隨工作負載成長調整策略。

## 判讀

叢集擴縮若停留在人工流程，面對高波動流量會放大成本與可用性風險。

## 策略

1. 把擴縮策略版本化與可回放。
2. 區分不同工作負載的擴縮政策。
3. 將容量治理與事故指標綁定。

## 下一步路由

回 [5.2](/backend/05-deployment-platform/kubernetes-deployment/) 與 [6.9](/backend/06-reliability/capacity-cost/)。

## 引用源

- [Dynamic Kubernetes Cluster Scaling at Airbnb](https://airbnb.tech/infrastructure/dynamic-kubernetes-cluster-scaling-at-airbnb/)
