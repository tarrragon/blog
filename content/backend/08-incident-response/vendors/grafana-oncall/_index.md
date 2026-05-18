---
title: "Grafana OnCall"
date: 2026-05-01
description: "OSS on-call 平台、Grafana Labs"
weight: 3
tags: ["backend", "incident-response", "vendor"]
---

Grafana OnCall 是 Grafana Labs 出品的 OSS on-call 平台、承擔三個責任：alert routing + schedule + escalation（PagerDuty 替代）、Grafana 生態整合（Grafana / Alertmanager / Mimir）、phone / SMS notification 透過 Twilio 等 provider。源自 Amixr 收購。可自管或用 Grafana Cloud。

## 本章目標

1. 自管 Grafana OnCall（Helm chart）或用 Grafana Cloud
2. 配置 schedule / escalation chain
3. 配置 Twilio / 其他 provider 做 phone / SMS
4. 跟 Alertmanager / Grafana alert 整合
5. 評估 Grafana OnCall vs PagerDuty / Opsgenie 取捨

## 最短路徑

```bash
# 1. 安裝（Grafana Cloud 直接啟用 / 自管 Helm）
# 2. 配置 webhook integration
# 3. 建 schedule + escalation chain
# 4. 試 alert
```

## 日常操作與決策形狀

### Schedule + escalation chain

子議題：rotation、N step escalation、跟 PagerDuty escalation policy 對齊

### Alert grouping + Notification

子議題：alert source（Alertmanager / Grafana / Prometheus / webhook）、grouping / deduplication、Twilio（phone / SMS）/ Slack / Teams / Mobile

## 進階主題（按需閱讀）

### Grafana 生態整合

子議題：Grafana Cloud 內 OnCall、Loki / Tempo alert 整合、跟 Grafana SLO 對應

### 自管部署

子議題：Helm chart、PostgreSQL + Redis 依賴、Twilio account、TLS / domain

### vs PagerDuty / Opsgenie

子議題：OSS / 預算敏感、advanced workflow 較弱、跟商業 SaaS 對齊 path

## 排錯快速判讀

- **Webhook 沒觸發**：integration URL / token 設錯
- **Twilio quota 用完**：phone / SMS 量超 quota、看 Twilio dashboard
- **Schedule overlap**：rotation override 配錯
- **Notification delay**：provider latency / queue backlog

## 何時改走其他服務

| 需求形狀         | 改走                                                              |
| ---------------- | ----------------------------------------------------------------- |
| 進階 IR workflow | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)     |
| Atlassian 生態   | [Opsgenie](/backend/08-incident-response/vendors/opsgenie/)       |
| Slack-native IR  | [incident.io](/backend/08-incident-response/vendors/incident-io/) |
| 商業 SLA         | PagerDuty / Opsgenie / Squadcast                                  |

## 不在本頁內的主題

- Twilio 完整 setup / Helm chart 細節 / Grafana Cloud pricing

## 案例回寫

**待補 Grafana OnCall case**：Grafana Labs 自家、Grafana Cloud customer。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)、[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)
- 下游：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)
