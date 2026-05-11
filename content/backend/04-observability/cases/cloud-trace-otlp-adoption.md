---
title: "4.C5 Google Cloud：Cloud Trace 導入 OTLP 入口"
date: 2026-05-07
description: "觀測平台從專有入口擴展到 OTLP 標準通道的案例。"
weight: 5
tags: ["backend", "observability", "case-study"]
---

這個案例的核心責任是說明 observability 平台轉換常來自資料通道標準化需求。

## 觀察

Google Cloud 在 Cloud Trace 提供 OTLP 支援，降低應用程式對特定傳輸介面的綁定。

## 判讀

當團隊要跨多環境與多工具，標準化傳輸協定能減少重複 instrumentation 與遷移摩擦。

## 策略

1. 將 collector 與 in-process exporter 對齊 OTLP。
2. 把 trace schema 與 sampling 規則集中治理。
3. 在遷移期保留舊通道與新通道比對。

## 下一步路由

回 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 與 [4.18 observability operating model](/backend/04-observability/observability-operating-model/)。

## 引用源

- [OTLP in Google Cloud Observability](https://cloud.google.com/blog/products/management-tools/opentelemetry-now-in-google-cloud-observability)
