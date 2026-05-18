---
title: "3.C47 PHP 微服務：Redis Streams + S3 hybrid storage"
date: 2026-05-18
description: "PHP 雙微服務通訊、Kafka 在 PHP 生態工具薄弱、用 Redis Streams + payload compression + S3 hybrid 處理大訊息。"
weight: 47
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個案例的核心責任是說明 in-memory 訊息的 payload 限制要靠 hybrid storage 解決。

## 觀察

PHP 雙微服務之間的可靠通訊、Kafka 在 PHP 生態工具薄弱、團隊無 Kafka 經驗、production 跑數月後寫此文；明確覆蓋 XADD / XREADGROUP / consumer group / MAXLEN / MINID / XDEL / XACK / XACKDEL（Redis 8.2+）/ XTRIM。

## 判讀

揭露 in-memory 訊息的 payload 限制：用 payload compression + S3 hybrid storage（大 payload 存 S3、stream 只放 reference）；用 MAXLEN/MINID 控制 stream 成長。揭露 broker 選型常被「語言生態 client 品質」主導、不是純技術 feature。**注意**：作者是個人工程師、production 經驗但非知名公司。

## 對應大綱

Redis Streams 進階主題：XADD/XREAD/XREADGROUP 操作 / Retention (MAXLEN/MINID) / Memory + retention 取捨。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [3.C16 Robinhood Faust](/backend/03-message-queue/cases/kafka-robinhood-faust-python-streaming/)（語言生態對照）。

## 引用源

- [Beyond the Hype: Why We Chose Redis Streams Over Kafka for Our Microservices](https://dev.to/mtk3d/beyond-the-hype-why-we-chose-redis-streams-over-kafka-for-our-microservices-dmc)
