---
title: "3.C58 Twilio：SQS 緩衝高流量 webhook"
date: 2026-05-18
description: "Twilio 教用 SQS 緩衝 SMS / status callback webhook、分 queue（SMS vs callback）、long polling 減 cost、FIFO 300 TPS 上限要分片。"
weight: 58
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 webhook → SQS buffer 是 Twilio 推薦的 pattern、FIFO TPS 上限的分片實務。

## 觀察

Twilio 自己 engineering blog 教使用者用 SQS 緩衝來自 Twilio 的高流量 SMS / status callback webhook（避免下游 app 來不及處理）。用 separate queue 區分 SMS vs status callback、long polling 減少空 API call、特別點出 FIFO 300 TPS 上限要分 queue。

## 判讀

Webhook 是 push、下游可能來不及、SQS 當 buffer 是常見 pattern。揭露 FIFO 的 300 TPS 上限是 hard limit、要設計分片才能擴張。

## 對應大綱

SQS 進階主題：Long polling / Standard vs FIFO。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。

## 引用源

- [Handling High Volume Inbound SMS and Webhooks with Twilio Functions and Amazon SQS](https://www.twilio.com/en-us/blog/handling-high-volume-inbound-sms-and-webhooks-with-twilio-functions-and-amazon-sqs-html)
