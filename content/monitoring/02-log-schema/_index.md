---
title: "模組二：Log Schema 設計"
date: 2026-06-19
description: "跨平台統一事件格式、欄位設計、版本演進策略"
weight: 2
tags: ["monitoring", "schema", "json", "event-format"]
---

回答「事件長什麼樣」。schema 是所有 SDK 和 collector 的契約 SOT。

## 待寫章節

- [x] event.schema.json 完整欄位解說
- [x] 欄位設計原則（source 標明來源 / data 自由欄位 / v 版本演進）
- [x] Schema 版本演進策略（backward compatible 的增量變更）
- [x] 跟 OpenTelemetry 的 schema 差異對照

## 跨分類引用

- SOT repo：[tarrragon/monitor](https://github.com/tarrragon/monitor) 的 `schema/event.schema.json`
- ← [testing 模組二](/testing/02-client-observability/)：log 點設計產出的事件需符合本 schema
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：schema 中哪些欄位需要 redaction
