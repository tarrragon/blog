---
title: "11.C63 Shopify webhooks：ordering 不保證、指定 header 去重、投遞不保證"
date: 2026-07-04
description: "跨 vendor 佐證 ordering-not-guaranteed 加冪等 header 是通則；甚至連投遞本身都不保證、需 reconciliation 兜底"
weight: 63
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 webhook「ordering 不保證加去重」為跨 vendor 通則的第二個獨立佐證。

## 觀察

Shopify webhooks 官方 best practices 明文：ordering 不保證（「Shopify doesn't guarantee ordering within a topic、or across different topics for the same resource」）、建議用 `X-Shopify-Triggered-At` header 或 payload `updated_at` 自行排序。去重：明文要求「ignore duplicate deliveries using `X-Shopify-Webhook-Id`」、指定用哪個 header 當冪等 key。投遞不保證：「Webhook delivery isn't always guaranteed、and your app can miss or mishandle events」。簽章：`X-Shopify-Hmac-Sha256` header。

## 判讀

第二個獨立 vendor 佐證「ordering 不保證加 consumer 用指定 header 去重」是 webhook 通則、而非 Stripe 特例（見 C60）。Shopify 甚至更弱 —— 連投遞本身都不保證、app 要另備 reconciliation 或 polling 補漏。這把「webhook 是盡力而為、不是可靠佇列」講得最白：要不漏事件、consumer 得在 webhook 之外自備對帳。

## 對應大綱

styles/realtime/「webhook 對外承諾」（ordering-not-guaranteed 加冪等 header 是通則；webhook 非可靠佇列、需 reconciliation 兜底）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Webhook best practices（Shopify 官方 docs）](https://shopify.dev/docs/apps/build/webhooks/best-practices) — 一手 vendor 官方 docs。

## 二手來源與狀態標注

本頁未列具體重試次數 / 視窗與 response timeout 秒數（在其 delivery 結構另頁）；此頁足夠支撐 ordering / 去重 / 不保證投遞三點。
