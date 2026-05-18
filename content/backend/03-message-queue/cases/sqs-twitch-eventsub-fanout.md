---
title: "3.C54 Twitch EventSub：SNS+SQS fan-out 給第三方"
date: 2026-05-18
description: "Twitch Event Bus ~1660 events/sec 進 SNS、EventSub 用 SQS 接收 + Dispatcher fan-out 給訂閱者。"
weight: 54
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 SNS-SQS fan-out + dispatcher pattern 的實戰。

## 觀察

Twitch 內部 Event Bus 發佈 ~1660 events/sec 到 SNS。EventSub（給第三方應用訂閱 Twitch 事件）用 SQS 接收 async notification、再由 Dispatcher fan-out 給各訂閱者。

## 判讀

fan-out 後每個 consumer 要自己一個 queue。揭露 SNS → SQS 是 AWS 生態的 fan-out 標配、SQS 是第三方訂閱的 buffer 層、Dispatcher 是 application 級別的分發責任。

## 對應大綱

SQS 進階主題：Standard queue + SQS + Lambda / SNS-SQS fan-out。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.C51 Atlassian JiRT](/backend/03-message-queue/cases/sqs-atlassian-jirt-kinesis-sqs/)（subscription 對照）。

## 引用源

- [Twitch State of Engineering 2023](https://blog.twitch.tv/en/2023/09/28/twitch-state-of-engineering-2023/)
