---
title: "Sloth"
date: 2026-05-01
description: "OSS SLO generator for Prometheus"
weight: 12
---

Sloth 是 OSS Prometheus SLO generator、輸入簡單 YAML 定義 SLO、輸出 Prometheus recording rules + alerting rules（multi-window multi-burn-rate）。適合 Prometheus-based 環境的純 OSS SLO。

## 適用場景

- Prometheus-based 環境
- 想要 OSS SLO 工具（無 SaaS 預算）
- GitOps 流程管理 SLO
- Multi-window multi-burn-rate alerting

## 不適用場景

- 跨 data source（Sloth Prometheus-only）
- 需要 SaaS / 企業治理 features
- 不在 k8s / Prometheus 生態

## 跟其他 vendor 的取捨

- vs `nobl9`：Sloth OSS / Prometheus-only；Nobl9 跨源 SaaS
- vs Pyrra（OSS）：類似定位、k8s-native CRD
- vs OpenSLO：Sloth 早於 OpenSLO、後續對齊

## 預計實作話題

- SLO YAML 定義
- 產出 recording rules
- Multi-window multi-burn-rate alert
- Kubernetes Operator mode
- 從 Sloth 升級到 Nobl9 / OpenSLO 路徑
