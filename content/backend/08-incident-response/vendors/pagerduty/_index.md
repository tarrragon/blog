---
title: "PagerDuty"
date: 2026-05-01
description: "On-call / alerting 主流 SaaS、IR 平台演化"
weight: 1
tags: ["backend", "incident-response", "vendor"]
---

PagerDuty 是 on-call / alerting 的事實標準 SaaS、承擔三個責任：alert routing + escalation policy + schedule、incident workflow + response play + runbook automation、postmortem 整合（Jeli 收購）。從 paging 工具演化成完整 IR 平台。

## 本章目標

1. 用 PagerDuty 配置 service + escalation policy + schedule
2. 設計 Event Orchestration（alert → incident 自動化）
3. 用 Response Play 自動化 incident response
4. 用 Process Automation（Runbook Automation）做 remediation
5. 評估 PagerDuty vs Opsgenie / incident.io / Rootly 的選用

## 最短路徑

```bash
# 1. 註冊 + 建 service / team / schedule
# 2. 配置 integration（觀測平台 webhook）
# 3. 觸發 test alert、看 escalation policy 是否生效
# 4. 用 Mobile app 接 incident
```

## 日常操作與決策形狀

### Service / team / escalation

子議題：

- Service：對應一個應用 / component
- Escalation policy：N 層 escalation
- Schedule：rotation / override
- 對應指令：Terraform PagerDuty provider

### Event Orchestration + Response Play

子議題：

- Alert → Incident deduplication / grouping rule
- Dynamic routing
- Response Play 自動 page additional / 建 Slack channel

## 進階主題（按需閱讀）

### Process Automation（Runbook Automation）

子議題：跟 Rundeck 整合、自動 remediation（restart / scale / rollback）、approval workflow

### Jeli integration（postmortem）

子議題：從 incident 自動 import 進 Jeli、timeline + interview workflow、對應 [Jeli vendor](/backend/08-incident-response/vendors/jeli/)

### Service ownership

子議題：service catalog、team ownership、跟 SRE org 對齊

### AIOps

子議題：ML alert clustering、probable root cause、change correlation

## 排錯快速判讀

- **Alert storm**：deduplication 不夠 / escalation 觸發過頭、用 Event Orchestration grouping
- **Missed ack**：on-call mobile 通知失效、檢查 notification log
- **False positive**：alert source（觀測平台）threshold 過敏感、對應 [04 observability](/backend/04-observability/)

## 何時改走其他服務

| 需求形狀              | 改走                                                                    |
| --------------------- | ----------------------------------------------------------------------- |
| Atlassian 生態        | [Opsgenie](/backend/08-incident-response/vendors/opsgenie/)             |
| OSS / 預算敏感        | [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) |
| Slack-first IR        | [incident.io](/backend/08-incident-response/vendors/incident-io/)       |
| Microsoft Teams       | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)       |
| No-code workflow + AI | [Rootly](/backend/08-incident-response/vendors/rootly/)                 |

## 不在本頁內的主題

- 各 integration 完整 setup / Pricing / AIOps 內部演算法

## 案例回寫

**PagerDuty 公開 customer 多為大型 SaaS / 平台**：GitHub / Cloudflare / Slack / Datadog 等皆為 PagerDuty 公開引用之案例（PagerDuty.com customer stories）。下列案例可作為「paging 設計如何影響事故 detect → ack → mitigate 時間」的閱讀脈絡。

| 案例                                                                | 對應主題                                   |
| ------------------------------------------------------------------- | ------------------------------------------ |
| [GitHub cases](/backend/08-incident-response/cases/github/)         | 大型平台事故的多輪 paging 與輪值           |
| [Cloudflare cases](/backend/08-incident-response/cases/cloudflare/) | 控制面 vs data plane 的 paging 分軌        |
| [Slack cases](/backend/08-incident-response/cases/slack/)           | 通訊平台失效時 paging 通道的退路           |
| [Datadog cases](/backend/08-incident-response/cases/datadog/)       | 觀測平台事故的 self-paging 與外部 fallback |

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)、[Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/)
- 下游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
