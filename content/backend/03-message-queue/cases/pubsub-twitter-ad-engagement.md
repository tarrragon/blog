---
title: "3.C69 Twitter Ad Engagement：把 stream 切成多 topic 做 partition"
date: 2026-05-18
description: "Twitter 把 80K msg/s stream 切成 6 個 topic 做 partition、Avro schema、Beam/Dataflow → Bigtable/BQ。"
weight: 69
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明 Pub/Sub 沒有 Kafka-style partition 概念下的應對策略。

## 觀察

Twitter 把 on-prem 服務的 Avro-formatted 訊息 push 到 Pub/Sub（兩條 stream、較不關鍵但量大的那條 ~80K msg/s 切成 6 個 topic）、下游用 Dataflow + Beam 處理進 Bigtable / BigQuery。

## 判讀

「把單一 high-volume stream 切成多 topic 做 partition」是 Pub/Sub 沒有 Kafka-style partition 概念下的應對策略。揭露 Pub/Sub 跟 Kafka 的選型差異不是 feature parity、是不同的擴張模型。

## 對應大綱

Pub/Sub 進階主題：Schema enforcement（Avro 是常見 schema 候選）/ Ordering key（topic 切分 vs ordering key 的取捨）。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)（partition 對照）。

## 引用源

- [Modernizing Twitter's Ad Engagement Analytics Platform](https://cloud.google.com/blog/products/data-analytics/modernizing-twitters-ad-engagement-analytics-platform)
