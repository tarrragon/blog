---
title: "OpenTelemetry"
date: 2026-05-01
description: "可觀測性開放標準、SDK 與 Collector"
weight: 1
---

OpenTelemetry（OTel）是 CNCF 開放標準、定義 traces / metrics / logs 的資料模型、SDK 與 OTLP 協議。Vendor-neutral instrumentation 的事實標準、避免 vendor lock-in。多數現代 observability 平台都接受 OTLP。

## 適用場景

- 跨 vendor instrumentation 標準化
- 避免 vendor lock-in
- 自動 instrumentation（Java / Python / Node 等）
- Collector 作為 vendor 切換抽象層

## 不適用場景

- 不需要替換 vendor 的小團隊（直接用 vendor SDK 較快）
- 需要 vendor-specific 高級特性

## 跟其他 vendor 的取捨

- 不是替代品、是抽象層 — 跟下面所有 vendor 互補
- vs vendor SDK（Datadog APM SDK 等）：OTel 跨家、SDK 功能可能落後

## 預計實作話題

- OTLP exporter 設定
- OTel Collector（agent / gateway 模式）
- Auto-instrumentation
- Sampling 策略（head / tail）
- Semantic conventions
- Logs in OTel（相對 metrics / traces 較晚成熟）
