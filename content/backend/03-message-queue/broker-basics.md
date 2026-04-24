---
title: "3.1 broker 基礎與投遞模型"
date: 2026-04-23
description: "先理解 broker、queue、consumer 與 delivery semantics"
weight: 1
---

這一章先建立訊息佇列的基本模型，後面的 [durable queue](../../knowledge-cards/durable-queue/)、outbox 與 [consumer](../../knowledge-cards/consumer/) 設計都會建立在這些語意上。

## 大綱

- [broker](../../knowledge-cards/broker/) 與 queue 的角色
- push 與 pull 模型
- at-most-once、at-least-once、exactly-once 的實務差異
- consumer 與 [ack/nack](../../knowledge-cards/ack-nack/) 的基本流程
