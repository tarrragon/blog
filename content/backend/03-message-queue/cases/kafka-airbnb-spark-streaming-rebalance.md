---
title: "3.C15 Airbnb：Spark Streaming Kafka reader rebalance"
date: 2026-05-18
description: "Airbnb logging pipeline 解 partition-task 1:1 造成的 data skew、catch-up 4 小時 lag 要再花 4 小時的反效率。"
weight: 15
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 stream processor 與 Kafka partition 數的緊耦合是 production scaling 瓶頸。

## 觀察

Airbnb logging pipeline 跨多個 topic、event size 從幾百 bytes 到幾百 KB、QPS 跨數個量級差異、Spark 一個 partition 對一個 task 造成 data skew、catch-up 一個 4 小時 lag 要再花 4 小時。

## 判讀

自建 balanced Spark Kafka reader、把 parallelism 從 partition 數解耦、按 event volume × size 重新分派 work。揭露 partition 數不該等同 consumer parallelism、要看 event 形狀。

## 對應大綱

Kafka 進階主題：Consumer 設計 / consumer lag / rebalance / partition + consumer group。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Scaling Spark Streaming for Logging Event Ingestion](https://medium.com/airbnb-engineering/scaling-spark-streaming-for-logging-event-ingestion-4a03141d135d)
