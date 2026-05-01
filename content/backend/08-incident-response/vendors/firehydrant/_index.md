---
title: "FireHydrant"
date: 2026-05-01
description: "IR + retrospective 平台、Slack / Teams 整合"
weight: 5
---

FireHydrant 是 IR 平台、覆蓋 incident response / retrospective / runbook automation / status page。同時支援 Slack 與 Microsoft Teams（vs incident.io 早期 Slack-only）。後加入 on-call 模組。

## 適用場景

- Microsoft Teams 公司
- 需要完整 retrospective workflow
- Runbook automation 重視
- 內建 status page（不想另外接 Statuspage）

## 不適用場景

- 純 Slack-first 偏好（看 incident.io）
- 預算敏感

## 跟其他 vendor 的取捨

- vs `incident-io`：FireHydrant 跨 Slack/Teams；incident.io Slack-first
- vs `rootly`：類似定位、自動化深度差異
- vs `pagerduty`：FireHydrant IR-first；PagerDuty paging-first

## 預計實作話題

- Incident lifecycle 配置
- Runbook automation
- Retrospective template + facilitation
- Status page 內建
- On-call 模組
- Service catalog
