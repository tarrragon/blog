---
title: "3.C64 Mercari Item Feed：DLT 防 poison message 阻塞"
date: 2026-05-18
description: "Mercari 商品 feed 同步、ack 整批 / nack 重送、重試多次仍失敗送 DLT、topic 同時當 load-leveling buffer。"
weight: 64
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是說明 DLT 在防止 poison message 阻塞 pipeline 的角色。

## 觀察

商品 feed 同步用 pull subscription + 自家 batch requester、成功時 ack 整批、失敗時 nack 讓 Pub/Sub 重送；重試多次仍失敗則送 Dead-letter topic、後續訊息優先處理；topic 同時當突發流量的緩衝。

## 判讀

直接示範 DLT 在防止 poison message 阻塞 pipeline 的角色、以及把 topic 當 load-leveling queue 的設計。揭露「topic = buffer + dispatch」雙重角色。

## 對應大綱

Pub/Sub 進階主題：Dead-letter topic / Push vs Pull subscription。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C56 PostNL EBE](/backend/03-message-queue/cases/sqs-postnl-mission-critical-ebe/)（DLQ 設計對照）。

## 引用源

- [Mercari's Seamless Item Feed Integration](https://engineering.mercari.com/en/blog/entry/20241212-mercaris-seamless-item-feed-integration-bridging-the-gap-between-systems/)
