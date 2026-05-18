---
title: "3.C50 Capital One：Visibility timeout 設計與 Lambda event source"
date: 2026-05-18
description: "Capital One tech blog 講 SQS + Lambda：visibility timeout 應略高於最大處理時間、Lambda 初 5 個 long polling、可擴 60/min。"
weight: 50
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明 visibility timeout 在 Lambda event source 的雙邊風險。

## 觀察

Capital One 官方 tech blog 講解 SQS + Lambda event source mapping、明示 visibility timeout 應「比最大處理時間略高」、Lambda 初始開 5 個 long polling connection、可擴張至 60 instances/min、上限 1000 並行 batch。

## 判讀

揭露 visibility timeout 太短會重複處理、太長會延遲 retry 的雙邊風險。揭露 Lambda 跟 SQS 的 scaling 不是線性、有 ramp-up 上限。

## 對應大綱

SQS 進階主題：Visibility timeout + in-flight / SQS + Lambda event source。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.C49 Airbnb Inspekt](/backend/03-message-queue/cases/sqs-airbnb-inspekt-data-protection/)（visibility timeout 對照）。

## 引用源

- [Using AWS Solutions for Event-Driven Serverless Architectures](https://www.capitalone.com/tech/cloud/using-aws-solutions-for-event-driven-serverless-architectures/)
