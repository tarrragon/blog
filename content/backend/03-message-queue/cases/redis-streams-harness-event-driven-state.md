---
title: "3.C44 Harness：CD 微服務 async state transfer"
date: 2026-05-18
description: "Harness CD 平台用 Redis Streams 解 brittle HTTP、揭露監控缺口 / MAXLEN truncation / head-of-line blocking 三類問題。"
weight: 44
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個案例的核心責任是說明 Redis Streams 在 production 落地的三類經常性議題。

## 觀察

Harness 為 CD 微服務之間的 async state transfer 採用 Redis Streams、避開「每個 service 都要知道怎麼跟其他 service 講話」的 brittle HTTP 模式；初始規模 a few thousand msgs/min、Kafka 在此規模 overkill、又能複用已存在的 Redis 基建。

## 判讀

落地後揭露三類問題：監控缺口（自寫 app 追 consumer lag）、需要主動 MAXLEN truncation、head-of-line blocking 要用 XAUTOCLAIM 重派並設計 redelivery 策略。揭露「Redis Streams 適合中小規模」這個聲明、實際包含三件 production work。

## 對應大綱

Redis Streams 進階主題：Consumer group + PEL / XCLAIM + 失敗接管 / Memory + retention 取捨。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [3.5 紅隊章](/backend/03-message-queue/red-team-delivery-layer/)。

## 引用源

- [Event-Driven Architecture with Redis Streams](https://www.harness.io/blog/event-driven-architecture-redis-streams)
