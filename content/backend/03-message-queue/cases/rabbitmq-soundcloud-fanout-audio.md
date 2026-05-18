---
title: "3.C24 SoundCloud：AMQP fan-out 音訊處理 pipeline"
date: 2026-05-18
description: "SoundCloud 每秒 20-30K persistent message、不同處理類型分開隊列、各自獨立 scale。"
weight: 24
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 fan-out 處理 pipeline 該按處理類型拆隊列、不該共用 queue。

## 觀察

上傳音訊後用 RabbitMQ 觸發 transcode + 波形圖 + follower 通知。當 Skrillex 等大號上傳時、要避免同步寫 Cassandra 千萬次。每秒 20-30,000 條 persistent message。

## 判讀

不同處理類型分開隊列、各自獨立 scale。揭露 fan-out 不是「broadcast 同一份工作」、而是「同事件觸發多種獨立 pipeline」、每種 pipeline 的 throughput / latency 要求不同。

## 對應大綱

RabbitMQ 進階主題：Prefetch + consumer 併發 / classic queue vs Streams（log fan-out 場景）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Scaling with RabbitMQ at SoundCloud (VMware Tanzu)](https://blogs.vmware.com/tanzu/scaling-with-rabbitmq-soundcloud)
- [AMQP at SoundCloud (InfoQ)](https://www.infoq.com/presentations/amqp-soundcloud/)
