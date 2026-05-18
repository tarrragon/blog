---
title: "3.C13 Shopify：Debezium CDC over sharded MySQL"
date: 2026-05-18
description: "Shopify 100+ MySQL shard、150 Debezium connector、Black Friday 100K records/sec P99 < 10s。"
weight: 13
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個案例的核心責任是說明 sharded monolith 上 Debezium 的真實 production 工程議題。

## 觀察

Shopify 從 query-based Longboat 換到 log-based CDC、100+ MySQL shard、~150 個 Debezium connector 跑在 12 個 Kubernetes pod、Black Friday peak 100K records/sec、P99 latency < 10s。

## 判讀

自家工程師 upstream contribute「lock-free snapshot」到 Debezium、解決 snapshot 鎖 read replica 數小時的問題；oversized record（> 1MB）走 GCS pointer。揭露 CDC pipeline 的真實壓力來自 snapshot 與 oversized payload、不是穩態複製。

## 對應大綱

Kafka 進階主題：Kafka Connect / CDC / Schema evolution。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。

## 引用源

- [Capturing Every Change From Shopify's Sharded Monolith](https://shopify.engineering/capturing-every-change-shopify-sharded-monolith)
