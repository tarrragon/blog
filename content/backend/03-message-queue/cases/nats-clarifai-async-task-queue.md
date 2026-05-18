---
title: "3.C38 Clarifai：NATS Streaming ML 平台非同步任務"
date: 2026-05-18
description: "Clarifai custom model 訓練、rolling deploy 掉訊息、改 NATS Streaming queue group、3 週遷移 1 服務、5 月 5 服務、每日 100k+ 訊息 100% uptime。"
weight: 38
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明 NATS Streaming（JetStream 前身）的 queue group + at-least-once 在 ML worker pool 的角色。

## 觀察

Clarifai 做 custom model 訓練、任務從幾秒到幾分鐘、原本同步呼叫遇到 rolling deployment 會掉訊息。三週內把一個服務遷到 NATS、5 個月內擴展到 5 個服務、每日 100k+ 訊息、100% uptime。

## 判讀

用 NATS Streaming 的 at-least-once delivery + queue subscription group 做 worker pool、每個微服務連到三個獨立 NATS Streaming 實例做 fanout 隔離。揭露 ML 任務的長尾處理時間特別需要 at-least-once + redelivery、不能容忍 rolling deploy 掉訊息。

## 對應大綱

NATS 進階主題：JetStream consumer 設計（NATS Streaming 是前身）/ Queue groups。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [How Clarifai Uses NATS and Kubernetes for Machine Learning](https://nats.io/blog/how-clarifai-uses-nats-and-kubernetes-for-machine-learning/)
