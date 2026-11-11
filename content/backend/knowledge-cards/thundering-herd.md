---
title: "Thundering Herd"
date: 2026-04-23
description: "說明大量工作同時被喚醒或同時競爭資源時的尖峰風險"
weight: 49
---

Thundering herd 的核心概念是「大量等待中的工作同時醒來並競爭同一個資源」。這種同步行為會製造瞬間尖峰，即使平均流量看起來可承受。 可先對照 [Timeout](/backend/knowledge-cards/timeout/)。

## 跟其他概念的關係

Thundering herd 常出現在 cache 過期、鎖釋放、服務恢復、排程任務、client reconnect 與廣播通知。它和 cache stampede 相近，但範圍更廣，包含各種同時醒來與同時競爭。 可先對照 [Timeout](/backend/knowledge-cards/timeout/)。

## 可觀察訊號與例子

系統需要處理 thundering herd 的訊號是故障恢復後流量突然高於平常數倍。WebSocket server 重啟後，所有 client 同時重連，可能讓 authentication、subscription 與 presence store 同時過載。

## 判斷條件與後果

Thundering herd 的處理方式取決於大量工作同時醒來的原因：

- **共用同一個時間點**（cache 同時過期、排程同一刻觸發、client 同時重連）：等待時間加上 jitter，同一刻的請求攤成一段時間內的分布。
- **同時要同一筆資料**（同一個 cache key 失效）：singleflight 讓一個請求去重建、其他請求等它的結果；soft TTL 讓過期的值在重建期間繼續回給讀取方，只有一個請求在背景更新。
- **服務恢復後的重連與補送**：排隊與分批恢復讓流量依後端承受得了的速度進來；token bucket 與 [Admission Control](/backend/knowledge-cards/admission-control/) 把超過容量的部分延後或拒絕，後端的負載停在上限內。

這幾種做法都把同步尖峰轉成可控的分布。沒有處理時，平均流量看起來承受得了，恢復的那一刻卻讓 authentication、presence store 這類共用元件同時過載，服務在恢復與再次失效之間反覆。
