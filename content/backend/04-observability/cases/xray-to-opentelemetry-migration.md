---
title: "4.C4 AWS：X-Ray 到 OpenTelemetry 轉換"
date: 2026-05-07
description: "觀測儀表從 vendor-specific SDK 轉向 OpenTelemetry 的治理重點。"
weight: 4
---

這個案例的核心責任是把觀測遷移從工具替換，提升為標準化策略。

## 觀察

AWS 已明確提出 X-Ray SDK/Daemon 的維護時程，並提供遷移到 OpenTelemetry 的路徑。

## 判讀

當 observability agent 與 SDK 受限於單一供應商，轉向 OTel 可以降低未來轉移成本，但需要治理採集、匯出與語意對齊。

## 策略

1. 先盤點現有 instrumentation 與依賴 SDK。
2. 先換 collector/agent，再逐步改應用端 instrumentation。
3. 把 trace/metric 的等價驗證納入 release gate。

## 下一步路由

回 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 與 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/)。

## 引用源

- [X-Ray to OpenTelemetry migration guide](https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-migration.html)
