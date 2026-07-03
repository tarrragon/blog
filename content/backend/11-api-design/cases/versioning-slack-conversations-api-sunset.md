---
title: "11.C16 Slack：四族 API 分階段收斂到 Conversations API"
date: 2026-07-03
description: "分階段 deprecation 執行：先掐斷新增量、再處理存量、最後硬停、過渡期用 in-band warning"
weight: 16
tags: ["backend", "api-design", "case-study", "versioning"]
---

這個案例的核心責任是提供 deprecation 分階段執行的完整時序範例。

## 觀察

Slack 2020-01-07 宣告 `channels.*` / `groups.*` / `im.*` / `mpim.*` 四族方法全數 deprecated、由 `conversations.*` 取代；2020-06-10 起新建 app 直接拿不到舊方法、2021-02-24 全面停用。過渡期呼叫舊方法會在 response 收到 `method_deprecated` warning、附解法提示與退場日期。

## 判讀

三個日期各承擔一種風險：先掐斷新增量（新 app 禁用）、再處理存量、最後硬停 — 13 個月分階段收斂。in-band warning（response 內帶 deprecation 訊號）是比 Sunset header 更常見的實務做法、因為它出現在開發者一定會看的地方。

## 對應大綱

11.5 版本策略與 deprecation（anchor）、11.6 向後相容的變更紀律。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Deprecating antecedents to the Conversations API（Slack changelog、2020）](https://docs.slack.dev/changelog/2020-01-deprecating-antecedents-to-the-conversations-api)
