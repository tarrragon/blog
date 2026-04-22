---
title: "8.8 Stream：Feeds 與 Chat"
date: 2026-04-23
description: "看 Go 如何支撐 feeds、chat 與即時訊息 SDK"
weight: 8
---

Stream 的官方案例很適合教學用途，因為它把 Go 的幾個核心優勢講得很直接：ecosystem、easy onboarding、fast performance、solid support for concurrency 與 productive programming environment。官方案例還特別提到，這讓一個小團隊能支撐超過 5 億使用者的 feeds 與 chat。

## 你應該看什麼

- [Stream case study](https://go.dev/solutions/stream)
- [Official Go SDK for Stream](https://github.com/GetStream/getstream-go)

## 這個案例告訴我們什麼

1. Go 很適合即時 feed 與 chat 這種高事件量服務。
2. 小團隊也能利用 Go 把服務做大。
3. SDK 與 server-side service 都能用同一套語言思維來維護。

## 可對照的公開原始碼

- [GetStream/getstream-go](https://github.com/GetStream/getstream-go)

這個 Go SDK 很適合拿來看 request/response model、client 設計、testing 與 OpenAPI codegen 的邊界。

