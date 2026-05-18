---
title: "Opsgenie"
date: 2026-05-01
description: "Atlassian on-call、跟 Jira / Statuspage 套件整合、JSM Premium migration 議題"
weight: 2
tags: ["backend", "incident-response", "vendor"]
---

Opsgenie 是 Atlassian 出品的 on-call 平台、承擔三個責任：alert routing + escalation policy、跟 Atlassian 套件（Jira Service Management / Statuspage / Confluence）深度整合、heartbeat monitoring（被動觀察 service 是否還在）。已被併入 Jira Service Management Cloud、原獨立服務逐漸 deprecated。

## 服務定位

Opsgenie 的核心定位是 *Atlassian 生態內的 on-call 元件*、跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 比、它的差異不在 *paging 能力本身*、而在 *跟 Jira Service Management / Confluence / Statuspage 的整合深度*：ticket、runbook、status page、incident 都在同一個身份體系（Atlassian Identity）內、不用跨 SaaS 串 SSO 跟 webhook。Atlassian-heavy enterprise 通常已經買了 JSM / Confluence / Statuspage、再買獨立 PagerDuty 等於多一條供應商線、ROI 不一定划算。

2025 年 Atlassian 公開宣布 *Opsgenie 將在 2027 年 4 月 EOL*、原 Opsgenie standalone 客戶要遷移到 [Jira Service Management Premium / Enterprise](https://www.atlassian.com/software/jira/service-management) 內建的 on-call 能力。這是現有 Opsgenie 客戶在 2025-2027 期間的最大議題、新案不該再選 Opsgenie standalone。

## 本章目標

1. 配置 Opsgenie team / schedule / escalation
2. 設計 alert routing 與 deduplication
3. 整合 Jira Service Management / Statuspage / Confluence
4. 用 Heartbeat monitoring 守護 cron / scheduled job
5. 評估 Opsgenie → JSM Cloud 遷移路徑

## 最短判讀路徑

判斷 Opsgenie deployment 是否健康、最少看四件事：

- **誰能 ack alert**：schedule rotation 是否真的有人在線、override 機制是否被濫用（永久 override 掩蓋人力缺口）、escalation policy 的 final step 是否有 fallback team 而非無限循環
- **跟 JSM migration plan**：是否已盤點 standalone Opsgenie 跟 JSM on-call 的 feature gap、現有 integration（Datadog / Prometheus webhook、Slack routing、custom API）在 JSM on-call 是否 parity、API token / Terraform config 的轉換路徑
- **Atlassian Identity 整合**：是否走 Atlassian Access（IdP SSO + SCIM provision + audit log）、還是停留在 Opsgenie 自己的 user store；後者在 migration / offboarding / compliance 都是坑
- **Slack notification routing**：alert routing 規則是 fan-out 到所有 team channel（吵雜）還是 priority-based（P1 → on-call DM + channel、P3 → channel only）；Slack 是事實上的 incident war room、routing 不對 SOC 就漏接

四件事任一缺失、就是 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 邊界的待補項目。

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

## 核心取捨表

| 取捨維度             | Opsgenie                                   | PagerDuty                            | incident.io                            | Grafana OnCall                  | JSM Premium on-call                   |
| -------------------- | ------------------------------------------ | ------------------------------------ | -------------------------------------- | ------------------------------- | ------------------------------------- |
| 生態錨點             | Atlassian（JSM / Confluence / Statuspage） | 獨立 SaaS、整合廣                    | Slack-first、incident workflow         | Grafana stack（OSS-friendly）   | Atlassian 內建                        |
| 計費模型             | 按 user / month                            | 按 user / month + add-on             | 按 user / month                        | OSS 免費 / Grafana Cloud 付費   | 包在 JSM Premium / Enterprise license |
| 身份整合             | Atlassian Identity / Access SSO            | 自家 + SAML / SCIM                   | Slack identity + SAML                  | Grafana auth + OAuth            | Atlassian Identity（原生）            |
| Runbook / postmortem | Confluence runbook + 基本 postmortem       | Runbook Automation + Jeli postmortem | 內建 incident timeline + retrospective | Grafana dashboard runbook（弱） | Confluence + JSM workflow             |
| 長期路徑             | 2027/4 EOL、移到 JSM on-call               | 持續演進、Process Automation 加深    | 持續演進、IR workflow 強化             | 持續演進、OSS 路線              | 跟 JSM 同步演進                       |
| 適合場景             | 既有 Opsgenie 客戶 migration 期、無新案    | 不在 Atlassian 生態、跨工具堆疊      | Slack-native IR、incident workflow 重  | OSS / 預算敏感、Grafana 已用    | Atlassian-heavy enterprise            |

選 Opsgenie 的核心訴求現在 *只有一個*：既有客戶在 EOL 前的 migration 緩衝期。新案應該直接走 JSM Premium on-call（已在 Atlassian 生態）、PagerDuty（不在 Atlassian 生態）或 incident.io（Slack-native）。

## 進階主題（按需閱讀）

### Heartbeat monitoring

子議題：主動 ping 監控、schedule heartbeat（cron / batch job 守護）。Heartbeat 是 *被動 alert* 的補位 — cron 跑完該打 ping、ping 沒到就 alert；常見坑是 network 路徑或 outbound proxy 擋掉 ping、cron 其實正常但 Opsgenie 收不到、變成 false positive 半夜叫人。

### Atlassian 整合深度

子議題：Issue creation / sync、SLA / OLA tracking、audit log。跟 PagerDuty + Jira webhook 比、Opsgenie 的差異是 *同身份體系 + native field mapping* — incident 直接綁 JSM ticket、Statuspage component 跟 Opsgenie service 同 schema、Confluence runbook 在 Opsgenie alert 內可直接 inline 預覽。

### Team-based routing 跟 service ownership

子議題：team 對應 service / component 的 ownership model、global schedule 跟 team-local schedule 的分層、cross-team escalation（DB team alert escalate 到 platform team）。跟 PagerDuty 比 Opsgenie 的 team 是 first-class concept、跟 JSM project / Confluence space 雙向綁、ownership 邊界比 PagerDuty service 更貼近組織結構。

### Atlassian Identity SSO + audit

子議題：[Atlassian Access](https://www.atlassian.com/software/access) 統一 IdP SSO（Okta / Azure AD / Google Workspace）+ SCIM 自動 provision / deprovision、audit log 集中。沒走 Atlassian Access 的 Opsgenie 是 *身份孤島* — 離職員工 JSM 已 deprovision 但 Opsgenie schedule 還在、半夜還會被 page。

### Opsgenie → JSM Cloud / JSM Premium on-call 過渡

子議題：原 Opsgenie 用戶遷移時程（Atlassian 官方公告 2027/4 EOL）、功能 parity 盤點（migration 前確認 integration / API / Terraform config 都有對應）、API 兼容（Opsgenie REST API 在 JSM 上是否保留 / 改路徑）。migration 不是換工具、是換產品架構 — schedule / escalation / integration / runbook 的 ID 都會變、要規劃 *parallel run 期* 而非 cutover。

## 排錯快速判讀

- **Alert 不觸發**：integration / API key / routing rule
- **Heartbeat false alarm**：cron 跑了但 ping 沒到 / network
- **Atlassian 整合斷裂**：JSM permission / project mapping
- **通知 missed**：mobile app / push / SMS provider
- **Escalation 跨時區壞掉**：schedule timezone 設錯（team timezone vs user timezone）、override 把全 24hr 都蓋掉、final step 沒 fallback team — 跑 game day 驗證實際 paging 路徑、不只看 config
- **Stale schedule**：有人離職但 schedule 沒撤、半夜叫到前同事；走 Atlassian Access SCIM auto-deprovision、或定期 schedule audit
- **Atlassian Cloud authentication trap**：API token 過期 / 換 region / Atlassian Access policy 變更導致 integration 全斷；token 走 secret manager、Atlassian Access policy 變更前先 dry-run integration
- **JSM migration drift**：migration 期間 standalone Opsgenie 跟 JSM on-call 兩邊 schedule / escalation 不同步、alert 兩邊都觸發或都沒觸發；parallel run 期要有 *single source of truth* 跟 reconciliation script

## 何時改走其他服務

| 需求形狀              | 改走                                                                    |
| --------------------- | ----------------------------------------------------------------------- |
| 不在 Atlassian 生態   | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)           |
| OSS 偏好              | [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) |
| Slack-native IR       | [incident.io](/backend/08-incident-response/vendors/incident-io/)       |
| Microsoft Teams + IR  | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)       |
| 新案、Atlassian-heavy | JSM Premium / Enterprise 內建 on-call（取代 Opsgenie standalone）       |

## 不在本頁內的主題

- Jira Service Management 完整 ITSM workflow / Atlassian Cloud admin / Statuspage 細節
- JSM Premium on-call 完整 feature set（屬 Atlassian product roadmap、跟 Opsgenie EOL 公告同期演進）
- Atlassian Access 完整 IdP / SCIM 設定（屬 identity 模組）

## 案例回寫

**Opsgenie 是 Atlassian 自家產品**：Atlassian 內部 incident routing / on-call 走 Opsgenie + Jira Service Management、其多租戶事故的協作流程是 Opsgenie 在大型 IR 場景的代表樣本。Atlassian-heavy enterprise 看這個案例的角度不是「PagerDuty 也能做」、而是「同身份體系 + JSM ticket / Confluence runbook / Statuspage 在 14 天事故內怎麼協作」— 這是 Opsgenie 在生態整合上的代表性場景。

| 案例                                                              | 對應主題                                          |
| ----------------------------------------------------------------- | ------------------------------------------------- |
| [Atlassian cases](/backend/08-incident-response/cases/atlassian/) | 14 天事故的 incident commander 輪值與 paging 節奏 |

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)、[Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/)
- 下游：[8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)
