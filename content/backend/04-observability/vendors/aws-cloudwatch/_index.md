---
title: "AWS CloudWatch"
date: 2026-05-01
description: "AWS 原生觀測性服務、Logs / Metrics / Traces (X-Ray)"
weight: 7
---

CloudWatch 是 AWS 原生 observability 服務、覆蓋 Metrics / Logs / Alarms / Synthetics / RUM、X-Ray 提供 tracing。優勢是跟 AWS 服務深度整合、缺點是查詢語法（Logs Insights / Metrics Math）有學習曲線、跨區成本可觀。

## 適用場景

- AWS-only 環境、深度整合需求
- Lambda / ECS / EKS 等 AWS managed 服務的內建觀測
- 不想額外引入第三方 observability vendor
- 簡單告警與儀表板

## 不適用場景

- 多雲 / 跨雲統一 observability
- 需要進階 APM 體驗（X-Ray 較弱於 Datadog APM）
- 高頻 query / 大量 logs（成本曲線陡峭）

## 跟其他 vendor 的取捨

- vs `datadog`：CloudWatch AWS 原生整合 vs Datadog 廣度
- vs `gcp-cloud-operations`：AWS 對應 GCP 的雲原生方案
- vs Grafana + CloudWatch data source：Grafana 視覺化 + CloudWatch 資料

## 預計實作話題

- CloudWatch Logs Insights 查詢
- Metrics Math
- Alarms 與 composite alarms
- X-Ray tracing
- Container Insights / Lambda Insights
- 成本控制
