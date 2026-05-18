---
title: "3.C20 Spotify：Event Delivery 從 Kafka 遷出（反例）"
date: 2026-05-18
description: "Spotify Kafka 0.7 MirrorMaker best-effort 會掉資料但回報成功、broker restart 後 producer 無法恢復、決定遷到 GCP Pub/Sub。"
weight: 20
tags: ["backend", "message-queue", "case-study", "kafka"]
---

這個反例的核心責任是說明 Kafka 早期 release 在 producer 可靠性與 mirror correctness 的硬限制、揭露「何時 Kafka 不該選」。

## 觀察

Spotify 跨 5 個 datacenter 跑 Kafka 0.7、production peak 700K events/sec、testing 2M events/sec；2016 年決定遷到 GCP Pub/Sub、不升級到 Kafka 0.8。

## 判讀

Kafka 0.8 的 MirrorMaker 在 best-effort mode 會掉資料但回報成功；broker restart 後 producer 進入無法自動恢復的狀態。揭露「broker 可靠性」是版本特性、不是 Kafka 的 invariant；early adopter 的版本特定故障值得記入決策歷史。

## 對應大綱

Kafka 進階主題：cross-region MirrorMaker / replication 失敗模式 / producer 可靠性。

## 下一步路由

回 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/) 與 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/)。

## 引用源

- [Spotify's Event Delivery — The Road to the Cloud (Part II)](https://engineering.atspotify.com/2017/03/spotifys-event-delivery-the-road-to-the-cloud-part-ii)
