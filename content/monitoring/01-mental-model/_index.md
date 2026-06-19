---
title: "模組一：監控心智模型"
date: 2026-06-19
description: "四類事件（event / error / metric / lifecycle）的分類與收集策略"
weight: 1
tags: ["monitoring", "mental-model", "event-classification"]
---

回答「要收集什麼、為什麼」。四類事件分類是整個監控體系的統一語言。

## 待寫章節

- [x] 四類事件的完整定義（event / error / metric / lifecycle）
- [x] 事件命名規範（namespace.action 格式）
- [x] 商業方案的事件類型對應（Sentry / Crashlytics / GA4 / Datadog RUM）
- [x] 從需求推導「該收集哪些事件」的方法

## 跨分類引用

- → [testing 模組二 客戶端可觀測性](/testing/02-client-observability/)：本模組教分類，testing 教設計 log 點
- → [monitoring 模組八 商業利用](/monitoring/08-business-analytics/)：event 類是行為分析的原料
- → [backend 04 可觀測性](/backend/04-observability/)：server-side 用 OTLP，本系列用 HTTP POST JSON
