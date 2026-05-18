---
title: "3.C57 Lob：自家 fork @lob/sqs-consumer 修 FIFO bug"
date: 2026-05-18
description: "Lob 原用 bbc/sqs-consumer 鎖 SDK v2、fork 出 @lob/sqs-consumer 支援 SDK v3 + TypeScript + 修 FIFO bug。"
weight: 57
tags: ["backend", "message-queue", "case-study", "aws-sqs"]
---

這個案例的核心責任是說明真實 production library 維護成本、FIFO consumer 的隱性 bug。

## 觀察

Lob（programmatic mail API）原本用 bbc/sqs-consumer 但被鎖在 AWS SDK v2。他們 fork 出 @lob/sqs-consumer：支援 SDK v3（模組化 import 縮 bundle、TypeScript 一級支援、async/await）、修正原 library 對 FIFO queue 的 bug。SQS 用在 Lob API 跟其他內部 service。

## 判讀

不能只靠 SDK 原生 API、SDK 升級會逼出 library 維護議題。揭露「FIFO queue 跟 standard queue 的 client 行為差異」是 library 層的隱性 bug 來源。

## 對應大綱

SQS 進階主題：Standard vs FIFO / Long polling / Client library 維護。

## 下一步路由

回 [SQS vendor 頁](/backend/03-message-queue/vendors/aws-sqs/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [@lob/sqs-consumer](https://www.lob.com/blog/lob-sqs-consumer)
