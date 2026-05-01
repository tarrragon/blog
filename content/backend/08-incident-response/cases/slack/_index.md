---
title: "Slack"
date: 2026-05-01
description: "Slack 通訊服務事故與外部狀態頁設計"
weight: 11
---

Slack 是即時通訊服務、事故時通訊管道本身受影響、是「monitor your own monitor」議題的代表。Slack engineering blog 公開度高、status page 設計細緻。

## 規劃重點

- 通訊管道自身故障：客戶用 Slack 通報 Slack 事故的 paradox
- 外部狀態頁設計：細粒度 region / feature 揭露
- WebSocket 連線風暴：reconnection storm 在大規模長連線服務的特殊風險
- 跨 workspace 隔離：multi-tenant 事故的部分擴散模式

## 預計收錄事故

| 年份 | 事故              | 教學重點                        |
| ---- | ----------------- | ------------------------------- |
| 2022 | Jan 全球登入失效  | 配置變更、跨服務依賴            |
| 待補 | 其他大規模 outage | reconnection storm、status 揭露 |

## 引用源

待補（Slack engineering blog、status.slack.com snapshot）。
