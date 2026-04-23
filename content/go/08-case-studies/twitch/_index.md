---
title: "8.5 Twitch：直播與聊天室系統"
date: 2026-04-23
description: "看 Go 如何服務低延遲、高併發的即時系統"
weight: 5
---

Twitch 的案例幾乎就是 Go 教材裡高併發與即時系統的縮影。官方說法很直接：Go 被用在很多 busiest systems，上下文是 live video 與 chat，重點是 simplicity、safety、performance 與 readability。

## 你應該看什麼

- [Twitch - Go’s march to low latency GC](https://go.dev/solutions/twitch)

## 這個案例告訴我們什麼

1. Go 很適合低延遲、高事件量的即時系統。
2. 直播與聊天室會大量依賴長連線與狀態協調。
3. 可讀性在高壓力服務中仍然重要，因為維護者需要快速定位問題。

## 可對照的公開原始碼

- [Go case studies page](https://go.dev/solutions/case-studies)

Twitch 的核心系統原始碼不是公開教學重點，所以這一章更適合把官方案例本身當成第一手材料，再回到你的 [WebSocket](../../../backend/knowledge-cards/websocket)、channel 與 [backpressure](../../../backend/knowledge-cards/backpressure) 章節對照。
