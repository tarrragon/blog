---
title: "Prometheus"
date: 2026-05-01
description: "Pull-based metrics 主流 OSS、PromQL 與 alerting"
weight: 2
---

Prometheus 是 CNCF graduated 的 metrics 系統、pull-based scraping、PromQL 查詢、Alertmanager 告警。是 Kubernetes 生態 metrics 的事實標準。短期儲存為主、長期儲存交給 Mimir / Thanos / Cortex 等。

## 適用場景

- Kubernetes / cloud-native metrics
- Pull-based service metrics
- 需要 PromQL 表達能力
- 短中期 metrics 儲存

## 不適用場景

- 長期 retention（單機受限）— 用 Mimir / Thanos
- High-cardinality 場景吃力
- Logs / traces（Prometheus 是 metrics-only）

## 跟其他 vendor 的取捨

- vs `datadog`：Prometheus OSS 自管；Datadog 是 SaaS
- vs `grafana-stack`：Prometheus 是 metrics 部分、Grafana stack 是視覺化 + 全域整合
- vs Mimir / Thanos / Cortex：長期儲存擴展

## 預計實作話題

- Pull vs push 模型
- Service discovery（Kubernetes / Consul）
- Recording rules / alerting rules
- High availability（Prometheus 沒原生 HA、靠 Thanos / Mimir）
- Exporters 生態
- Remote write / read
