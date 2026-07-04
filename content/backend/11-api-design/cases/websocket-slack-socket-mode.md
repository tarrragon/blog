---
title: "11.C57 Slack Socket Mode：WebSocket 上自建 ack、retry 與多連線熱備"
date: 2026-07-04
description: "協議不給保證、vendor 在應用層自建整套可靠性：envelope ack、未 ack 就 retry、多連線熱備、斷線預警"
weight: 57
tags: ["backend", "api-design", "case-study", "realtime"]
---

這個案例的核心責任是提供 WebSocket 可靠性由應用層自建的一手實證。

## 觀察

Slack Socket Mode 用 WebSocket 取代 HTTP webhook 收 events 與 interactions。連線會定期 refresh：app 拿到 `approximate_connection_time`、要盡快連上新的 WebSocket URL；斷線前約 10 秒可能收到 `disconnect`（`reason: "warning"`）或 `refresh_requested`。允許同時最多 10 條 WebSocket 連線做 graceful restart 與負載。ack 強制：app 必須為每個 event 回送 `envelope_id` 確認、否則 Slack 會 retry（「Your app still needs to acknowledge receiving each event so that Slack knows whether to retry」）。

## 判讀

因為 WebSocket 協議層不給保證（見 C56）、vendor 必須在應用層自建整套可靠性 —— 多連線熱備、disconnect 預警、envelope ack、未 ack 就 retry。這是「WebSocket 給管線、投遞保證要自己做」的一手實證：協議的空白由 vendor 的應用層協定填上、而每個 vendor 填的方式不同。

## 對應大綱

styles/realtime/「持久連線推送機制」（投遞保證：應用層自建 at-least-once 加 ack；重連語意：vendor 怎麼處理斷線/refresh）。

## 下一步路由

回 [模組十一案例庫](/backend/11-api-design/cases/)。

## 引用源

- [Using Socket Mode（Slack 官方 docs）](https://docs.slack.dev/apis/events-api/using-socket-mode) — 一手 vendor 官方 docs。

## 二手來源與狀態標注

Slack 特定實作、非 WebSocket 通則；docs 未給 retry 次數/間隔、重複事件去重、ack 時間窗的具體數字。教學引用定位為「vendor 如何在 WebSocket 上補齊協議不給的保證」的示例、非 WebSocket 標準行為。
