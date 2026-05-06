---
title: "Span"
date: 2026-04-23
description: "說明 trace 中一段工作如何記錄耗時、狀態與關聯"
weight: 107
---


Span 的核心概念是「trace 中的一段工作」。每個 span 描述某個操作的開始、結束、耗時、狀態、屬性與父子關係。 可先對照 [Server-Sent Events (SSE)](/backend/knowledge-cards/sse/)。

## 概念位置

Span 是 tracing 的基本單位。HTTP handler、database query、cache call、broker publish、consumer handle 與外部 API 呼叫都可以形成 span。 可先對照 [Server-Sent Events (SSE)](/backend/knowledge-cards/sse/)。

## 可觀察訊號與例子

系統需要 span 的訊號是單一 request 裡有多個步驟，需要知道哪一步變慢。Checkout trace 中 payment span 佔 80% 時間，問題焦點就落在付款依賴或其網路路徑。

## 設計責任

Span 設計要控制名稱、屬性、錯誤狀態與敏感資料。Span 太粗會看不出瓶頸，太細會增加成本與噪音。
