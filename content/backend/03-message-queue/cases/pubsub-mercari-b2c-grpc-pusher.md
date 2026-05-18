---
title: "3.C66 Mercari B2C：自建 PubSub gRPC Pusher"
date: 2026-05-18
description: "Mercari 全球商品同步、原生 HTTP push 在「長 job + 高吞吐 + 動態 RPS」場景受限、自建 gRPC 版 push。"
weight: 66
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明原生 push subscription 在特定場景的限制、逼出自建層的工程選擇。

## 觀察

全球商品同步系統、自建 in-house「PubSub gRPC Pusher」（Pub/Sub 的 gRPC 版 push subscription）解決高吞吐 / 長 job / 彈性 RPS；同時用 message ID 做去重、timestamp 驗證解決重複 + 亂序。

## 判讀

原生 HTTP push subscription 在「長 job + 高吞吐 + 動態 rate」場景的限制、逼出自建層的工程選擇。揭露 managed broker 的「原生功能」不是所有場景的終點。

## 對應大綱

Pub/Sub 進階主題：Push vs Pull subscription / Ordering key（亂序的 application-level 處理）。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.4 consumer 設計](/backend/03-message-queue/consumer-design/)。

## 引用源

- [From Local to Global: Building Seamless B2C Product Integration at Mercari](https://engineering.mercari.com/en/blog/entry/20251009-from-local-to-global-building-seamless-b2c-product-integration-at-mercari/)
