---
title: "事故處理 Vendor 清單"
date: 2026-05-01
description: "後端事故處理實作時的常用工具選擇，預先建立引用路徑"
weight: 91
---

本清單列出 backend 事故處理會選用的 vendor / platform：on-call、IR 平台、status page、retrospective 工具。每個 vendor 一個資料夾。

跟 [cases/](/backend/08-incident-response/cases/) 是不同維度 — cases 是公開事故案例來源（AWS / Cloudflare / GitHub 等），vendors 是實作工具。

## T1 vendor

On-call / 告警：

- [pagerduty](/backend/08-incident-response/vendors/pagerduty/) — On-call 主流 SaaS
- [opsgenie](/backend/08-incident-response/vendors/opsgenie/) — Atlassian on-call
- [grafana-oncall](/backend/08-incident-response/vendors/grafana-oncall/) — OSS on-call

IR 平台：

- [incident-io](/backend/08-incident-response/vendors/incident-io/) — Slack-native IR
- [firehydrant](/backend/08-incident-response/vendors/firehydrant/) — IR + retrospective
- [rootly](/backend/08-incident-response/vendors/rootly/) — IR 自動化

Status page：

- [atlassian-statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) — Atlassian status page SaaS
- [instatus](/backend/08-incident-response/vendors/instatus/) — 輕量替代

Postmortem / Learning：

- [jeli](/backend/08-incident-response/vendors/jeli/) — Postmortem / learning（PagerDuty 收購）

## 後續擴充

- T2 候選：squadcast、xMatters、splunk-on-call、status.io、cachet（OSS status）、howie、blameless
- T3 候選：自建（Slack workflow + GitHub Issues）、jira-service-management
