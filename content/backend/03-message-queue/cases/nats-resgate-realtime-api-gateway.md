---
title: "3.C40 Resgate：WebSocket-to-NATS realtime API gateway"
date: 2026-05-18
description: "Resgate 把 NATS subject 暴露成 REST + WebSocket、subject 階層當 schema、event 延遲 < 1ms、純 Core NATS。"
weight: 40
tags: ["backend", "message-queue", "case-study", "nats"]
---

這個案例的核心責任是說明「subject hierarchy 即 access control 邊界」的設計範例。

## 觀察

Resgate 把 NATS subject 暴露成 REST + WebSocket、客戶端跨多 Resgate 實例自動同步狀態、事件延遲 < 1ms。需要同時支援 pub-sub 跟 request-reply、選 NATS 因為「performance、simplicity、兩種模式都原生支援」。

## 判讀

subject 設計遵循 `get.{service}.{resource}` / `event.{service}.{resource}.{event-type}` 的命名規約、是「subject 階層當 schema」的典型範例。揭露 subject 命名是 NATS 的 API contract 起點、不是隨意命名。

## 對應大綱

NATS 進階主題：Request/Reply pattern / Subject-based ACL + 多租戶（subject hierarchy 即 access control 邊界）/ Core NATS vs JetStream（純 Core）。

## 下一步路由

回 [NATS vendor 頁](/backend/03-message-queue/vendors/nats/) 與 [3.C26 GoCardless Hutch routing key](/backend/03-message-queue/cases/rabbitmq-gocardless-hutch-service-mesh/)（命名規約對照）。

## 引用源

- [Introducing Resgate](https://resgate.io/blog/introducing-resgate/)
