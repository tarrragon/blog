---
title: "Nobl9"
date: 2026-05-01
description: "SLO platform、跨 data source、企業 SLO 治理"
weight: 11
---

Nobl9 是商業 SLO 平台、跨 data source（Datadog / Prometheus / New Relic / CloudWatch / Splunk 等）、把 SLO 從工具孤島提升到組織治理層。創辦人來自 Google SRE、推動 OpenSLO 標準。

## 適用場景

- 多 data source 統一 SLO 治理
- 企業需要跨團隊 SLO governance
- Error budget 與 burn rate alerting
- OpenSLO 標準採用

## 不適用場景

- 單一 vendor 環境（vendor 內建 SLO 已夠）
- OSS 偏好（用 Sloth / Pyrra）

## 跟其他 vendor 的取捨

- vs `sloth`：Nobl9 SaaS / 跨源；Sloth Prometheus-only OSS
- vs Datadog SLO / Honeycomb SLO：vendor-locked vs 跨源
- vs Pyrra（OSS）：Pyrra k8s-native generator

## 預計實作話題

- SLO 定義（SLI / target / time window）
- Error budget burn rate
- Composite SLO（跨服務）
- OpenSLO 標準
- Alert routing 與整合
