---
title: "3.C68 Wix：Pub/Sub decouple + Dataflow + BQ archive"
date: 2026-05-18
description: "Wix App Engine 收 clickstream 進 Pub/Sub、Dataflow 進 Datastore < 100ms、BigQuery 並行存 raw recovery。"
weight: 68
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是「Pub/Sub buffer + Dataflow stream processor + BQ archive」的教科書組合。

## 觀察

App Engine 收 clickstream → 進 Cloud Pub/Sub queue、再由 Dataflow streaming 處理進 Datastore、dashboard 端到端 latency < 100ms；BigQuery 並行存 raw data 做 recovery。

## 判讀

「Pub/Sub 當 decouple buffer + Dataflow 當 stream processor + BigQuery 當 raw archive」的 textbook 組合、可作為 BigQuery subscription 出現前的對比 case（為什麼後來原生 BQ subscription 能省掉 Dataflow 中介層）。

## 對應大綱

Pub/Sub 進階主題：BigQuery subscription / Push vs Pull。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C67 Niantic Pokémon GO](/backend/03-message-queue/cases/pubsub-niantic-pokemon-go-telemetry/)（同類組合）。

## 引用源

- [Wix Customer Story](https://cloud.google.com/customers/wix)
