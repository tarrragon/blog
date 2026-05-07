---
title: "4.C8 Airbnb：Kubernetes 規模化下的觀測訊號治理"
date: 2026-05-07
description: "叢集擴縮與工作負載變動如何回寫觀測模型。"
weight: 8
---

這個案例的核心責任是把平台擴縮行為轉成可觀測治理問題。

## 觀察

Airbnb 在 Kubernetes 規模化過程強調動態擴縮，代表觀測系統需要追上容量與拓撲變化。

## 判讀

若訊號模型無法反映動態叢集，告警與容量判讀容易失真。

## 策略

1. 將叢集層指標與服務層指標分開治理。
2. 在擴縮流程中保留關鍵健康訊號。
3. 用回溯報表驗證擴縮與事故關聯。

## 下一步路由

回 [4.13](/backend/04-observability/service-topology/) 與 [4.18](/backend/04-observability/observability-operating-model/)。

## 引用源

- [Dynamic Kubernetes Cluster Scaling at Airbnb](https://airbnb.tech/infrastructure/dynamic-kubernetes-cluster-scaling-at-airbnb/)
