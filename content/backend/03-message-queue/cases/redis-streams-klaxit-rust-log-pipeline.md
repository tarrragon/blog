---
title: "3.C45 Klaxit：Rust + Redis Streams 處理 Heroku Logplex"
date: 2026-05-18
description: "Klaxit carpool 用 Redis Streams 處理 Heroku Logplex 匯流、自動偵測修復平台 perf 問題、6 個月 production Rust。"
weight: 45
tags: ["backend", "message-queue", "case-study", "redis-streams"]
---

這個案例的核心責任是說明 Redis Streams 在高吞吐 log ingestion 的 consumer group 分流。

## 觀察

Klaxit 用 Redis Streams 處理 Heroku Logplex 匯流的 log、自動偵測並修復 Heroku 平台層 perf 問題（在使用者察覺前）；正式 production 跑超過 6 個月、是團隊第一個 Rust project。

## 判讀

揭露 high-throughput log ingestion 對 Redis Streams 的壓力：用 consumer group 分流到多個 Rust worker、需要長時間穩定運轉。揭露 client library 品質決定 Redis Streams 在小眾語言（Rust）的可行性。

## 對應大綱

Redis Streams 進階主題：XADD / XREAD / XREADGROUP 操作 / Consumer group + PEL。

## 下一步路由

回 [Redis Streams vendor 頁](/backend/03-message-queue/vendors/redis-streams/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [Consuming High-Throughput Redis Streams with Rust](https://dev.to/goodtouch/consuming-high-throughput-redis-streams-with-rust-580c)
