---
title: "3.1 broker 基礎與投遞模型"
date: 2026-04-23
description: "先理解 broker、queue、consumer 與 delivery semantics"
weight: 1
---

這一章先建立訊息佇列的基本模型，後面的 durable queue、outbox 與 consumer 設計都會建立在這些語意上。

## 大綱

- broker 與 queue 的角色
- push 與 pull 模型
- at-most-once、at-least-once、exactly-once 的實務差異
- consumer 與 ack/nack 的基本流程

## 相關語言章節

- [Go：channel](../../go/04-concurrency/channel/)
- [Go 進階：非阻塞送出與事件丟棄策略](../../go-advanced/01-concurrency-patterns/non-blocking-send/)
