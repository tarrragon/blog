---
title: "3.C35 Form3：NATS JetStream 多雲低延遲支付"
date: 2026-05-18
description: "Form3 服務 Tier-1 銀行、500ms SLA、SNS/SQS 吃 300ms 預算、改 NATS+JetStream 跨雲 6x 延遲改善。"
weight: 35
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 JetStream Leaf Node 在跨地理 / 跨雲 durability 拓樸的關鍵角色。

## 觀察

Form3 服務 Tier-1 銀行（含 Mastercard、Square 等）、要求 500ms 端到端 SLA、AWS SNS/SQS 約 300ms 延遲吃掉預算。在 Faster Payments 機房資源受限下、用 NATS + JetStream 替換 legacy pub/sub bus、達到約 6× 延遲改善並做到「AWS 整個 region 掛掉時不喪失處理能力」。

## 判讀

用 JetStream 的 Leaf Node 做跨雲橋接、把 on-prem Faster Payments 機房跟雲端 cluster 連起來。揭露金融支付對端到端 latency 預算的硬要求逼出特定 broker 選型、不是「Kafka / SQS 通用化」。

## 對應大綱

NATS 進階主題：Cluster + Supercluster + Leaf node / JetStream stream 設計。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.C1 Meta FOQS](/backend/03-message-queue/cases/meta-foqs-global-migration/)（跨區對照）。

## 引用源

- [How Form3 Built a Multi-Cloud Low-Latency Payments Service with NATS JetStream (Synadia blog)](https://www.synadia.com/blog/how-form3-built-a-multi-cloud-low-latency-payments-service-with-nats-io-jetstream)
