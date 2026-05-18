---
title: "3.C42 Bitso：Reliable Redis Streams 抽象 + 自建 DLQ"
date: 2026-05-18
description: "Bitso 加密交易所、千 msg/sec/stream + 亞毫秒延遲、自建 Reliable Streams 封裝 PEL + retry + DLQ、idempotent processing。"
weight: 42
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個案例的核心責任是說明 Redis Streams 沒有原生 DLQ、要在 application 層自建抽象。

## 觀察

Bitso 的 Order Engine 微服務需要 thousands of messages/sec/stream + 亞毫秒延遲、撐住 BTC 價格暴動的流量尖峰；先後評估 Kafka（latency）跟 SQS（vendor lock-in + latency）後選 Redis Streams、團隊本來就熟 Redis、已在 mission-critical service 跑超過半年。

## 判讀

自建 "Reliable Redis Streams" 抽象層（StreamRedisOperations adapter / ReliableStream interface / MessageReadingLoop）封裝 readMessages + readPendingMessages、加上 Redis Streams 沒有原生支援的 DLQ（N 次 retry 後路由）、走 idempotent processing 接受重複勝過遺失。揭露 Redis Streams 是「資料結構」、不是「broker 系統」、可靠性責任在 application 層。

## 對應大綱

Redis Streams 進階主題：Consumer group + PEL / XCLAIM + 失敗接管 / Sentinel + Cluster 可靠性。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [The Redis Streams We Have Known and Loved](https://medium.com/bitso-engineering/the-redis-streams-we-have-known-and-loved-e9e596d49a22)
