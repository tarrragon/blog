---
title: "FireHydrant"
date: 2026-05-01
description: "IR + retrospective 平台、Slack / Teams 整合、service catalog + runbook automation 為核心"
weight: 5
tags: ["backend", "incident-response", "vendor"]
---

FireHydrant 是 IR 平台、承擔三個責任：incident response lifecycle（declare / respond / update）、retrospective workflow + runbook automation、cross-platform integration（Slack + Microsoft Teams 雙支援）。內建 status page、後加 on-call 模組。設計取捨偏向「完整 IR + retrospective + Teams 支援」、跟 incident.io 的差異是 Teams 友善。

## 服務定位

FireHydrant 的核心定位是 *service catalog 驅動的 IR platform* — 強調 *service ownership + runbook automation + retrospective workflow* 三角支撐、而不是只把 Slack 當 chat surface。底層是 *service catalog*（service / team / dependency / owner metadata）、incident 一宣告就自動關聯 affected service 跟 on-call team；上層是 *runbook engine*（trigger + action DAG）跟 *retrospective workflow*（template + facilitator + action item tracking）。跟 [incident.io](/backend/08-incident-response/vendors/incident-io/) 同層、差異在 *Teams-native* 而非 Slack-only — Microsoft 365 + Salesforce-heavy enterprise 是 FireHydrant 主場。跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 比是 *IR + retrospective platform* vs *paging platform*、覆蓋 lifecycle 更廣但 on-call 模組相對年輕。跟 [Rootly](/backend/08-incident-response/vendors/rootly/) 比走 *catalog-first* 而非 *AI / no-code first*。

關鍵張力：*service catalog 完整度* ↔ *runbook automation 黑箱* 是 FireHydrant 客戶最大的 trade-off。catalog 沒維護好、runbook 自動 page 錯 team、retrospective owner 找不到；catalog 維護成本又會被視為 platform team 負擔。要看清楚自己 *願意投多少 catalog 治理換多少 IR 自動化*。

## 本章目標

1. 整合 FireHydrant 到 Slack / Teams
2. 配置 incident lifecycle + severity matrix
3. 用 Runbook automation 自動化 standard response
4. 用 Retrospective facilitator 跑復盤
5. 評估 FireHydrant vs incident.io / Rootly

## 最短判讀路徑

判斷 FireHydrant deployment 是否健康、最少看四件事：

- **Runbook automation 範圍**：runbook 是否走版控（API / Terraform Provider）、trigger 條件是否有 staging dry-run、high-impact action（自動 page exec / 自動發 customer notification）是否走 *approval gate* 而非 fire-and-forget
- **Service catalog 完整度**：service / team / dependency / owner 是否齊全、stale entry 是否有 review cadence、incident declare 時 affected service dropdown 是否能立即定位、catalog 是否跟 [ServiceNow CMDB](/backend/09-performance-capacity/) / Backstage / Salesforce 同步
- **Retrospective workflow**：incident close 後是否自動觸發 retrospective、facilitator 是否指定、action item 是否寫回 Jira / Linear 並 track close-rate、template 是否區分 sev1 / sev2 不同深度
- **SSO + audit**：SCIM provisioning 是否跟 IdP 同步、admin / responder / viewer 三層角色是否區分、audit log 是否 export 到 [Splunk](/backend/07-security-data-protection/vendors/splunk/) 或 SIEM

四件事任一缺失、就是 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 邊界的待補項目。

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

## 核心取捨表

| 取捨維度      | FireHydrant                                  | incident.io                     | PagerDuty                          | Rootly                          |
| ------------- | -------------------------------------------- | ------------------------------- | ---------------------------------- | ------------------------------- |
| Chat 主場     | Slack + Teams 雙支援                         | Slack-first（Teams 後加）       | Slack / Teams（chat 非核心）       | Slack-first                     |
| 核心抽象      | Service catalog + runbook                    | Incident workflow + AI assist   | On-call schedule + paging          | No-code workflow + AI           |
| Retrospective | 內建 facilitator + template + action 追蹤    | 內建、AI assist 草稿            | 弱、靠 integration                 | 內建、AI summary                |
| Catalog       | 一級概念、service / team / dependency        | 有 catalog、深度較淺            | Service 概念存在、不強調 ownership | 有 catalog、強調 no-code 編輯   |
| On-call       | 後加模組、相對年輕                           | 內建、跟 incident workflow 整合 | 業界最成熟                         | 內建                            |
| 整合主場      | ServiceNow / Salesforce / Microsoft          | Linear / Notion / GitHub        | 廣泛、paging-centric               | Jira / Slack                    |
| 適合場景      | Enterprise + Teams + service ownership-heavy | Slack-native + 高速 startup     | Paging-first + 已有 IR tooling     | No-code / AI-forward + 中型團隊 |

