---
title: "Rootly"
date: 2026-05-01
description: "IR 自動化平台、no-code workflow"
weight: 6
tags: ["backend", "incident-response", "vendor"]
---

Rootly 是 IR 平台、承擔三個責任：no-code workflow builder（拖拉式自動化）、AI 輔助 retrospective + timeline 整理、Slack / Teams 雙平台整合 + integration 數量最廣（200+）。產品迭代快、跟 incident.io / FireHydrant 三家構成 modern IR 平台主要選項。

## 本章目標

1. 用 no-code builder 設計 incident workflow
2. 配置 severity matrix + role assignment
3. 用 AI 輔助 timeline + retrospective
4. 整合 200+ tool（觀測 / cloud / collaboration / ticket）
5. 評估 Rootly vs incident.io / FireHydrant

## 最短路徑

```bash
# 1. Slack / Teams install Rootly app
# 2. /rootly declare 建 test incident
# 3. 拖拉 workflow（severity → action）
# 4. Close + AI retrospective
```

## 日常操作與決策形狀

### No-code workflow builder

子議題：

- Trigger（severity / status / time）→ Action（page / message / ticket）
- Branch / condition / parallel
- Custom field bind

### AI retrospective + Slack/Teams workflow

子議題：

- 自動 timeline from Slack messages
- AI summary（what happened / contributing factor）
- 同 incident.io / FireHydrant Slack workflow
- Teams 平等支援
- Mobile app

## 進階主題（按需閱讀）

### Integration 廣度

子議題：觀測（Datadog / Grafana / New Relic / Honeycomb）/ Cloud（AWS / GCP / Azure）/ Collaboration（Slack / Teams / Zoom）/ Ticket（Jira / Linear / GitHub）/ Status page

### Service catalog + Custom field

子議題：service / team / customer metadata、custom field 帶業務 context、workflow trigger by field

### On-call 模組

子議題：Rootly OnCall（schedule + escalation）、跟 IR workflow 同 app

## 排錯快速判讀

- **Workflow 行為不符**：trigger / condition 邏輯錯、看 workflow run log
- **AI summary 不準**：Slack noise 多、手動補 timeline
- **Integration token 失效**：rotate / OAuth re-auth
- **Slack channel 亂**：naming convention / retention 沒設

## 何時改走其他服務

| 需求形狀            | 改走                                                              |
| ------------------- | ----------------------------------------------------------------- |
| Slack-only / 簡潔   | [incident.io](/backend/08-incident-response/vendors/incident-io/) |
| Microsoft Teams     | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) |
| Paging-first        | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)     |
| Learning-focused    | [Jeli](/backend/08-incident-response/vendors/jeli/)               |
| 自建 Slack workflow | Slack + GitHub Issues / Linear                                    |

## 不在本頁內的主題

- AI model / training detail / Pricing / 200+ integration 個別 setup

## 案例回寫

**待補 Rootly case**：startup / mid-size customer story。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[incident.io](/backend/08-incident-response/vendors/incident-io/)、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
