---
title: "3.C55 SmugMug：SQS 驅動可重放搜尋管線"
date: 2026-05-18
description: "SmugMug 用 SQS 兩種模式：DynamoDB scan-segment 平行 backfill + production query 鏡像 replay 到 replica。"
weight: 55
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 SQS 作為「workload generator」的分散式平行化角色。

## 觀察

SmugMug 用 SQS 兩種模式：(1) backfill — script 推 DynamoDB scan-segment 指令進 SQS、Lambda 拉取做平行掃描寫 OpenSearch、(2) 鏡像查詢 — production query 推副本 SQS、Lambda replay 到 replica domain。每小時可 index > 1 billion document、不影響 production。

## 判讀

SQS 作為「workload generator」分散式平行化、不需協調 worker 數量。揭露 SQS 不只是「事件 queue」、也是「並行任務分散」的協調基礎。

## 對應大綱

SQS 進階主題：Standard queue / Long polling / SQS + Lambda event source。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [SmugMug's Durable Search Pipelines for Amazon OpenSearch Service](https://aws.amazon.com/blogs/big-data/smugmugs-durable-search-pipelines-for-amazon-opensearch-service/)
