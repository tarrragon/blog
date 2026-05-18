---
title: "3.C11 Pinterest：Kafka tiered storage broker-decoupled"
date: 2026-05-18
description: "Pinterest 採 broker-decoupled tiered storage、把 ~200 TB/day 熱資料卸到 S3、broker 不再是熱路徑。"
weight: 11
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 tiered storage 不只是「冷資料 offload」、是 broker 與儲存解耦的架構選擇。

## 觀察

Pinterest 從 Kafka broker 卸 ~200 TB/day 熱資料到 S3、2024 年 5 月起 20+ production topic 上線、跟 KIP-405 native tiered storage 不同、採 broker-decoupled 設計。

## 判讀

Broker-decoupled 設計讓 consumer 直接從 S3 拉、broker 不再是熱路徑。揭露「broker resource 跟 cross-AZ network cost」其實該分離治理、而非綁在 broker 容量擴張上。

## 對應大綱

Kafka 進階主題：tiered storage / 跨層儲存成本。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.1 broker basics](/backend/03-message-queue/broker-basics/)。

## 引用源

- [Pinterest Tiered Storage for Apache Kafka — a Broker-Decoupled Approach](https://medium.com/pinterest-engineering/pinterest-tiered-storage-for-apache-kafka-%EF%B8%8F-a-broker-decoupled-approach-c33c69e9958b)
