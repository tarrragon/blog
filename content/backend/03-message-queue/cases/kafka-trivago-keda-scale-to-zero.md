---
title: "3.C22 Trivago：KEDA scale-to-zero by Kafka lag"
date: 2026-05-18
description: "Trivago 50+ Kafka sink、CPU/mem autoscaling 無效（I/O bottleneck）、KEDA 以 consumer lag 為訊號達到 scale-to-zero。"
weight: 22
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 event-driven workload 該按 backlog 而非 resource usage scale 的設計判準。

## 觀察

Trivago 跨 3 個 region 跑 50+ Kafka sink service、每個 always-on 用 1 CPU + 1 GB；CPU/mem-based autoscaling 無效（sink 多為 I/O bottleneck、CPU 平坦）。

## 判讀

KEDA 以 consumer lag 為 scaling signal、minReplicaCount=0 達到 scale-to-zero、daily replica-hour 從 50 降到 1-2。揭露「resource usage 不等於工作量」、event-driven 場景該看 backlog signal。

## 對應大綱

Kafka 進階主題：consumer lag / autoscaling / multi-tenant 配額。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [From Always-On to On-Demand: Scaling Kafka Sinks with KEDA](https://tech.trivago.com/post/2026-02-18-from-always-on-to-on-demand-scaling-kafka-sinks-with-keda)
