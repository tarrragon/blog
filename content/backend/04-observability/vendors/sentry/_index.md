---
title: "Sentry"
date: 2026-05-01
description: "Error tracking 主流、APM / Profiling / Session Replay 擴展"
weight: 9
---

Sentry 是 error tracking 的事實標準、覆蓋 frontend / backend / mobile，近年擴展到 APM、Continuous Profiling、Session Replay、Cron Monitoring、Feedback。產品 OSS（self-hosted）+ SaaS 雙軌、規模化用 SaaS 為主。

## 適用場景

- Production unhandled exception 追蹤
- 跨 frontend / backend / mobile 的錯誤統一聚合
- Release-aware error tracking（regressed errors）
- 簡易 APM（Performance / Tracing）入門
- Session Replay（前端用戶體驗回放）
- Cron / Scheduled job monitoring

## 不適用場景

- 需要完整 metrics / logs 平台（用 Datadog / Grafana / ELK）
- High-cardinality 分析（用 Honeycomb）
- 純 backend 觀測且已有 Datadog（功能重疊）

## 跟其他 vendor 的取捨

- vs `datadog`：Sentry 錯誤追蹤 UX 強；Datadog 觀測廣度
- vs `honeycomb`：互補、Sentry 錯誤聚合 / 用戶影響；Honeycomb 偵錯深度
- vs `bugsnag` / `rollbar`（T2）：類似定位、Sentry 生態最大
- vs OTel + 其他 backend：Sentry 接受 OTel SDK、但專屬 SDK 功能更深

## 預計實作話題

- SDK 整合（auto-instrumentation）
- Release / source map 設定
- Issue grouping 與 fingerprint
- Performance monitoring（Sentry APM）
- Session Replay 配置與隱私
- Cron Monitoring（Sentry Crons）
- Self-hosted vs SaaS 取捨
- 跟 IR 平台整合（PagerDuty / incident.io）
