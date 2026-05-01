---
title: "Discord"
date: 2026-05-01
description: "Discord Gateway scale-out 事故與容量驚奇"
weight: 13
---

Discord 是大規模長連線 gateway 的代表、事故多源自 capacity surprise（用戶行為意外觸發 fan-out 放大）。Discord engineering blog 揭露多次 scaling 事故。

## 規劃重點

- Long-lived WebSocket：與短連線 HTTP 服務的故障模式差異
- Fan-out 放大：單一訊息推播到大量連線的容量風險
- Sharding 與 cluster topology：超大型 guild 的特殊處理
- Gradual rollout 限制：長連線服務的 deploy 節奏

## 預計收錄事故

| 年份 | 事故                   | 教學重點                        |
| ---- | ---------------------- | ------------------------------- |
| 待補 | Gateway scale-out 事故 | capacity surprise、reconnection |
| 待補 | Sessions DB 事故       | session state 規模化的失敗模式  |

## 引用源

待補（Discord engineering blog、status post-mortem）。
