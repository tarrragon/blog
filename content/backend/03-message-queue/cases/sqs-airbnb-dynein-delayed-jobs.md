---
title: "3.C48 Airbnb Dynein：SQS 分散式延遲任務排程"
date: 2026-05-18
description: "Airbnb 用 SQS at-least-once + DLQ 取代 Resque 單 Redis 限制、每 scheduler 1000 QPS、SQS wrap DynamoDB 處理 > 15 分鐘 delay。"
weight: 48
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 SQS at-least-once + DLQ 模型在工作排程的對齊邏輯。

## 觀察

Airbnb 構建 Dynein 分散式延遲任務排程系統取代 Resque（受限於單 Redis 實例）。明確選 SQS、利用 at-least-once delivery、dead letter queue、individual message acknowledgment、access control 與 encryption-at-rest。每個 scheduler instance 達 ~1000 QPS、可水平擴展。

## 判讀

at-least-once 對工作排程「不丟資料」假設足夠、SQS wrap DynamoDB 處理 > 15 分鐘 delay、DLQ 分離「短暫失敗」與「永久毒訊息」。揭露 managed queue 在工作排程的取捨：trade ordering 換 scaling。

## 對應大綱

SQS 進階主題：Standard vs FIFO / DLQ 設計。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。

## 引用源

- [Dynein: Building a Distributed Delayed Job Queueing System](https://medium.com/airbnb-engineering/dynein-building-a-distributed-delayed-job-queueing-system-93ab10f05f99)
