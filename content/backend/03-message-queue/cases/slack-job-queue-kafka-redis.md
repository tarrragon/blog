---
title: "3.C5 Slack：Job Queue 演進到 Kafka + Redis"
date: 2026-05-07
description: "背景工作通道在成長期如何從單一路徑演進成組合式架構。"
weight: 5
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是說明工作佇列轉換常是拓樸重整，而不是單點替換。

## 觀察

Slack 在 job queue 擴展中使用 Kafka 與 Redis 分工，處理吞吐與即時性需求。

## 判讀

當背景工作同時要高吞吐與快速反應，單一通道模型通常會變成瓶頸。

## 策略

1. 把不同工作類型切到不同傳遞路徑。
2. 分別治理持久性與即時性目標。
3. 以 lag、重試與失敗重播驗證穩定性。

## 下一步路由

回 [3.2 durable queue](/backend/03-message-queue/durable-queue/) 與 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)。

## 引用源

- [Scaling Slack's Job Queue](https://slack.engineering/scaling-slacks-job-queue/)
