---
title: "Grafana Stack"
date: 2026-05-01
description: "Grafana / Loki / Tempo / Mimir / Pyroscope 全棧"
weight: 3
---

Grafana Labs 提供開源 observability 全棧：Grafana（視覺化）/ Loki（logs）/ Tempo（traces）/ Mimir（metrics 長期儲存）/ Pyroscope（profiling）。可自管或用 Grafana Cloud。是 OSS-first 的 Datadog 替代方案。

## 適用場景

- 需要 OSS / 自管 observability 全棧
- 多 data source 統一視覺化（Prometheus / Loki / Tempo / SQL）
- Grafana Cloud（managed 版）
- 跨雲 / 多環境統一儀表板

## 不適用場景

- 想要極致簡單 turnkey 體驗（vs Datadog）
- 需要 APM 自動 instrumentation 深度（部分弱於 Datadog）

## 跟其他 vendor 的取捨

- vs `datadog`：OSS 可自管 vs SaaS 整合；Grafana Cloud 是 SaaS 對標
- vs `prometheus`：Mimir 解決 Prometheus 長期儲存
- vs `elastic-stack`：Loki 是 log aggregation 替代

## 預計實作話題

- Grafana 視覺化與 dashboard as code
- Loki LogQL 查詢
- Tempo trace 採集
- Mimir 長期 metrics 儲存
- Pyroscope continuous profiling
- Grafana Cloud 適用判斷
