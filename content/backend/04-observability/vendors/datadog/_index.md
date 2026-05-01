---
title: "Datadog"
date: 2026-05-01
description: "All-in-one SaaS 觀測平台、APM / Logs / Metrics / RUM / Security"
weight: 4
---

Datadog 是 all-in-one SaaS observability 平台、覆蓋 APM / logs / metrics / RUM / synthetics / security / CI visibility。賣點是整合度高、安裝簡單、auto-instrumentation 完整。成本是主要取捨點。

## 適用場景

- 想要 turnkey 體驗、不想自管
- 需要 APM 自動 instrumentation
- 多訊號類型統一平台
- AWS / GCP / Azure 多雲整合

## 不適用場景

- 預算敏感（成本可能爆）
- 高 cardinality / high-volume 數據（成本曲線陡峭）
- 需要嚴格 data residency 或 self-hosted

## 跟其他 vendor 的取捨

- vs `grafana-stack`：Datadog SaaS 整合 vs Grafana OSS 可自管
- vs `new-relic`（T2）：類似定位、定價模型不同
- vs `honeycomb`：Datadog 廣度；Honeycomb high-cardinality 深度
- vs `elastic-stack`：Datadog SaaS / 整合；Elastic 偏 logs

## 預計實作話題

- Agent 安裝與配置
- APM 自動 instrumentation
- 成本控制（log indexing / metric cardinality）
- Dashboard / Monitor as code（Terraform）
- OTLP ingestion
