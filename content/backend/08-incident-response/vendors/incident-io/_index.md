---
title: "incident.io"
date: 2026-05-01
description: "Slack-native IR 平台、整合 paging / response / retro"
weight: 4
tags: ["backend", "incident-response", "vendor"]
---

incident.io 是 Slack-native IR 平台、承擔三個責任：把 incident lifecycle 整合在 Slack 內（declare / respond / update / close / postmortem）、自動 timeline + action item tracking、後加 on-call 模組整合 paging。設計取捨偏向「Slack-first + lifecycle automation + 一站式」。

## 本章目標

1. 整合 incident.io 到 Slack workspace
2. 配置 incident severity / role / status workflow
3. 設計 catalog（service / team metadata）
4. 用 post-incident flow 自動產 postmortem template
5. 評估 incident.io vs FireHydrant / Rootly

## 最短路徑

```bash
# 1. Slack install incident.io app
# 2. /incident declare 建第一個 incident
# 3. 配置 severity / role
# 4. close + retrospective
```

## 日常操作與決策形狀

### Slack workflow

子議題：

- `/incident` slash command
- Auto-created channel（#inc-...）
- Role assignment（commander / scribe / comms）
- Bot prompts

### Catalog + Post-incident flow

子議題：

- Service / team / customer metadata
- 跟 [5 deployment service ownership](/backend/05-deployment-platform/) 對齊
- Auto timeline from Slack
- Action item sync 到 Jira / Linear
- Postmortem template + learning review

## 進階主題（按需閱讀）

### On-call 模組

子議題：incident.io 自家 paging、schedule + escalation、跟 IR workflow 同 app

### Status page integration

子議題：跟 Atlassian Statuspage / Instatus 整合、自動 sync incident status to public page

### Workflow automation

子議題：custom workflow（trigger → action）、severity-based auto-page、approval gate

## 排錯快速判讀

- **Slack app 沒回應**：bot offline / permission
- **Severity 沒對齊**：team severity definition 不一致、設 catalog default
- **Action item drift**：sync to Jira 失敗 / ownership 不明
- **Postmortem 沒做**：close 後 prompt 沒觸發 / template 太複雜

## 何時改走其他服務

| 需求形狀              | 改走                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| Microsoft Teams       | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)     |
| No-code workflow / AI | [Rootly](/backend/08-incident-response/vendors/rootly/)               |
| Paging-first          | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)         |
| 自建 Slack workflow   | Slack workflow + GitHub Issues / Linear                               |
| Learning-focused      | [Jeli](/backend/08-incident-response/vendors/jeli/)（PagerDuty 整合） |

## 不在本頁內的主題

- Slack app 完整 spec / Custom workflow 細節 / Pricing

## 案例回寫

**incident.io 主打 Slack-native IR**：本案例庫尚無直接揭露 incident.io 使用細節的事故；可參照的閱讀脈絡是「以 Slack 為主要協作通道、事故 channel + 公開 status 同步運作」的服務。

| 案例                                                          | 對應主題                                     |
| ------------------------------------------------------------- | -------------------------------------------- |
| [Slack cases](/backend/08-incident-response/cases/slack/)     | 通訊平台失效時 IR channel 的退路設計         |
| [Discord cases](/backend/08-incident-response/cases/discord/) | 即時通訊產品事故的多通道協作節奏（對照素材） |

待補 candidate：Lightspeed / Linear / Etsy 等 incident.io 公開 customer story。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)、[Rootly](/backend/08-incident-response/vendors/rootly/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
