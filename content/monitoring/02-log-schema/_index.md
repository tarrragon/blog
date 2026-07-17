---
title: "模組二：Log Schema 設計"
date: 2026-06-19
description: "跨平台統一事件格式、欄位設計、版本演進策略"
weight: 2
tags: ["monitoring", "schema", "json", "event-format"]
---

回答「事件長什麼樣」。schema 是所有 SDK 和 collector 的契約 SOT。

## 章節

- [event.schema.json 完整欄位解說](/monitoring/02-log-schema/event-schema-fields/) — 每個欄位的語意、必填與選填、格式規範
- [欄位設計原則](/monitoring/02-log-schema/field-design-principles/) — source 標明來源、data 自由欄位、v 版本演進的設計原則
- [Schema 版本演進策略](/monitoring/02-log-schema/schema-versioning/) — backward compatible 的增量變更策略
- [跟 OpenTelemetry 的 schema 差異對照](/monitoring/02-log-schema/otel-comparison/) — OTLP schema 與自定義 schema 的功能差異與取捨

## 跨分類引用

- SOT repo：[tarrragon/monitor](https://github.com/tarrragon/monitor) 的 `schema/event.schema.json`
- ← [testing 模組二](/testing/02-client-observability/)：log 點設計產出的事件需符合本 schema
- → [monitoring 模組七 資安](/monitoring/07-security-privacy/)：schema 中哪些欄位需要 redaction
