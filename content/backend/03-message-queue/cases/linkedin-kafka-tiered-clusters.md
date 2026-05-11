---
title: "3.C4 LinkedIn：Kafka 分層叢集治理"
date: 2026-05-07
description: "Kafka 從單叢集走向 tiered clusters 的轉換案例。"
weight: 4
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是把 queue 轉換從容量問題提升到治理問題。

## 觀察

LinkedIn 在 Kafka 規模化過程引入分層叢集策略，按業務特性與風險分配不同叢集。

## 判讀

當所有 workload 混在同一叢集，故障與資源競爭容易互相放大。

## 策略

1. 依流量與可靠性需求分層。
2. 為高優先 workload 提供獨立保護。
3. 建立跨叢集治理與容量規劃節奏。

## 下一步路由

回 [3.1 broker basics](/backend/03-message-queue/broker-basics/) 與 [6.14 dependency reliability budget](/backend/06-reliability/dependency-reliability-budget/)。

## 引用源

- [Running Kafka at Scale at LinkedIn](https://engineering.linkedin.com/kafka/running-kafka-scale)
