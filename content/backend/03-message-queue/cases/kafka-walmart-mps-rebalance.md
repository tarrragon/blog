---
title: "3.C17 Walmart：Messaging Proxy Service 解 rebalance storm"
date: 2026-05-18
description: "Walmart 每天 trillions of message、25K+ consumer 在 K8s、partition-consumer 1:1 模型撞到擴張極限。"
weight: 17
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 partition-consumer 1:1 模型在大規模 K8s 環境的擴張極限。

## 觀察

Walmart 每天 trillions of message、25K+ Kafka consumer 跑在 WCNP Kubernetes 多雲環境；最大痛點是 pod scaling / deploy / heartbeat fail 觸發 consumer rebalance、lag spike。

## 判讀

自建 Messaging Proxy Service（MPS、Kafka Connect sink connector）、把 consumer 從 partition-bound 解耦成 stateless REST service、可獨立 auto-scale、不用增 partition；內建 DLQ 處理 poison pill。揭露「consumer 該跟 partition 數綁定」這個假設在 K8s 規模化下不再成立。

## 對應大綱

Kafka 進階主題：rebalance storm / consumer lag / multi-tenant 配額。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Reliably Processing Trillions of Kafka Messages Per Day](https://medium.com/walmartglobaltech/reliably-processing-trillions-of-kafka-messages-per-day-23494f553ef9)
