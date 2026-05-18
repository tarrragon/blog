---
title: "3.C46 Learning.com：Redis 事件源退場（反例）"
date: 2026-05-18
description: "Learning.com 把 microservice event store 放 Redis、1 年累積 GB/週、AOF+EBS 變 latency 痛點、退到 PostgreSQL。"
weight: 46
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個反例的核心責任是說明 Redis 不適合長期事件儲存、揭露「Redis-as-event-store」的退場路徑。

## 觀察

Learning.com 把 microservice 之間的 event store 放 Redis 上、一年內累積到 GB/週的 memory 成長、AOF fsync + EBS 磁碟 I/O 變成 latency 痛點。

## 判讀

揭露「Redis 不適合長期事件儲存」的退場路徑：event 移到 PostgreSQL、Redis 留做訊息佇列 + snapshot；中途靠 syncTimeout 調整、提升 IOPS、調整 AOF fsync 緩解。揭露 broker 選型要看「長期存儲是 source-of-truth 還是 transient」。**注意**：此文討論的是 Redis-as-event-store 整體、Streams 是其中一塊、引用時要小心區分。

## 對應大綱

Redis Streams 進階主題：Memory + retention 取捨 / Sentinel + Cluster 可靠性（持久化選型）。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。

## 引用源

- [A Year with Redis Event Sourcing - Lessons Learned](https://medium.com/lcom-techblog/a-year-with-redis-event-sourcing-lessons-learned-6736068e17cc)
