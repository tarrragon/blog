---
title: "3.C56 PostNL EBE：完整 DLQ + retention + redrive 設計"
date: 2026-05-18
description: "PostNL 物流每天 1000 萬訊息、每 producer/consumer 隔離 stack、24h 內 100 次 retry、final DLQ 可 consumer redrive。"
weight: 56
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是業內真正完整的 DLQ + redrive + retention 設計案例、不是 demo 規模。

## 觀察

PostNL（荷蘭最大物流商、每天 6.9M 信件 + 1.1M 包裹）的 Event Broker E-commerce 系統每天處理 ~10M message。完整列出 SQS 配置：每 producer/consumer 隔離 stack（最小爆炸半徑）、3 天 replay via EventBridge、exponential backoff with jitter、24 小時內最多 retry 100 次、final DLQ 允許 consumer 自己 redrive。max receive count 設 1 觸發 DLQ 告警。

## 判讀

「每 producer/consumer 隔離 stack」是 mission-critical 系統的 blast radius 設計、不只是 queue 配置。揭露 production-grade SQS 設計含三件事：隔離 + retry 政策 + redrive 流程。

## 對應大綱

SQS 進階主題：DLQ 設計 / CloudWatch alarm / Cost 模型。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.C9 反例：語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。

## 引用源

- [Designing a Mission-Critical Serverless Application for High Resilience](https://medium.com/postnl-engineering/design-a-mission-critical-serverless-application-for-high-resilience-2858bf11360a)
