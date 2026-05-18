---
title: "3.C65 Mercari LINE：Pull subscription 對齊外部 RPS"
date: 2026-05-18
description: "Mercari LINE webhook 轉 Pub/Sub、worker pull subscription 精確控制 RPS、應 LINE API 限制。"
weight: 65
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明「下游有 RPS 限制」是 Pull subscription 勝過 push 的典型情境。

## 觀察

Braze webhook 進來後轉成 Pub/Sub event、下游 LINE worker pull subscription「精確控制每秒處理訊息數」、因為外部 LINE API 有 RPS 限制。

## 判讀

push 會把流量瞬間打到 endpoint、pull 可由 consumer 自行 throttle。揭露 push vs pull 不是「實作偏好」、是「下游能否接受 push 衝擊」的判讀。

## 對應大綱

Pub/Sub 進階主題：Push vs Pull subscription。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C58 Twilio webhook buffer](/backend/03-message-queue/cases/sqs-twilio-webhook-buffer/)（webhook + buffer 對照）。

## 引用源

- [Flow Control Challenges in Mercari's LINE Integration](https://engineering.mercari.com/en/blog/entry/20231212-flow-control-challenges-in-mercaris-line-integration/)
