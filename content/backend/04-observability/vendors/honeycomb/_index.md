---
title: "Honeycomb"
date: 2026-05-01
description: "High-cardinality observability 平台、events-based 模型"
weight: 6
---

Honeycomb 是 high-cardinality observability SaaS、events-based 模型（不是 metrics aggregation）、強調 unknown-unknowns 的偵錯能力。Charity Majors 推動的 observability-driven SRE 文化代表平台。06 教學標竿同時是實作 vendor，見 [06 honeycomb cases](/backend/06-reliability/cases/honeycomb/)。

## 適用場景

- 需要 high-cardinality query（user_id / request_id 等）
- Distributed system debugging（unknown-unknowns）
- BubbleUp / heatmap 分析模式
- SLO burn rate alerting

## 不適用場景

- 大規模 logs aggregation（Honeycomb 是 events / traces 為主）
- 預算極敏感
- 需要 turnkey APM 自動 instrumentation 廣度（vs Datadog）

## 跟其他 vendor 的取捨

- vs `datadog`：Honeycomb 哲學深度 vs Datadog 廣度
- vs OTel + 其他 backend：Honeycomb 接受 OTLP、可作 OTel 的 traces backend
- 自有 SDK vs OTel：兩者都支援

## 預計實作話題

- Events vs metrics 心智模型
- BubbleUp 分析
- SLO 與 burn rate alert
- OTLP integration
- Refinery（tail-based sampling）
