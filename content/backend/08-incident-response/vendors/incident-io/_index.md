---
title: "incident.io"
date: 2026-05-01
description: "Slack-native IR 平台、整合 paging / response / retro"
weight: 4
tags: ["backend", "incident-response", "vendor"]
---

incident.io 是 Slack-native IR 平台、承擔三個責任：把 incident lifecycle 整合在 Slack 內（declare / respond / update / close / postmortem）、自動 timeline + action item tracking、後加 on-call 模組整合 paging。設計取捨偏向「Slack-first + lifecycle automation + 一站式」。

## 服務定位

incident.io 設計上把 *Slack 當成 IR 工作台*、不需要在事故中切換 dashboard：宣告、角色指派、status update、stakeholder comms、timeline、action item、postmortem 全部在 Slack channel 完成、PM / leadership / customer-facing team 看 Slack 就能跟上節奏。2023 年起加上 incident.io On-call（取代 PagerDuty 的 alerting / schedule / escalation layer），從純 *response orchestration* 變成完整 *IR + on-call 平台*、減少 PagerDuty + Slack bot 雙系統的 state drift。

跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 比、incident.io 是 *response-first*、PagerDuty 是 *paging-first*；組合使用時 PagerDuty 觸發 → incident.io 開 channel 跑 response、現在 On-call 模組讓 incident.io 也能獨立扛 paging layer。跟 [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) 比、兩者定位接近、差別在 incident.io 偏 *opinionated workflow*（流程預設嚴謹、custom 餘地小）、FireHydrant 偏 *customizable + Microsoft Teams 友善*。跟 [Rootly](/backend/08-incident-response/vendors/rootly/) 比、Rootly 強調 no-code workflow builder 跟 AI 補助、incident.io 強調 *catalog-driven service ownership* 跟 learning review 結構化。

## 本章目標

1. 整合 incident.io 到 Slack workspace
2. 配置 incident severity / role / status workflow
3. 設計 catalog（service / team metadata）
4. 用 post-incident flow 自動產 postmortem template
5. 評估 incident.io vs FireHydrant / Rootly、判斷是否要走 On-call 模組合併 PagerDuty

## 最短判讀路徑

判斷 incident.io deployment 是否健康、最少看四件事：

- **Slack workflow 完整度**：`/incident` declare 後是否自動開 channel、role bot prompt 是否觸發、status update reminder 是否進 Slack（不靠人記憶 cadence）、stakeholder 是否能在不進 incident channel 的前提下追進度（broadcast channel / status page mirror）
- **Incident type 設計**：severity（SEV1-4）+ incident type（infra / security / customer-facing）+ role 三者是否清楚、severity 定義有沒有歧義（這條是大型 org 最常翻車的地方）
- **Role assignment 跟交接**：commander / scribe / comms / SME 的角色定義、handoff 時 bot 是否 prompt、長 incident（>4hr）的 commander rotation 是否有 fallback
- **Post-incident learning**：close 後是否自動產 postmortem skeleton、action item 是否 sync 到 Jira / Linear 並追完成率、learning review 是否在 N 天內走完（不是寫完 postmortem 就結案）

四件事任一缺失、就是 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 的待補項目。

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

## 核心取捨表

| 取捨維度        | incident.io                        | PagerDuty                                 | FireHydrant                                   | Rootly                                       |
| --------------- | ---------------------------------- | ----------------------------------------- | --------------------------------------------- | -------------------------------------------- |
| 主要 surface    | Slack-native                       | Web / mobile app + 通知                   | Slack + Microsoft Teams                       | Slack 為主                                   |
| 設計取向        | Opinionated workflow、流程預設嚴謹 | Paging-first、response 較淺               | Customizable workflow、Teams 友善             | No-code workflow builder + AI 補助           |
| Paging layer    | 自家 On-call 模組（2023+）         | 業界 paging 標準                          | 整合 PagerDuty / Opsgenie                     | 整合 PagerDuty / Opsgenie                    |
| Catalog         | First-class、service ownership 強  | Service directory 較淺                    | Functionality + service catalog               | Service catalog 中等                         |
| Learning review | Structured（內建 review cadence）  | Postmortems by PagerDuty（需另外 enable） | Retrospectives 工作流                         | Retrospectives + AI summary                  |
| 適合場景        | Slack-heavy 中型 SaaS、流程要嚴謹  | 大型 enterprise、paging-critical          | 多 surface（Slack + Teams）、需要 custom 流程 | Slack-heavy、想用 AI 加速 retro / comms 撰寫 |

