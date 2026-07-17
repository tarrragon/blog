---
title: "模組一：監控心智模型"
date: 2026-06-19
description: "四類事件（event / error / metric / lifecycle）的分類與收集策略"
weight: 1
tags: ["monitoring", "mental-model", "event-classification"]
---

回答「要收集什麼、為什麼」。四類事件分類是整個監控體系的統一語言。

## 章節

- [四類事件的完整定義](/monitoring/01-mental-model/four-event-types/) — event / error / metric / lifecycle 的分類定義與各自的收集場景
- [事件命名規範](/monitoring/01-mental-model/event-naming-convention/) — namespace.action 格式、命名慣例與衝突解決
- [商業方案的事件類型對應](/monitoring/01-mental-model/commercial-event-mapping/) — Sentry / Crashlytics / GA4 / Datadog RUM 怎麼對應四類事件
- [從需求推導「該收集哪些事件」](/monitoring/01-mental-model/derive-collection-from-requirements/) — 從業務需求出發、系統性推導收集清單的方法
- [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/) — 四類補齊檢查確保事件清單沒有遺漏、粒度判準確保每個事件只記一個事實
- [動機驅動的事件設計](/monitoring/01-mental-model/motivation-to-event-mapping/) — Debug / 商業 / 資安 / 效能四個動機各自需要什麼事件

## 跨分類引用

- → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)：本模組教分類，testing 教設計 log 點
- → [monitoring 模組八 商業利用](/monitoring/08-business-analytics/)：event 類是行為分析的原料
- → [backend 04 可觀測性](/backend/04-observability/)：server-side 用 OTLP，本系列用 HTTP POST JSON
