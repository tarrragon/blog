---
title: "PagerDuty"
date: 2026-05-01
description: "On-call / alerting 主流 SaaS、IR 平台演化"
weight: 1
---

PagerDuty 是 on-call / alerting 的事實標準 SaaS、escalation policy / schedule / incident workflow / mobile app 成熟。從 paging 工具演化成完整 IR 平台（Incident Response、AIOps、Process Automation）。

## 適用場景

- On-call schedule 與 escalation
- 多訊號源整合（觀測平台 / cloud / SaaS）
- 完整 IR workflow（response play / postmortem）
- 企業級 SLA 與支援

## 不適用場景

- 預算極敏感
- 純 OSS 偏好（用 Grafana OnCall）
- 簡單 paging 需求（看輕量替代）

## 跟其他 vendor 的取捨

- vs `opsgenie`：PagerDuty 更成熟；Opsgenie 跟 Atlassian 套件整合
- vs `grafana-oncall`：PagerDuty SaaS / 完整；Grafana OnCall OSS / 基礎
- vs `incident-io`：PagerDuty paging-first；Incident.io Slack-native IR

## 預計實作話題

- Escalation policy 設計
- On-call schedule（rotation / override）
- Service / integration 模型
- Event Orchestration
- Process Automation（PagerDuty Runbook Automation）
- Incident Workflow / Response Play
- Jeli 整合（postmortem）