選 incident.io 的核心訴求：*團隊已 Slack-heavy*、想要一套 *opinionated workflow* 把 IR 從「靠經驗」變成「靠流程」、且願意接受 catalog 維護成本換取 ownership clarity。

## 進階主題（按需閱讀）

### Workflows（custom automation）

子議題：trigger → condition → action 的低代碼自動化、severity-based auto-page、approval gate、跟外部 API 串接（呼叫 Jira / Linear / Statuspage）。重點是 workflow 進 Git 版控、change review 走 PR、不在 console 直改。

### Catalogue（service ownership + dependency）

子議題：incident.io Catalog 把 service / team / customer / region 等實體建模、incident 宣告時自動帶出 owner team + on-call 名單 + dependent service。對應 [5 deployment service ownership](/backend/05-deployment-platform/) 的 service catalog 概念；catalog stale 是常見 anti-pattern、要設 sync source（Backstage / Terraform / IdP group）+ stale alert。

### On-call layer integration（2023+）

子議題：incident.io On-call 取代 PagerDuty 的 schedule + escalation + paging。優勢是 *single source of truth*（不需要 PagerDuty incident ↔ Slack channel state sync）、缺點是 paging reliability 還在追 PagerDuty 的 multi-region failover 成熟度。遷移時走 *parallel run*（兩邊都 page）2-4 週再切。

### Status Page integration

子議題：跟 [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/) 整合、auto-sync incident status 到 public page、避免 SRE 手動雙寫造成 stakeholder 看到的狀態跟內部不一致。

### AI investigation features（2024+）

子議題：AI summarizer（自動產 incident summary 給 leadership）、suggested actions、postmortem draft。要當 *first draft* 不是 *source of truth*、commander 仍負責最終敘事。

## 排錯快速判讀

- **Slack outage 時 fallback**：incident.io 重度依賴 Slack、Slack 自身 outage 時 IR 工作台會跟著掛 — 要預先準備 *out-of-band channel*（Zoom war room / Google Meet / 手機群組）、commander handoff 流程要寫進 runbook、不能假設 Slack 永遠在
- **Slack app 沒回應**：bot offline / permission scope 不足 / workspace admin 改了 app 權限 — 檢查 incident.io admin console 的 health status
- **Incident type 設計過細**：SEV 1-5 + 10 種 type + 20 個 role 結果沒人記得選哪個、宣告時 friction 太高反而延遲 declare — 收斂到 3-4 種 type、severity 限 4 級、role 預設帶入
- **Incident type 設計過粗**：所有事故都 SEV2、escalation criteria 不明 — 要寫 *severity definition doc*、附判讀範例（customer-facing impact / data loss risk / blast radius）
- **Severity 沒對齊**：team severity definition 不一致、設 catalog default + 在 Slack 宣告時 bot 自動 quote 定義
- **Catalog stale**：service owner 離職沒更新、dependency 改了沒同步 — 要從 IdP group / Terraform / Backstage sync、設 *stale threshold*（>90 天沒更新就 alert owner team）
- **Action item drift**：sync to Jira 失敗 / ownership 不明 — 在 close incident 前 bot 強制要求每個 action item 都有 owner + due date + Jira ticket
- **Postmortem 沒做**：close 後 prompt 沒觸發 / template 太複雜 — 把 template 縮到 5 個必填欄位、其餘 optional、用 AI draft 降低 friction

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

**incident.io 主打 Slack-native IR**：本案例庫尚無直接揭露 incident.io 使用細節的事故；可參照的閱讀脈絡是「以 Slack 為主要協作通道、事故 channel + 公開 status 同步運作」的服務、典型客戶側 profile 是 *Slack-heavy 中型 SaaS organization*、IR 流程強調 collaboration 跟 learning 而非單純 paging。

| 案例                                                          | 對應主題                                     |
| ------------------------------------------------------------- | -------------------------------------------- |
| [Slack cases](/backend/08-incident-response/cases/slack/)     | 通訊平台失效時 IR channel 的退路設計         |
| [Discord cases](/backend/08-incident-response/cases/discord/) | 即時通訊產品事故的多通道協作節奏（對照素材） |

待補 candidate：Lightspeed / Linear / Etsy 等 incident.io 公開 customer story。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)、[Rootly](/backend/08-incident-response/vendors/rootly/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
