---
title: "3.C60 Spotify：Event Delivery 從 Kafka 遷到 Pub/Sub"
date: 2026-05-18
description: "Spotify 全球 event delivery 從 Kafka 遷到 Pub/Sub、~2500 VM、Q1 2019 8M events/s、350TB/day raw、自建 dedup。"
weight: 60
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明大規模 Pub/Sub pull subscription 的工程現實：at-least-once + 自建 dedup。

## 觀察

Spotify 把全球 event delivery 系統從 Kafka 完整遷到 Cloud Pub/Sub、每個 event type 一個 topic、~15 個 microservice 跑在 ~2500 VM 上、Q1 2019 高峰 8M events/s、每日 350 TB raw event 流量。

## 判讀

「at-least-once 加上自建 deduplication 層」是大規模 Pub/Sub pull subscription 的工程現實。揭露 Pub/Sub 沒有 exactly-once（早期）、應用層去重不可省。

## 對應大綱

Pub/Sub 進階主題：Pub/Sub vs Pub/Sub Lite 取捨 / Push vs Pull subscription / Ack deadline。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C20 Spotify 遷出 Kafka](/backend/03-message-queue/cases/kafka-spotify-event-delivery-exodus/)（遷移源頭）。

## 引用源

- [Spotify's Event Delivery — Life in the Cloud](https://engineering.atspotify.com/2019/11/spotifys-event-delivery-life-in-the-cloud)
