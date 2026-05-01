---
title: "可觀測性 Vendor 清單"
date: 2026-05-01
description: "後端可觀測性實作時的常用選擇，預先建立引用路徑"
weight: 90
---

本清單列出 backend 服務實作會選用的 observability vendor / platform。每個 vendor 一個資料夾，先建定位與取捨骨架。

## T1 vendor

- [opentelemetry](/backend/04-observability/vendors/opentelemetry/) — 標準與 SDK、跨家相容
- [prometheus](/backend/04-observability/vendors/prometheus/) — metrics 主流 OSS
- [grafana-stack](/backend/04-observability/vendors/grafana-stack/) — Grafana / Loki / Tempo / Mimir
- [datadog](/backend/04-observability/vendors/datadog/) — all-in-one SaaS 主流
- [elastic-stack](/backend/04-observability/vendors/elastic-stack/) — ELK / Elastic Cloud
- [honeycomb](/backend/04-observability/vendors/honeycomb/) — high-cardinality 觀察哲學
- [aws-cloudwatch](/backend/04-observability/vendors/aws-cloudwatch/) — AWS 原生
- [gcp-cloud-operations](/backend/04-observability/vendors/gcp-cloud-operations/) — GCP 原生（前 Stackdriver）
- [sentry](/backend/04-observability/vendors/sentry/) — Error tracking 主流、APM / Profiling / Session Replay 擴展

## 後續擴充

- T2 候選：new-relic、splunk、dynatrace、chronosphere、signoz、bugsnag、rollbar（error tracking 替代）
- T3 候選：lightstep、coralogix、azure-monitor、raygun、crashlytics（mobile-focused）
