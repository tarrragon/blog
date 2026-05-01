---
title: "incident.io"
date: 2026-05-01
description: "Slack-native IR 平台、整合 paging / response / retro"
weight: 4
---

incident.io 是 Slack-native 的 IR 平台、強項是把 incident lifecycle（declare / respond / update / close / postmortem）整合在 Slack 內、降低工具切換成本。整合 PagerDuty / Opsgenie / Statuspage 等。後加入 on-call 模組。

## 適用場景

- Slack-first 公司文化
- 想把 IR workflow 集中在 Slack
- 需要 incident lifecycle automation
- Postmortem template + automation

## 不適用場景

- 不用 Slack（用 Microsoft Teams 看其他選項）
- 想要 best-of-breed paging-only 工具
- 預算敏感

## 跟其他 vendor 的取捨

- vs `pagerduty`：Incident.io Slack-first IR；PagerDuty paging 為主延伸 IR
- vs `firehydrant` / `rootly`：類似 IR 平台、UX 與整合差異
- vs Slack workflow + GitHub：自建 vs SaaS 取捨

## 預計實作話題

- Slack workflow 整合
- Incident severity / role / status
- Post-incident flow（actions / learnings）
- Catalog（service / team metadata）
- Status page integration
- On-call 模組
