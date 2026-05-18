---
title: "3.C32 LoyaltyLion：監控數千 RabbitMQ queue"
date: 2026-05-18
description: "LoyaltyLion 跑數千 queue、用 rabbitmqctl + statsd 推 Datadog、揭露大規模 queue 拓樸下原生 plugin API 不夠用。"
weight: 32
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明大規模 queue topology 的監控議題超出 Management plugin 能力範圍。

## 觀察

LoyaltyLion 跑數千個 RabbitMQ queue、用 rabbitmqctl 跑 recurring script 抓 queue 資訊、透過 statsd 送到 Datadog。

## 判讀

大規模 queue 拓撲下管理 plugin API 不夠用、需自寫採集腳本。揭露 queue 數量上萬時、原生 monitoring 介面（HTTP API、Management UI）會變成瓶頸、需要 metrics agent 模式。

## 對應大綱

RabbitMQ 進階主題：Prefetch + consumer 併發（大規模 queue topology 的監控議題）/ RabbitMQ Cluster Operator（運維邊界）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [4 觀測模組](/backend/04-observability/)。

## 引用源

- [Monitoring Thousands of RabbitMQ Queues with Datadog](https://engineering.loyaltylion.com/monitoring-thousands-of-rabbitmq-queues-with-datadog-d3168c088ea6)
