---
title: "GCP Cloud Operations"
date: 2026-05-01
description: "GCP 原生觀測性套件（前 Stackdriver）：Logging / Monitoring / Trace / Profiler"
weight: 8
---

Cloud Operations（前 Stackdriver）是 GCP 原生 observability 套件、Cloud Logging / Monitoring / Trace / Profiler / Error Reporting。跟 GCP 服務深度整合、GKE / Cloud Run / BigQuery 內建匯出。

## 適用場景

- GCP-only 環境、深度整合
- GKE / Cloud Run / Cloud Functions 自動觀測
- BigQuery 匯出長期 logs
- Cloud Profiler 持續 profiling

## 不適用場景

- 多雲 / 跨雲統一
- 需要進階 high-cardinality 分析
- 複雜跨服務 distributed tracing（Trace 較基礎）

## 跟其他 vendor 的取捨

- vs `aws-cloudwatch`：GCP 對應的雲原生方案
- vs Grafana + GCP data source：類似 CloudWatch + Grafana 模式
- vs OTel：GCP 接受 OTLP、可作為 OTel backend

## 預計實作話題

- Cloud Logging 結構化 logs
- Log-based metrics
- Monitoring uptime checks / SLO
- Cloud Trace
- Cloud Profiler
- BigQuery 匯出長期儲存
