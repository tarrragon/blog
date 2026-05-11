---
title: "3.C6 Uber：Kafka 事件平台演進"
date: 2026-05-07
description: "事件平台從團隊自管走向多租戶共享基礎設施。"
weight: 6
tags: ["backend", "message-queue", "case-study"]
---

這個案例的核心責任是把 broker 轉換從單隊列問題提升到平台治理問題。

## 觀察

Uber 把 Kafka 用在大規模事件流，演進過程強調多租戶治理與平台化運維。

## 判讀

當事件平台服務眾多團隊，重點是配額、隔離、觀測與運維標準化，而非只擴 broker。

## 策略

1. 定義租戶隔離與配額規則。
2. 標準化 topic 治理與故障處理流程。
3. 以平台指標治理容量與可靠性。

## 下一步路由

回 [3.1](/backend/03-message-queue/broker-basics/) 與 [6.14](/backend/06-reliability/dependency-reliability-budget/)。

## 引用源

- [Building Uber’s Kafka Infrastructure](https://www.uber.com/en-TW/blog/kafka/)
