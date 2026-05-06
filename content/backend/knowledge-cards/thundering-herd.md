---
title: "Thundering Herd"
date: 2026-04-23
description: "說明大量工作同時被喚醒或同時競爭資源時的尖峰風險"
weight: 48
---


Thundering herd 的核心概念是「大量等待中的工作同時醒來並競爭同一個資源」。這種同步行為會製造瞬間尖峰，即使平均流量看起來可承受。 可先對照 [Timeout](/backend/knowledge-cards/timeout/)。

## 概念位置

Thundering herd 常出現在 cache 過期、鎖釋放、服務恢復、排程任務、client reconnect 與廣播通知。它和 cache stampede 相近，但範圍更廣，包含各種同時醒來與同時競爭。 可先對照 [Timeout](/backend/knowledge-cards/timeout/)。

## 可觀察訊號與例子

系統需要處理 thundering herd 的訊號是故障恢復後流量突然高於平常數倍。WebSocket server 重啟後，所有 client 同時重連，可能讓 authentication、subscription 與 presence store 同時過載。

## 設計責任

常見策略包括 jitter、排隊、分批恢復、token bucket、singleflight、soft TTL 與 admission control。設計重點是把同步尖峰轉成可控分布。