選 FireHydrant 的核心訴求：*service ownership 是組織一級概念*（platform team / SRE 已維護 catalog）、*Microsoft 365 / Teams 是預設辦公 surface*、*retrospective + action item 追蹤要 first-class*。Slack-only + startup 速度優先走 incident.io；paging 是核心走 PagerDuty。

## 進階主題（按需閱讀）

### Status page 內建

子議題：不需另接 Statuspage / Instatus、Component / incident sync、Subscriber notification

### Cross-platform（Slack + Teams）

子議題：同帳號跨兩平台、Microsoft Teams enterprise 需求

### On-call 模組 + Service catalog

子議題：後加 module、service / team / dependency metadata 跟 incident 自動關聯

### Runbook automation（trigger + action DAG）

Runbook 是 trigger（severity 升級 / service 標籤 / 時間 elapsed）+ action（page team / 建 Zoom / 建 Jira / 發 customer notification / 更新 status page）的 DAG。production 設計要回答：*哪些 action 可以 fire-and-forget*（建 Zoom / 建 ticket）、*哪些要 approval gate*（發 customer notification / 自動 page exec）、*失敗回退是什麼*（action 失敗時 commander 是否會收到通知、還是默默 skip）。Runbook 走 API / Terraform Provider 版控、不在 console 直改 production。

### Service catalog + dependency

Catalog 一級欄位：service / owning team / on-call rotation / upstream dependency / downstream consumer / tier（critical / standard / experimental）。意義是 incident declare 時 *affected service* 一選、systems team + on-call + 通報範圍自動推導。catalog stale 是最大失敗模式 — team 重組沒同步、deprecated service 沒下架、ownership 落在離職員工身上。對應 [9 IT asset 模組](/backend/09-performance-capacity/) 的 CMDB / inventory 治理原則。

### ServiceNow / Salesforce 整合

FireHydrant 的 Microsoft / Salesforce 生態整合是 differentiator：incident 自動建 ServiceNow ticket（CMDB CI 關聯）、Salesforce case escalate 自動 declare incident、Customer Success 在 Salesforce 看到 affected account list。enterprise customer 常見部署模式。

### Signals（alerting layer）

FireHydrant Signals 是 alerting / paging layer、跟 PagerDuty 直接對打 — alert source（[Datadog](/backend/07-security-data-protection/vendors/datadog-security/) / Prometheus / [Sentry](/backend/07-security-data-protection/) etc）→ Signals → on-call rotation。意義是 *paging 不再需要外接 PagerDuty*、FireHydrant 一站涵蓋 alert → incident → retrospective。但成熟度仍年輕、PagerDuty paging 細節（escalation policy / override / global event routing）仍有差距。

### AI features

FireHydrant 後加 AI assist：incident summary 草稿、retrospective draft、similar incident suggestion。定位是 *assist*、不取代 commander / facilitator 判斷。production 用法限制在 *草稿 + human review*、不自動 publish 對外 communication。

## 排錯快速判讀

- **Severity matrix 不一致**：跨 team 定義不同、用 catalog default + onboarding
- **Runbook 沒觸發**：trigger 不滿足 / integration token 失效
- **Status page 不同步**：自動 / 手動 sync 配置錯
- **Retrospective 沒人做**：close 後沒 prompt / facilitator 沒指派
- **Service catalog stale**：team 重組沒同步、ownership 落在離職員工身上 — 設 quarterly review cadence、catalog 走 PR + owner attestation、跟 IdP / HR system join 偵測 orphan ownership
- **Runbook action 黑箱 fire-and-forget**：自動發 customer notification 結果發錯客群、自動 page exec 結果半夜誤叫 — high-impact action 走 approval gate、failure path 要顯式通知 commander、不能默默 skip
- **SSO sync drift**：SCIM 沒同步離職 user、admin 角色沒回收 — SCIM provisioning 必開、admin 角色走 break-glass、audit log export 到 SIEM 對賬

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

**FireHydrant 偏向 Microsoft Teams + Jira 生態的 IR 平台**：本案例庫尚無直接揭露 FireHydrant 使用細節的事故；可參照的閱讀脈絡是「企業套件 + 跨產品 IR」與「service ownership-heavy enterprise 跨產品依賴」的事故。

| 案例                                                                      | 對應主題                                                                        |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [Microsoft 365 cases](/backend/08-incident-response/cases/microsoft-365/) | Teams + 套件級事故的 IR 協作對照、ServiceNow ticket join 場景                   |
| [Azure AD cases](/backend/08-incident-response/cases/azure-ad/)           | 身份控制面事故的跨產品依賴對照、SSO drift 跟 service catalog ownership 失準對應 |
| [Atlassian cases](/backend/08-incident-response/cases/atlassian/)         | Jira / Confluence 生態事故、retrospective action item 寫回流程的失敗模式        |

待補 candidate：Snyk / Vercel / 大型 Microsoft 生態 customer 公開 story。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[incident.io](/backend/08-incident-response/vendors/incident-io/)、[Rootly](/backend/08-incident-response/vendors/rootly/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
