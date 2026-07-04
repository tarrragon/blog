---
title: "11.C60 Stripe webhooks：at-least-once 加簽章、明文要求 consumer 冪等與不依賴順序"
date: 2026-07-04
description: "webhook 對外承諾的教科書樣本：三天重試、重複投遞、no-ordering、簽章驗證的責任在同一頁明文轉移給 consumer"
weight: 60
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 webhook 對外承諾的主錨：可靠性責任如何在 vendor 與 consumer 之間分配。

## 觀察

Stripe webhooks 官方 docs 明文列出四項承諾。重試：live mode 對 destination 重試投遞「up to three days with an exponential back off」。重複投遞明文承認、去重責任丟回 consumer：endpoint「might occasionally receive the same event more than once」、建議「logging the event IDs you've processed」再跳過已處理的。Ordering 明文不保證：「Stripe doesn't guarantee the delivery of events in the order that they're generated」、要求 endpoint 不依賴特定順序。簽章：`Stripe-Signature` header、格式 `t=<timestamp>,v1=<hmac-sha256>`、HMAC-SHA256、signed payload 為 `timestamp + "." + body`、預設 5 分鐘 timestamp tolerance 防 replay。ack：先快速回 2xx、再做可能 timeout 的複雜邏輯。

## 判讀

Stripe 是「對外承諾」的教科書樣本 —— 同一頁把 at-least-once（重複）、no-ordering、簽章驗證三個責任明文轉移給 consumer。可靠性的分工是：vendor 負責「至少送到一次加三天內重試」、consumer 負責「用 event ID 去重、不依賴順序、先 2xx 再處理」。webhook 不是可靠佇列、是把可靠性責任切一半給 consumer 的推送。

## 對應大綱

styles/realtime/「webhook 對外承諾」（主錨、涵蓋 at-least-once 到冪等、ordering 不保證、簽章、快速 ack 四點）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Receive Stripe events in your webhook endpoint（Stripe 官方 docs）](https://docs.stripe.com/webhooks) — 一手 vendor 官方 docs。

## 二手來源與狀態標注

live/sandbox 重試策略不同；tolerance 秒數為 library 預設可調；承諾隨版本變。
