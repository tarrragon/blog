---
title: "3.C67 Niantic Pokémon GO：Pub/Sub 當 telemetry ingest"
date: 2026-05-18
description: "Pokémon GO frontend publish 玩家事件、~1M TPS、Pub/Sub elastic buffer、下游 BigQuery streaming。"
weight: 67
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明大規模遊戲 telemetry 的 ingest backbone 設計。

## 觀察

Pokémon GO frontend 把玩家事件 publish 到 Pub/Sub topic 餵分析 pipeline、再進 BigQuery streaming；高峰 ~1M TPS、Pub/Sub 是 managed service 因此 SRE 維運成本低。

## 判讀

Pub/Sub 在 publisher 突發流量下作為 elastic buffer、下游 BigQuery streaming 是常見組合。揭露「managed service 的 SRE 成本」是大規模遊戲場景的關鍵選型理由。

## 對應大綱

Pub/Sub 進階主題：BigQuery subscription（原生 BQ subscription 出現前的 Dataflow pattern）。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C68 Wix clickstream](/backend/03-message-queue/cases/pubsub-wix-clickstream-dashboard/)（同類組合）。

## 引用源

- [How Pokémon GO Scales to Millions of Requests](https://cloud.google.com/blog/topics/developers-practitioners/how-pok%C3%A9mon-go-scales-millions-requests)
