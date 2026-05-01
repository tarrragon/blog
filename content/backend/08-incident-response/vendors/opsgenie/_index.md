---
title: "Opsgenie"
date: 2026-05-01
description: "Atlassian on-call、跟 Jira / Statuspage 套件整合"
weight: 2
---

Opsgenie 是 Atlassian 出品的 on-call / alerting 平台、強項是跟 Jira Service Management / Statuspage / Confluence 等 Atlassian 套件深度整合。已被併入 Jira Service Management Cloud。

## 適用場景

- Atlassian 套件用戶（Jira / Confluence / Statuspage）
- 需要 ITSM workflow 整合
- Heartbeat monitoring
- 既有 Opsgenie 投資

## 不適用場景

- 不在 Atlassian 生態
- 想要最先進 IR 自動化（看 PagerDuty / Rootly）

## 跟其他 vendor 的取捨

- vs `pagerduty`：Opsgenie + Atlassian 整合；PagerDuty 獨立成熟
- vs `incident-io`：Opsgenie paging-first；Incident.io IR-first
- vs Jira Service Management：Atlassian 統合 ITSM

## 預計實作話題

- Team / schedule / escalation
- Alert routing 與 deduplication
- Atlassian 套件整合
- Heartbeat monitoring
- 從 Opsgenie → JSM Cloud 過渡
