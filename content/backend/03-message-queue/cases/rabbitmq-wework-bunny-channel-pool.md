---
title: "3.C29 WeWork：Bunny + Puma 多執行緒 channel pool"
date: 2026-05-18
description: "WeWork 從 Unicorn 切到 Puma 後遇 ConnectionClosedError、根因是 AMQP channel 跨執行緒共用、改用 connection_pool 管理。"
weight: 29
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 AMQP client 的 connection / channel 邊界跟執行緒模型緊密耦合。

## 觀察

從 Unicorn 切到 Puma 後遇到 `ConnectionClosedError`、根因是快取 Bunny channel 在多執行緒間共享。

## 判讀

AMQP channel 不應跨執行緒共用、改用 `connection_pool` gem 管理 channel pool。揭露 AMQP 不是 stateless HTTP-style client、channel 是 statefull 物件、多 thread 模型要特別處理。

## 對應大綱

RabbitMQ 進階主題：Prefetch + consumer 併發（client library 層的 connection / channel 邊界）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Bunny Threads in Puma at WeWork](https://wework.github.io/ruby/rails/bunny/rabbitmq/threads/concurrency/puma/errors/2015/11/12/bunny-threads/)
