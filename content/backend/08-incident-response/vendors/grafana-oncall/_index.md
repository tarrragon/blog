---
title: "Grafana OnCall"
date: 2026-05-01
description: "OSS on-call 平台、Grafana Labs"
weight: 3
---

Grafana OnCall 是 Grafana Labs 出品的 OSS on-call 平台、源自 Amixr 收購、提供 schedule / escalation / phone & SMS notification。可自管或用 Grafana Cloud。是 PagerDuty / Opsgenie 的 OSS 替代。

## 適用場景

- 需要 OSS on-call 工具
- 已用 Grafana 生態
- 預算敏感、想自管
- 中小團隊

## 不適用場景

- 需要進階 IR 自動化（用 PagerDuty / Rootly）
- 需要企業級 SLA

## 跟其他 vendor 的取捨

- vs `pagerduty`：Grafana OnCall OSS；PagerDuty SaaS / 完整
- vs `opsgenie`：類似定位、不同生態
- vs Cachet（OSS status）：互補

## 預計實作話題

- Schedule / escalation chain
- Webhook integration
- Phone / SMS provider 配置（Twilio）
- Grafana Cloud 整合
- 自管部署
