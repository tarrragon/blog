---
title: "事故處理 Vendor 清單"
date: 2026-05-01
description: "規劃 on-call、incident response、status page 與 postmortem 工具的服務頁撰寫順序與判準"
weight: 91
tags: ["backend", "incident-response", "vendor"]
---

事故處理 Vendor 清單的核心責任是把工具名稱放回 alert routing、incident command、stakeholder communication、status page、postmortem 與 learning loop 的判斷。每個服務頁先回答它承擔事故流程的哪一段，再討論輪值成本、協作模型、稽核證據與案例回寫。

跟 [cases/](/backend/08-incident-response/cases/) 是不同維度。Cases 是公開事故案例來源，vendors 是把事故流程落地的工具入口。

## 讀法

事故工具要從協作節點進入。讀者如果要處理告警與輪值，先回到 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)；如果要處理決策紀錄，先回到 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)；如果要處理復盤與回寫，先回到 [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## T1 服務頁大綱

| 服務                                                                                | 類型                  | 頁面要回答的核心問題                                                             |
| ----------------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------- |
| [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)                       | On-call platform      | escalation、service ownership、runbook 與 incident object 如何支援輪值           |
| [Opsgenie](/backend/08-incident-response/vendors/opsgenie/)                         | On-call platform      | Atlassian workflow、routing rule 與 team schedule 如何取捨                       |
| [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/)             | OSS / Grafana on-call | alert grouping、Grafana integration 與自管成本如何取捨                           |
| [incident.io](/backend/08-incident-response/vendors/incident-io/)                   | IR platform           | Slack-native command、timeline、action 與 post-incident workflow 如何支援協作    |
| [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)                   | IR platform           | service catalog、runbook、retrospective 與 automation 如何整合                   |
| [Rootly](/backend/08-incident-response/vendors/rootly/)                             | IR automation         | Slack workflow、status update、task automation 與 Jira / Linear handoff 如何取捨 |
| [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) | Status page           | component、subscriber、incident update 與 stakeholder communication 如何管理     |
| [Instatus](/backend/08-incident-response/vendors/instatus/)                         | Status page           | 輕量 status page、custom domain 與低操作成本如何取捨                             |
| [Jeli](/backend/08-incident-response/vendors/jeli/)                                 | Learning platform     | postmortem、interview、timeline 與 learning review 如何支援組織學習              |

## 服務頁撰寫欄位

| 欄位     | 事故處理服務頁要保留的問題                                                                     |
| -------- | ---------------------------------------------------------------------------------------------- |
| 服務責任 | 它承擔 on-call、IR coordination、status communication、postmortem 還是 learning loop           |
| 適用壓力 | alert volume、team count、customer communication、compliance、learning maturity 哪個壓力最明顯 |
| 替代邊界 | on-call SaaS、Slack workflow、自建流程、status page、learning platform 的機會成本              |
| 操作成本 | rota hygiene、service catalog、integration、timeline quality、stakeholder update               |
| Evidence | alert route、ack time、incident timeline、decision log、status update、action item             |
| 案例回寫 | AWS、Cloudflare、GitHub、Atlassian 等事故案例如何提供流程判準                                  |

## 服務頁標準章節

| 章節                 | 事故處理工具頁要補的內容                                                               |
| -------------------- | -------------------------------------------------------------------------------------- |
| 工具定位             | 它是 on-call、IR coordination、status communication、postmortem 還是 learning platform |
| 本章目標             | 讀者能判斷該工具改善哪個事故協作節點與哪種 evidence handoff                            |
| 最短判讀路徑         | 用「告警找人、事故指揮、對外更新、復盤學習」快速定位工具類型                           |
| 日常操作與決策形狀   | service catalog、rota、escalation、timeline、status update、action item                |
| 核心取捨表           | On-call SaaS、Slack-native IR、自建流程、status page、learning platform 的機會成本     |
| 進階主題             | multi-team escalation、compliance report、customer communication、learning review      |
| 排錯與失敗快速判讀   | alert storm、missed ack、unclear commander、stale status page、action item drift       |
| 何時改走其他服務     | 信號品質回 04、release gate 回 06、平台回退回 05、資安事件回 07                        |
| 不在本頁內的主題     | 完整組織設計、HR 輪值政策、法律公告模板、每個聊天平台 automation                       |
| 案例回寫與下一步路由 | 回到 08 cases、8.19 decision log、8.22 evidence write-back                             |

## 撰寫批次

| 批次 | 服務頁                                | 撰寫目的                                                  |
| ---- | ------------------------------------- | --------------------------------------------------------- |
| I1   | PagerDuty / Opsgenie / Grafana OnCall | 建立 alert routing、escalation 與輪值 baseline            |
| I2   | incident.io / FireHydrant / Rootly    | 建立 incident command、timeline 與 automation 對照        |
| I3   | Atlassian Statuspage / Instatus       | 建立外部溝通、component status 與 stakeholder update 判準 |
| I4   | Jeli / Blameless / 自建流程           | 建立 postmortem、learning review 與 action tracking 對照  |

## 後續候選

| 類型                | 候選服務                                                | 寫作重點                                                         |
| ------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- |
| On-call             | Squadcast、xMatters、Splunk On-Call、Better Stack       | escalation policy、enterprise workflow、handoff                  |
| ITSM / service desk | ServiceNow、Jira Service Management                     | ticket lifecycle、change / incident linkage、enterprise workflow |
| Status page         | status.io、Cachet、Better Stack Status                  | hosted vs self-hosted、subscriber communication                  |
| Learning            | Blameless、Howie                                        | postmortem workflow、learning capture、action follow-up          |
| Collaboration       | Slack workflow、Microsoft Teams workflow、GitHub Issues | 低成本流程、缺口、handoff evidence                               |

主流覆蓋檢查的重點是分開 paging、incident command、ITSM、status communication 與 learning。PagerDuty / Opsgenie / Grafana OnCall 解 paging；incident.io / FireHydrant / Rootly 解 command workflow；ServiceNow / Jira Service Management 解 enterprise ticket lifecycle；Statuspage / Instatus / Cachet 解對外溝通；Jeli / Blameless 解 learning loop。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 上游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
- 上游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
- 規劃：[0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)
