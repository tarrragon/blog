---
title: "3.C59 Rapid7：SQS 100 億 message/day 規模"
date: 2026-05-18
description: "Rapid7 公開引述：SQS 撐 10s of billions of messages per day、是架構關鍵元件、scale 量級的具體參考。"
weight: 59
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是建立 SQS 在 10 billion+/day 規模下的成本結構與量級參考點。

## 觀察

Rapid7 Platform Software Architect 公開引述：「SQS 是我們架構的關鍵元件、讓我們 scale 到處理 10s of billions of messages per day。」是 AWS 官方文中具名客戶 quote、非 marketing 概括。

## 判讀

SQS 在百億訊息/日規模下仍可用、是 scale 的具體量級參考點。揭露 SQS request-based 計費在這個規模下、cost 模型該被認真評估。

## 對應大綱

SQS 進階主題：Cost 模型 / Standard queue。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [0.6 成本取捨](/backend/00-service-selection/cost-risk-tradeoffs/)。

## 引用源

- [Amazon SQS — 15 Years and Still Queueing](https://aws.amazon.com/blogs/aws/amazon-sqs-15-years-and-still-queueing/)
