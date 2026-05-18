---
title: "3.C25 Indeed：Delay queue + DLQ 三層 escalation"
date: 2026-05-18
description: "Indeed 每天 35M+ 職缺、設計 Requeue → Delay queue → DLQ 三層 escalation 避開 head-of-line blocking。"
weight: 25
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 retry 不該直接 requeue 到 head、要走分層延遲 + DLQ。

## 觀察

Indeed 每天 35M+ 職缺、原 architecture 在 requeue 失敗訊息時把它推到 queue head、阻塞後續訊息。

## 判讀

設計 Requeue → Delay queue → Dead Letter Queue 三層 escalation。Retry n 次後進延遲隊列、再 m 次才進 DLQ。揭露 retry 策略要跟 queue 拓樸結合設計、不是純 client 端 backoff。

## 對應大綱

RabbitMQ 進階主題：Dead-letter exchange（DLX）/ retry 策略。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.2 durable queue](/backend/03-message-queue/durable-queue/)。

## 引用源

- [Delaying Messages with RabbitMQ at Indeed](https://engineering.indeedblog.com/blog/2017/06/delaying-messages/)
- [Get a Job 35 Million Times a Day Using RabbitMQ (talk)](https://engineering.indeedblog.com/talks/get-job-35-million-times-day-using-rabbitmq/)
