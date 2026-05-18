---
title: "3.C63 Mercari Actionable History：ack deadline 是 batch-level"
date: 2026-05-18
description: "Merpay 支付流水帳用 Pub/Sub、ack deadline 是整批 batch 而非單訊息、acked 訊息會跟同批 expired 一起 redeliver。"
weight: 63
tags: ["backend", "message-queue", "case-study", "google-pubsub"]
---

這個案例的核心責任是揭露 Pub/Sub client lib 「ack deadline 是 batch-level」這個真實的工程陷阱。

## 觀察

Merpay 支付流水帳服務用 Pub/Sub 做 async messaging、靠 nack 控制處理順序；踩到「ack deadline 是整批 batch 而非單訊息」、acked 訊息會跟同 batch 其他 expired/nacked 訊息一起 redeliver 的設計細節。

## 判讀

「ack deadline 是 batch-level」是 Pub/Sub client lib 真實的工程陷阱；idempotency 是處理 duplicate 的必要設計、新出的 exactly-once delivery 才有機會降低重複量。揭露 client lib 的批次語意會「污染」單訊息 ack。

## 對應大綱

Pub/Sub 進階主題：Ack deadline / Push vs Pull / Ordering key（exactly-once / ordering 章節）。

## 下一步路由

回 [Pub/Sub vendor 頁](/backend/03-message-queue/vendors/google-pubsub/) 與 [3.C9 反例：語義誤配](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)。

## 引用源

- [Merpay Actionable History: Displaying Millions of Payments with Lightning Speed](https://engineering.mercari.com/en/blog/entry/20221212-merpay-actionable-history-displaying-millions-of-payments-with-lightning-speed/)
