---
title: "3.C16 Robinhood：Faust Python stream processing"
date: 2026-05-18
description: "Robinhood 每天 billions of events、Python 團隊不想用 JVM 生態、把 Kafka Streams 移植到 Python。"
weight: 16
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明語言生態與 stream framework 的選型張力。

## 觀察

Robinhood 每天處理 billions of events / TB 資料、用於 risk signal、order quality、market data、fraud detection；team 多為 Python、不想用 JVM 生態。

## 判讀

把 Kafka Streams 的 stateful streaming 模式（topology、tables、windowing）移植到 Python library 形式、不需要 Yarn / Mesos resource manager。揭露 stream processing framework 選型常被語言生態主導、不是技術 feature。

## 對應大綱

Kafka 進階主題：跨語言 client / Streams framework / stream processing on Kafka。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Faust: Stream Processing for Python](https://medium.com/robinhood-engineering/faust-stream-processing-for-python-a66d3a51212d)
