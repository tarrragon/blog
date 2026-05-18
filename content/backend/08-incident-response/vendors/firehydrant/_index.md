---
title: "FireHydrant"
date: 2026-05-01
description: "IR + retrospective 平台、Slack / Teams 整合"
weight: 5
tags: ["backend", "incident-response", "vendor"]
---

FireHydrant 是 IR 平台、承擔三個責任：incident response lifecycle（declare / respond / update）、retrospective workflow + runbook automation、cross-platform integration（Slack + Microsoft Teams 雙支援）。內建 status page、後加 on-call 模組。設計取捨偏向「完整 IR + retrospective + Teams 支援」、跟 incident.io 的差異是 Teams 友善。

## 本章目標

1. 整合 FireHydrant 到 Slack / Teams
2. 配置 incident lifecycle + severity matrix
3. 用 Runbook automation 自動化 standard response
4. 用 Retrospective facilitator 跑復盤
5. 評估 FireHydrant vs incident.io / Rootly

## 最短路徑

```bash
# 1. 註冊 + install Slack / Teams app
# 2. 配置 severity matrix / roles
# 3. Declare test incident
# 4. 跑 retrospective workflow
```

## 日常操作與決策形狀

### Incident lifecycle

子議題：

- Severity matrix（impact × urgency）
- Status workflow（detected → investigating → identified → monitoring → resolved）
- Role：commander / scribe / SME

### Runbook automation + Retrospective

子議題：

- 預定 runbook（auto page / 建 Jira / open Zoom）
- Trigger condition
- Retrospective template + facilitator role + action items

## 進階主題（按需閱讀）

### Status page 內建

子議題：不需另接 Statuspage / Instatus、Component / incident sync、Subscriber notification

### Cross-platform（Slack + Teams）

子議題：同帳號跨兩平台、Microsoft Teams enterprise 需求

### On-call 模組 + Service catalog

子議題：後加 module、service / team / dependency metadata 跟 incident 自動關聯

## 排錯快速判讀

- **Severity matrix 不一致**：跨 team 定義不同、用 catalog default + onboarding
- **Runbook 沒觸發**：trigger 不滿足 / integration token 失效
- **Status page 不同步**：自動 / 手動 sync 配置錯
- **Retrospective 沒人做**：close 後沒 prompt / facilitator 沒指派

## 何時改走其他服務

| 需求形狀       | 改走                                                              |
| -------------- | ----------------------------------------------------------------- |
| Slack-first    | [incident.io](/backend/08-incident-response/vendors/incident-io/) |
| No-code / AI   | [Rootly](/backend/08-incident-response/vendors/rootly/)           |
| Paging-first   | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)     |
| Atlassian 套件 | [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) + JSM |

## 不在本頁內的主題

- 各 integration 完整 setup / Pricing / Teams workflow 細節

## 案例回寫

**待補 FireHydrant case**：customer story、Microsoft Teams + IR 用戶案例。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[incident.io](/backend/08-incident-response/vendors/incident-io/)、[Rootly](/backend/08-incident-response/vendors/rootly/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
