---
title: "3.C51 Atlassian JiRT：Kinesis + SQS subscription"
date: 2026-05-18
description: "Atlassian StreamHub Kinesis 底層、每 consumer 自己一個 SQS queue、JiRT 把輪詢 1 min 改成秒級 event-driven。"
weight: 51
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 SQS 作為 streaming source 的 per-consumer subscription 模式。

## 觀察

Atlassian 內部 event bus StreamHub 底層用 Kinesis、但「每個 consumer 自己準備 SQS queue 接收 event」。JiRT 即時服務透過此模式把輪詢式（~1 min）改成 event-driven（秒級）。

## 判讀

在 Kinesis 上面疊 SQS 讓 consumer 各自設定 retention、各自獨立 visibility timeout。揭露「stream + per-consumer queue」是 fan-out 場景的常見複合 pattern、不是 streaming vs queue 二選一。

## 對應大綱

SQS 進階主題：Standard vs FIFO / SQS 作為 fan-out subscriber。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)（streaming + queue 對照）。

## 引用源

- [Using an Event-Driven Architecture to Improve Jira Software Responsiveness](https://www.atlassian.com/blog/atlassian-engineering/using-an-event-driven-architecture-to-improve-jira-software-responsiveness)
