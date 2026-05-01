---
title: "訊息佇列 Vendor 清單"
date: 2026-05-01
description: "後端訊息佇列實作時的常用選擇，預先建立引用路徑"
weight: 90
---

本清單列出 backend 服務實作會選用的 message queue / broker vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架。

## T1 vendor

- [rabbitmq](/backend/03-message-queue/vendors/rabbitmq/) — classic broker、routing 為主
- [kafka](/backend/03-message-queue/vendors/kafka/) — event streaming 主流
- [nats](/backend/03-message-queue/vendors/nats/) — lightweight、JetStream 加持久化
- [redis-streams](/backend/03-message-queue/vendors/redis-streams/) — Redis 生態內的 streams（住於 02 的 redis 引用）
- [aws-sqs](/backend/03-message-queue/vendors/aws-sqs/) — managed queue、無 ordering
- [google-pubsub](/backend/03-message-queue/vendors/google-pubsub/) — managed pub/sub

## 後續擴充

- T2 候選：pulsar、aws-kinesis、azure-service-bus、temporal（workflow engine）
- T3 候選：activemq、nsq、zeromq
