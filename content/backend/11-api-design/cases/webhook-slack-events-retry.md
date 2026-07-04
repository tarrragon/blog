---
title: "11.C62 Slack Events API：3 秒 ack 上限加固定三次重試"
date: 2026-07-04
description: "「慢等於失敗」寫死成 3 秒硬上限、逼 consumer 走立即 2xx 加背景處理；retry header 讓 consumer 辨識重投"
weight: 62
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 webhook ack timeout 逼出同步 ack 與非同步處理拆分的實證。

## 觀察

Slack Events API 官方 docs 明文：app 應在 3 秒內回 HTTP 2xx（「within three seconds」）、否則視為投遞失敗。重試排程固定且明文：初次失敗後共三次重試 —— 第一次幾乎立即、第二次 1 分鐘後、第三次 5 分鐘後。每次重試帶 `x-slack-retry-num`（值 1/2/3）與 `x-slack-retry-reason`（含 `http_timeout`、`http_error`、`too_many_redirects`、`connection_failed`、`ssl_error`）。簽章改用 signed secrets、細節在另一頁。

## 判讀

Slack 把「慢等於失敗」寫死成 3 秒硬上限、逼 consumer 走「立即 2xx 加背景處理」模式；`x-slack-retry-num` 讓 consumer 辨識這是重投、把去重責任明文交出。重試次數與間隔是固定有限的 —— 跟 Stripe 的三天指數退避（見 C60）是不同的承諾形狀。選型時「重試形狀」本身就是一條要讀清楚的承諾。

## 對應大綱

styles/realtime/「webhook 對外承諾」（ack timeout 逼出同步 ack / 非同步處理拆分；重試 header 讓 consumer 辨識重複；跟 Stripe 對照有限固定 vs 長視窗指數退避）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Using the Slack Events API（Slack 官方 docs）](https://docs.slack.dev/apis/events-api/) — 一手 vendor 官方 docs。

## 二手來源與狀態標注

signing 細節需另頁；3 次 / 3 秒為 Slack 特定值。
