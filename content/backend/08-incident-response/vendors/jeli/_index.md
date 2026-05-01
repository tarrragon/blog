---
title: "Jeli"
date: 2026-05-01
description: "Postmortem / learning 平台、PagerDuty 收購整合"
weight: 9
---

Jeli（2023 被 PagerDuty 收購、整合進 PagerDuty 平台）是聚焦 incident learning 的工具、強調 narrative-based investigation、把 timeline、人員、決策變成結構化資料。源自 Honeycomb 的 Production Excellence 文化圈。

## 適用場景

- 重視 learning over blame 的團隊
- 需要結構化 incident investigation
- 多事故 longitudinal analysis（看 pattern）
- PagerDuty 用戶（已整合）

## 不適用場景

- 想要 lightweight retro template（用 IR 平台內建）
- 不在 PagerDuty 生態

## 跟其他 vendor 的取捨

- vs `incident-io` / `firehydrant` / `rootly` 的 retro 模組：Jeli 專注 learning 深度
- vs blameless：類似定位、UX 差異
- vs Howie：類似 learning-focused 工具

## 預計實作話題

- Narrative timeline construction
- Incident analysis interview
- Cross-incident pattern detection
- 從 Slack / IR 平台 import
- PagerDuty 整合後的功能演化
