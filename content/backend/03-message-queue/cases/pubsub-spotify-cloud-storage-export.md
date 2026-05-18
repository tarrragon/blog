---
title: "3.C62 Spotify：Pub/Sub → GCS reliable export"
date: 2026-05-18
description: "Spotify 用 Oldest Unacknowledged Message metric 判斷 hourly bucket 何時可安全關閉、ack 綁定下游 commit。"
weight: 62
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明 ack 是 end-to-end commit 信號、不是 buffer-flush 信號。

## 觀察

Consumer 只在下游 Completionist 回 200 OK 才 ack 回 Pub/Sub、並用「Oldest Unacknowledged Message」metric 判斷 hourly bucket 何時可安全關閉；ack semantics 直接綁定下游 commit。

## 判讀

ack 是 end-to-end commit 信號、不是 buffer-flush 信號。揭露為什麼後來原生 GCS subscription 有價值（Spotify 早期沒有原生、自建管線）。

## 對應大綱

Pub/Sub 進階主題：Ack deadline / Cloud Storage subscription（早期無原生、自建對照）。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.7 event contract / replay boundary](/backend/03-message-queue/event-contract-replay-boundary/)。

## 引用源

- [Reliable Export of Cloud Pub/Sub Streams to Cloud Storage](https://engineering.atspotify.com/2017/04/reliable-export-of-cloud-pubsub-streams-to-cloud-storage)
