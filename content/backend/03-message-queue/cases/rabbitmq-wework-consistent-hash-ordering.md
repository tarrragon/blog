---
title: "3.C28 WeWork：Consistent hash exchange 保證帳戶順序"
date: 2026-05-18
description: "WeWork 固定數量 queue + account ID hash 路由、每 queue 一個 worker + exclusive consumer 保 partition-level ordering。"
weight: 28
tags: ["backend", "message-queue", "case-study", "rabbitmq"]
---

這個案例的核心責任是說明 RabbitMQ 也能做「per-key ordering」、用 consistent hash exchange 模擬 partition。

## 觀察

訊息順序對某些業務流程關鍵、但全局排序代價高。WeWork 採固定數量 queue + 用 account ID hash 路由到特定 queue。

## 判讀

每個 queue 一個 SideKiq worker + exclusive consumer 保證單帳戶順序。文後發現 RabbitMQ Consistent Hashing plugin 已內建類似機制（類似 Kafka 分區）。揭露 partition-level ordering 不是 Kafka 專屬、在 broker model 可用 hash exchange 達成。

## 對應大綱

RabbitMQ 進階主題：Exchange types / Prefetch + consumer 併發（partition-level ordering 模式）。

## 下一步路由

回 [RabbitMQ vendor 頁](/backend/03-message-queue/vendors/rabbitmq/) 與 [Kafka vendor 頁](/backend/03-message-queue/vendors/kafka/)（partition + key 對照）。

## 引用源

- [WeWork's "Good Enough" Order Guarantee](https://www.cloudamqp.com/blog/weworks-good-enough-order%20guarantee.html)
