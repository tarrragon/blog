---
title: "3.C43 Arcjet：Redis Streams 取代 Kafka 省 6 位數 $"
date: 2026-05-18
description: "Arcjet security 平台、Kafka managed 6 位數 $/yr、用 Redis Streams 約 $1k/yr、自寫 Janitor 監控 retention。"
weight: 43
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個案例的核心責任是說明 Redis Streams 在中小規模可以是 Kafka 的成本替代、但需要自寫運維工具。

## 觀察

Arcjet 的 security/bot detection 平台、需要 low-latency 請求處理、但 Kafka 管理難度高且 managed offering 要六位數年費、他們現有 Redis cache 層升級成 Streams 後總成本約 $1k/yr。

## 判讀

揭露 Redis Streams 沒有自動 retention：自寫 Janitor process 監測 stream length + consumer group state、根據 ~100 msgs/min 的實際處理速度 selectively trim、計畫把 consumer group 進度持久化到 Redis 以做精確 MINID 截斷。揭露「Redis Streams 可以取代 Kafka」的前提是接受自寫運維工具的成本。

## 對應大綱

Redis Streams 進階主題：Retention (MAXLEN/MINID) / Memory + retention 取捨。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)（成本對照）。

## 引用源

- [Replacing Kafka with Redis Streams](https://blog.arcjet.com/replacing-kafka-with-redis-streams/)
