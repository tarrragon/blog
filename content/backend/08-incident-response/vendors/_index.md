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

## 內容覆蓋進度

每個 vendor 服務頁下會擴充兩類文章：deep article（vendor 自身的配置、故障、容量、走 [6-section 模板](/posts/vendor-deep-article-methodology/)）跟 migration playbook（跨 vendor 遷移流程、走 [6-type 結構](/posts/migration-playbook-methodology/)）。「→ X」代表遷移到 X 的 playbook、「← X」代表從 X 遷入。

| Vendor                                        | Deep article | Migration playbook                                               |
| --------------------------------------------- | ------------ | ---------------------------------------------------------------- |
| [PagerDuty](pagerduty/)                       | —            | [→ incident.io (Type E)](pagerduty/migrate-to-incident-io/)      |
| [Opsgenie](opsgenie/)                         | —            | [← PagerDuty (Type A)](opsgenie/migrate-from-pagerduty/)         |
| [Atlassian Statuspage](atlassian-statuspage/) | —            | [→ Instatus (Type B)](atlassian-statuspage/migrate-to-instatus/) |

其他 T1 vendor（Grafana OnCall / incident.io / FireHydrant / Rootly / Instatus / Jeli）尚未開始。對應的 backlog 議題見上方「T1 服務頁大綱」段每個服務頁要回答的核心問題、跟各 vendor `_index.md` 的「預計實作話題」段。

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

## 跨 vendor 議題對照

本模組 9 個 vendor 跨 4 個 sub-category（on-call paging / IR coordination / status page / learning）、覆蓋 incident 全流程。對照表用「橫向 incident 流程節點」標明每個議題在哪個 sub-category 落地。

| 議題            | PagerDuty           | Opsgenie            | Grafana OnCall | incident.io     | FireHydrant      | Rootly          | Statuspage  | Instatus    | Jeli                  |
| --------------- | ------------------- | ------------------- | -------------- | --------------- | ---------------- | --------------- | ----------- | ----------- | --------------------- |
| 主責任          | On-call SaaS        | Atlassian on-call   | OSS on-call    | IR coordination | IR coordination  | IR coordination | Status page | Status page | Learning / postmortem |
| Paging          | 核心                | 核心                | 核心           | 後加            | 後加             | 後加            | N/A         | N/A         | N/A                   |
| IR coordination | Response Play       | 中等                | 弱             | 核心 (Slack)    | 核心 (Teams)     | 核心 (no-code)  | N/A         | N/A         | N/A                   |
| Status page     | 整合外部            | 整合 Statuspage     | 整合外部       | 整合外部        | 內建             | 整合外部        | 核心        | 核心        | N/A                   |
| Retrospective   | Jeli (整合)         | Confluence          | 弱             | template        | facilitator      | AI              | N/A         | N/A         | 核心 (narrative)      |
| 配置模式        | UI + Terraform      | UI                  | UI / Helm      | Slack + UI      | Slack/Teams + UI | No-code UI      | UI + API    | UI + API    | UI                    |
| 整合 IR 工具    | 支援                | 支援                | 中等           | 支援            | 支援             | 200+ 整合       | IR push     | IR push     | PagerDuty 整合        |
| 商業 / 開源     | 商業 SaaS           | 商業 SaaS           | OSS / Cloud    | 商業 SaaS       | 商業 SaaS        | 商業 SaaS       | 商業 SaaS   | 商業 SaaS   | 商業（PD 旗下）       |
| 平台支援        | iOS / Android / Web | iOS / Android / Web | Web            | Slack first     | Slack + Teams    | Slack + Teams   | Web         | Web         | Web                   |

對照表的用途有三：

- 寫某 vendor 頁時、看相同 sub-category 對手如何處理同議題
- 讀者組 IR stack：paging + IR coordination + status page + learning 各選 1
- 評估 best-of-breed vs all-in-one 取捨

下面 4 段把對照表的 sub-category 展開。

### Paging（PagerDuty / Opsgenie / Grafana OnCall）

Paging 是 alert 找對人的入口。**PagerDuty** 業界標準、完整 IR 平台演化、Jeli 收購補 learning；**Opsgenie** Atlassian 生態最強、跟 JSM / Statuspage / Confluence 一站式；**Grafana OnCall** OSS / 預算敏感替代、跟 Grafana 觀測生態整合。

選型判讀：成熟 + 跨生態 → PagerDuty；Atlassian 用戶 → Opsgenie；OSS / Grafana 用戶 → Grafana OnCall。

### IR coordination（incident.io / FireHydrant / Rootly）

IR coordination 是事故當下的協作平台、把 incident lifecycle 自動化。**incident.io** Slack-first、UX 最簡潔；**FireHydrant** 雙平台（Slack + Teams）、內建 status page + retrospective facilitator；**Rootly** no-code workflow + AI 輔助、200+ integration。

選型判讀：Slack-only + 簡潔 → incident.io；Microsoft Teams + 完整 retro → FireHydrant；no-code 客製 + AI → Rootly。三者都有 paging 模組、可不另外用 PagerDuty。

### Status page（Atlassian Statuspage / Instatus）

Status page 是對外溝通入口、是法律 / SLA / 客戶信任的 evidence。**Statuspage** 事實標準、enterprise SLA、跟 Opsgenie / PagerDuty / IR 平台廣泛整合；**Instatus** 輕量 / 價格親民 / 現代 UI / startup 友善。

選型判讀：enterprise / 既有 Atlassian 投資 → Statuspage；budget / startup → Instatus；OSS 自管 → Cachet（不在本表）；IR 平台內建夠 → FireHydrant 內建 status page。

### Learning（Jeli）

Learning 是事故後的組織學習、不是 retro template、是 longitudinal pattern analysis。**Jeli**（2023 PagerDuty 收購）narrative-based investigation + cross-incident pattern detection、源自 Honeycomb Production Excellence 文化。Jeli 跟 IR 平台的 retrospective 模組 complement、不取代 — IR retro 是單事故、Jeli 是跨事故學習。

選型判讀：深度 learning + multi-incident pattern → Jeli（PagerDuty 用戶）；單事故 retro template → IR 平台內建即可；組織學習 / 文化變革 → Jeli + 對應流程。

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
