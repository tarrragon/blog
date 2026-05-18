---
title: "3.C52 Nielsen：Spark on EKS 雙 SQS 工作流"
date: 2026-05-18
description: "Nielsen 每日 25TB / 30B event、work queue + completion queue 雙 SQS、queue depth autoscale EKS pod。"
weight: 52
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 SQS queue depth 作為 autoscale 訊號的真實案例。

## 觀察

Nielsen 每日處理 25 TB / 30 billion event。架構用兩個 SQS queue：work queue（待處理工作項）+ completion queue（回報完成）。Lambda 從 DB 拉檔案、組成 work item 推進 work queue、EKS pod 拉取處理、處理完寫 completion queue。基於 queue depth 自動擴 pod。

## 判讀

不用直接 Lambda invoke（pod 上跑長時間 Spark workload）、queue depth 當 backlog signal driving autoscale。揭露長 workload 場景該用 pod + queue depth、不是 Lambda function。

## 對應大綱

SQS 進階主題：CloudWatch metric + alarm / Standard queue / 長 workload autoscaling。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.C22 Trivago KEDA](/backend/03-message-queue/cases/kafka-trivago-keda-scale-to-zero/)（lag-based autoscale 對照）。

## 引用源

- [How Nielsen Uses Serverless Concepts on Amazon EKS for Big Data Spark Workloads](https://aws.amazon.com/blogs/architecture/how-nielsen-uses-serverless-concepts-on-amazon-eks-for-big-data-processing-with-spark-workloads/)
