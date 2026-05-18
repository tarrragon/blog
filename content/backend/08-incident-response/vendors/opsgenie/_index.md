---
title: "Opsgenie"
date: 2026-05-01
description: "Atlassian on-call、跟 Jira / Statuspage 套件整合"
weight: 2
tags: ["backend", "incident-response", "vendor"]
---

Opsgenie 是 Atlassian 出品的 on-call 平台、承擔三個責任：alert routing + escalation policy、跟 Atlassian 套件（Jira Service Management / Statuspage / Confluence）深度整合、heartbeat monitoring（被動觀察 service 是否還在）。已被併入 Jira Service Management Cloud、原獨立服務逐漸 deprecated。

## 本章目標

1. 配置 Opsgenie team / schedule / escalation
2. 設計 alert routing 與 deduplication
3. 整合 Jira Service Management / Statuspage / Confluence
4. 用 Heartbeat monitoring 守護 cron / scheduled job
5. 評估 Opsgenie → JSM Cloud 遷移路徑

## 最短路徑

```bash
# 1. Atlassian admin 啟用 Opsgenie / JSM
# 2. 建 team / schedule
# 3. 配置 integration（Datadog / Prometheus webhook）
# 4. 試 alert + escalation
```

## 日常操作與決策形狀

### Team / schedule / escalation

子議題：

- Team 對應 service 或 component
- Schedule rotation / override
- Escalation policy（多 step / responder）

### Alert routing + Atlassian 套件整合

子議題：

- Routing rule（priority / source）+ deduplication
- Jira Service Management（ITSM workflow）
- Statuspage（incident → public update）
- Confluence runbook
- Slack / Teams 通知

## 進階主題（按需閱讀）

### Heartbeat monitoring

子議題：主動 ping 監控、schedule heartbeat（cron / batch job 守護）

### Atlassian 整合深度

子議題：Issue creation / sync、SLA / OLA tracking、audit log

### Opsgenie → JSM Cloud 過渡

子議題：原 Opsgenie 用戶遷移時程、功能 parity、API 兼容

## 排錯快速判讀

- **Alert 不觸發**：integration / API key / routing rule
- **Heartbeat false alarm**：cron 跑了但 ping 沒到 / network
- **Atlassian 整合斷裂**：JSM permission / project mapping
- **通知 missed**：mobile app / push / SMS provider

## 何時改走其他服務

| 需求形狀             | 改走                                                                    |
| -------------------- | ----------------------------------------------------------------------- |
| 不在 Atlassian 生態  | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)           |
| OSS 偏好             | [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) |
| Slack-native IR      | [incident.io](/backend/08-incident-response/vendors/incident-io/)       |
| Microsoft Teams + IR | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)       |

## 不在本頁內的主題

- Jira Service Management 完整 ITSM workflow / Atlassian Cloud admin / Statuspage 細節

## 案例回寫

**Opsgenie 是 Atlassian 自家產品**：Atlassian 內部 incident routing / on-call 走 Opsgenie + Jira Service Management、其多租戶事故的協作流程是 Opsgenie 在大型 IR 場景的代表樣本。

| 案例                                                              | 對應主題                                          |
| ----------------------------------------------------------------- | ------------------------------------------------- |
| [Atlassian cases](/backend/08-incident-response/cases/atlassian/) | 14 天事故的 incident commander 輪值與 paging 節奏 |

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)、[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/)
- 下游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
