---
title: "事件命名規範"
date: 2026-06-19
description: "namespace.action 格式的事件命名、命名一致性的工程價值、和商業方案命名慣例的對應"
weight: 2
tags: ["monitoring", "mental-model", "naming", "convention", "event"]
---

事件命名的目的是讓事件可以被 grep、過濾和統計。統一的命名規範讓不同時期、不同開發者加入的事件能在同一個查詢框架中使用。

## namespace.action 格式

每個事件名稱由兩部分組成：namespace（事件發生的模組或功能區域）和 action（發生了什麼）。用 `.` 分隔。

```bash
terminal.connect.start      ← namespace: terminal.connect, action: start
terminal.connect.done       ← namespace: terminal.connect, action: done
terminal.input.submit       ← namespace: terminal.input, action: submit
auth.biometric.success      ← namespace: auth.biometric, action: success
auth.biometric.fallback     ← namespace: auth.biometric, action: fallback
enrollment.qr.scan          ← namespace: enrollment.qr, action: scan
```

### Namespace 層級

Namespace 的層級深度依功能結構而定。兩層通常足夠（`terminal.connect`），三層用於需要進一步區分的場景（`terminal.connect.ws`）。超過三層通常代表 namespace 設計過細，增加認知成本但不增加分析價值。

### Action 命名

Action 使用動詞（`start`、`submit`、`scan`）或狀態（`success`、`failed`、`timeout`）。同一組動作用配對的 action 名稱：`start` / `done`（成對的生命週期）、`success` / `failed`（結果分支）。

避免在 action 中重複 namespace 的資訊。`terminal.connect.terminal_connected` 中 `terminal` 重複了；`terminal.connect.done` 更簡潔。

## 命名一致性的工程價值

### Grep 友好

統一的 namespace 結構讓開發者用 `grep "terminal.connect"` 就能找到所有連線相關事件，不需要知道每個事件的完整名稱。

### 統計友好

按 namespace 前綴分群統計。`terminal.*` 的事件數量 = terminal 功能的使用頻率；`auth.*` 的事件數量 = 認證觸發頻率。層級結構讓統計的粒度可以調整。

### 文件友好

事件清單按 namespace 排列就是一份結構化的功能地圖。新加入的開發者讀事件清單就能理解系統有哪些功能模組。

## 和商業方案的命名對應

不同的商業監控方案有各自的命名慣例。自架方案用 namespace.action 格式，接入商業方案時需要做對應。

| 商業方案    | 命名慣例                  | 對應方式                                           |
| ----------- | ------------------------- | -------------------------------------------------- |
| GA4         | `event_name` + parameters | namespace.action → `event_name`，細節放 parameters |
| Sentry      | transaction name + spans  | namespace → transaction，action → span             |
| Mixpanel    | event name + properties   | namespace.action → event name                      |
| Datadog RUM | action name + view name   | action → action name，namespace → view             |

對應時保持一個原則：自架方案的事件名稱是 source of truth，商業方案的名稱是它的映射。在自架方案中改名後，映射層跟著改；不要讓商業方案的命名反過來影響自架的命名結構。

## 下一步路由

- 四類事件的定義 → [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/)
- 從需求推導收集策略 → [從需求推導「該收集哪些事件」](/monitoring/01-mental-model/derive-collection-from-requirements/)
- 商業方案的完整比較 → [模組六 商業方案比較](/monitoring/06-commercial-comparison/)
