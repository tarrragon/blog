---
title: "PagerDuty"
date: 2026-05-01
description: "On-call / alerting 主流 SaaS、IR 平台演化"
weight: 1
tags: ["backend", "incident-response", "vendor"]
---

PagerDuty 是 on-call / alerting 的事實標準 SaaS、承擔三個責任：alert routing + escalation policy + schedule、incident workflow + response play + runbook automation、postmortem 整合（Jeli 收購）。從 paging 工具演化成完整 IR 平台。

## 服務定位

PagerDuty 的核心定位是 *signal → human → action* 的中介層、把 alert source（觀測、SIEM、合成監控、cloud control plane）變成具體某個人手機震動 + 24 小時內可追蹤的 incident timeline。它是 *routing engine + on-call schedule 的事實標準*、定位有別於 alert source 和溝通平台。

跟上游 07 章的 detection stack 是直接 wire：[Splunk](/backend/07-security-data-protection/vendors/splunk/) ES app 產生的 Notable Event 透過 *Splunk-PagerDuty integration* 或 SOAR playbook 變成 PagerDuty incident、severity 直接帶過來；[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/) 的高分 rate-limit / bot block 透過 webhook 進 PagerDuty Event API v2、再經 Event Orchestration 判斷是丟 SecOps schedule 還是 platform schedule。這條鏈最常壞在 *severity 對應不一致*（Splunk medium 在 PagerDuty 變 P1）、跟 *integration 沒 deduplication key*（一次 attack 100 個 Notable Event 各起 100 個 incident）。

跟 [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) / [incident.io](/backend/08-incident-response/vendors/incident-io/) / [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) 的差異在 *ecosystem 跟 IR 模型* — PagerDuty 走 enterprise + AIOps + Process Automation 重資料堆疊、incident.io 走 Slack-native + collab-first、Opsgenie 綁 Atlassian、Grafana OnCall 是 OSS 自管。選 PagerDuty 的核心理由通常是 *AIOps + Process Automation + Jeli postmortem 整合的 ecosystem maturity*、不是 paging 功能本身。

關鍵張力：*alert volume* ↔ *responder burnout* 是 PagerDuty 客戶最常見 trade-off。為了「不漏 alert」把 grouping / deduplication 設很寬、結果 on-call 一週被叫醒 20 次、3 個月後人員流失。要看清楚自己 *容忍多少漏報換多少 responder sustainability*、不是把 alert source 全開到 PagerDuty 當保險。

## 本章目標

讀完本頁、讀者能判斷：

1. PagerDuty 在 alert pipeline 中承擔哪一段（routing / schedule / incident workflow）、哪些要外接（Slack 通訊、Jeli postmortem、Process Automation 對接 runbook）
2. Service / escalation policy / schedule 的 ownership 設計（誰建 service、誰改 escalation、誰能 override schedule）
3. Event Orchestration 的 deduplication / grouping / dynamic routing 設計、跟上游 SIEM 的 severity mapping 一致性
4. 何時用 PagerDuty、何時走 Opsgenie / incident.io / Grafana OnCall 的取捨

本頁不教 PagerDuty console 操作步驟、也不列 pricing tier — 那些 vendor 官方文件已經完整。本頁重點在 *判讀問題*：怎麼看一個 PagerDuty deployment 健康與否、哪些 config 是 high blast radius、跟上下游（07 detection / 04 observability / Jeli postmortem）怎麼接。

## 最短判讀路徑

判斷 PagerDuty deployment 是否健康、最少看四件事：

- **誰能 ack / escalate / resolve**：on-call rotation 有沒有人、escalation policy 第二層第三層是不是同一個人、有沒有 break-glass 流程（primary 失聯時誰補位）。schedule override 是否走 PR / approval、還是 console 直改沒留痕。
- **Escalation policy 設計**：每層 escalation timeout（5min / 10min / 15min）是否符合 SLO、是否有 *無人 ack 自動上報主管* 規則、跨時區 schedule 是否避免半夜 page 給 off-shift 區域
- **Event Orchestration 設定**：alert deduplication key 是否正確（同一 host + 同一 alert type 合併）、grouping rule 是否避免 alert storm、dynamic routing 是否依 service / severity / time 分軌到不同 schedule
- **SOAR / Process Automation playbook 觸發點**：哪些 incident 自動觸發 runbook（restart / rotate token / scale up）、approval gate 是否設在高風險動作、playbook 失敗有沒有 fallback 回 human page

四件事任一缺失、就是 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 的待補項目。

## 日常操作與決策形狀

### Service / team / escalation

PagerDuty 的 *service* 對應一個應用 / component、是 incident 的最小 ownership 單位。一個 service 綁一個 *escalation policy*（N 層、每層 X 分鐘 timeout）、一個 *schedule*（rotation + override）。production 部署用 *Terraform PagerDuty provider* 進版控、不在 console 直改 — 因為 schedule / escalation 是高 blast radius config、誤改可能讓半夜 alert 漏掉。Service 通常按 Service Ownership 對齊組織結構、不是按技術 stack 切：把一個微服務 stack 拆成 10 個 service 看似乾淨、但 incident 起來時 responder 要同時 ack 10 個 incident 對 SLO 不利、合理粒度通常是 *一個 product team 一個 service*。

### Event Orchestration + Response Play

Event Orchestration 是 alert → incident 的工程化路由層、處理 *deduplication / grouping / dynamic routing* 三件事。deduplication 用 *dedup_key*（同 host + 同 check type 合併、避免 100 個 alert 起 100 個 incident）、grouping 用 *time window + tag*（同一服務 5min 內多個 alert 合一）、dynamic routing 依 severity / time / service tag 分軌到不同 schedule。Response Play 則是 incident 起來後自動執行的動作 bundle — page additional responder、建 Slack channel、發 status page、call conference bridge。Response Play 應該走 PR review、不能 console 直加 — 一個誤設的 Response Play 可能在每個 P1 自動 page 整個 leadership。

### Severity mapping 跟上游一致性

上游 source（Splunk Notable Event / Datadog monitor / Cloudflare WAF alert）的 severity 跟 PagerDuty incident urgency 要 *對應表化*、不是各自為政。常見錯位：Splunk medium 在 PagerDuty 變成 high urgency（半夜被吵醒）、或 Cloudflare 高分 bot block 進來只標 low（真實 attack 漏報）。實務做法是寫一張 *severity translation table* 進 Event Orchestration、source severity → PagerDuty urgency 一對一寫死、變更走 PR review。對應 [Incident Severity Trigger](/backend/08-incident-response/incident-severity-trigger/) 的判讀標準。

## 核心取捨表

| 取捨維度        | PagerDuty                                  | Opsgenie                       | incident.io                           | Grafana OnCall                     |
| --------------- | ------------------------------------------ | ------------------------------ | ------------------------------------- | ---------------------------------- |
| 定位            | Enterprise IR platform、AIOps + automation | Atlassian 生態 paging          | Slack-native IR collaboration         | OSS / 自管 OnCall                  |
| 部署模型        | SaaS only                                  | SaaS（Atlassian Cloud）        | SaaS only                             | Self-hosted（Grafana stack）/ SaaS |
| Alert routing   | Event Orchestration（dedup + group + dyn） | Alert policy + integration     | Slack-first、簡化 routing             | Integrations + routes（OSS 等效）  |
| Schedule        | 強 — rotation / override / multi-tz        | 強 — 跟 Jira / Confluence 整合 | 中 — schedule 較簡化                  | 中 — 基本 rotation                 |
| Workflow / Play | Response Play + Process Automation         | Atlassian Automation           | Slack-driven workflow（強）           | 基本 webhook                       |
| Postmortem      | Jeli（收購、深度整合）                     | Confluence template            | 內建 postmortem + learning loop       | 外接                               |
| AIOps           | Machine Learning alert clustering、PRCC    | 基本 grouping                  | 無                                    | 無                                 |
| Pricing         | Per-user + 按 feature tier、enterprise 貴  | 按 user、Atlassian bundle 划算 | Per-responder、中等                   | OSS 免費 / Grafana Cloud 按 active |
| 適合場景        | Enterprise + 多 service + AIOps 需求       | Atlassian 已用 + 預算敏感      | Startup / mid-size + Slack-first 文化 | OSS-friendly + Grafana stack 已用  |
| 退場成本        | 高 — schedule / policy / Play 量多         | 中 — Atlassian 內可遷          | 中 — Slack 工作流綁深                 | 低 — OSS、可帶走 config            |

選 PagerDuty 的核心訴求：*多 service 大組織 + AIOps 對 alert storm 有 ROI + Process Automation 對接 runbook + Jeli postmortem 整合需求*。Slack-first 小組直接 incident.io、Atlassian-heavy 走 Opsgenie、預算敏感 OSS 走 Grafana OnCall。

## 進階主題

**Event Orchestration deduplication / grouping**：deduplication 跟 grouping 是兩個層次 — dedup 是 *同一事件多次發送只算一個*（用 dedup_key）、grouping 是 *多個相關事件合成一個 incident*（用 time window + service / tag）。設定太寬會漏 alert（不同 root cause 被合併、漏報重要事件）、設定太窄會 alert storm。實務做法是 *先寬後窄* — 上線初期用較寬 grouping 觀察、再依 false-merge 案例收窄。

**AIOps Machine Learning**：PagerDuty AIOps 用 ML 做 *alert clustering + probable root cause + change correlation* — 多個 alert 自動歸成 cluster、推測 root cause、跟近期 deploy / config change 對照。風險是 *黑箱*：ML 把不相關 alert 合一、SOC analyst 看不到原始事件就 ack；或把真實 incident 歸到 noise cluster。production 應該開、但 *保留 manual ungroup 機制 + 定期 audit cluster accuracy*。

**Process Automation + Splunk SOAR 整合**：PagerDuty Process Automation（前 Rundeck）做 runbook 自動執行 — restart / scale / rollback / rotate token。對接 [Splunk SOAR](/backend/07-security-data-protection/vendors/splunk/) 形成 *incident enrichment + auto-remediation* 鏈：Splunk SOAR 在 incident 起來時自動拉 context（user / host / IP recent activity）寫進 PagerDuty incident note、再依 playbook 觸發 PagerDuty Process Automation 做動作。高風險動作（disable account、rotate prod credential）必走 *approval gate*、不能 fire-and-forget。

**Jeli postmortem 整合（2023 收購後）**：PagerDuty incident resolve 後可以一鍵 import 進 Jeli、自動帶 timeline / responder list / Slack transcript、開始做 interview + narrative。對應 [Jeli vendor](/backend/08-incident-response/vendors/jeli/) — Jeli 走「learning from incident」方法論、不是只生 root cause report、強調 *near miss* 跟 *human factor* 也要分析。

**Service ownership / Service Standards**：PagerDuty Service Standards 把 service 的 *escalation policy / runbook link / business criticality / oncall coverage* 做成 checklist、organization 可以看哪些 service 沒達標。對 platform team 是治理工具、避免某 service「沒人 oncall 但有 alert source」。配對 [Repeated Incident Toil](/backend/08-incident-response/repeated-incident-toil/) 的反模式：service 沒人 own 但 alert 一直響、最後變 noise 被全部靜音、真實 incident 進來時也漏報。

**Status page 整合**：PagerDuty incident 可以自動同步到 [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/) 對外 status page、但 *自動同步* 是雙刃刀 — internal P1 不一定是 customer-facing、誤公告影響品牌。實務做法是 *只同步 customer-facing severity 的 incident*、用 Event Orchestration 加 tag (`customer_facing: true`) 才觸發 statuspage update、其他 incident 走人工 publish。

## 排錯與失敗快速判讀

- **Escalation 漏配 / primary 失聯沒人補**：escalation policy 第二層第三層是同一個人、或 off-shift 時無人 ack — 改成跨層異人 + break-glass policy（自動 page manager-on-call）+ 半年 audit
- **Schedule 跨時區算錯**：把 UTC schedule 套到亞太工程師、結果半夜 page off-shift — schedule 用 follow-the-sun rotation、或在 schedule layer 加 time restriction
- **Event Orchestration deduplication 太寬**：不同 root cause 的 alert 被 dedup 成同一 incident、漏報 — 收窄 dedup_key（加 service + alert_type）、保留 manual unmerge
- **Event Orchestration grouping 太窄**：同一事故 100 個 alert 各起 100 個 incident、alert storm、on-call 看不完 — 放寬 time window grouping、或開 AIOps clustering
- **AIOps ML 黑箱誤合**：真實 incident 被歸到 noise cluster、responder 沒看到 — 開 ML cluster audit dashboard、每月 sample review、保留 manual ungroup 機制
- **Slack notification stale**：PagerDuty Slack app token 過期 / channel 改名、incident 通知沒進 Slack — Slack integration health check + fallback channel + on-call 應該收 mobile push 不只看 Slack
- **Response Play 自動誤觸**：Play 設成 P1 自動 page leadership、結果一個 noise P1 把整個 C-level 半夜叫起來 — Play 必走 PR review、defaults to *additional engineer* not *leadership*、leadership page 走人工升級

## 何時改走其他服務

PagerDuty 不是所有 IR 場景都適合：

| 需求形狀              | 改走                                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Atlassian 生態        | [Opsgenie](/backend/08-incident-response/vendors/opsgenie/)                                                                                       |
| OSS / 預算敏感        | [Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/)                                                                           |
| Slack-first IR        | [incident.io](/backend/08-incident-response/vendors/incident-io/)                                                                                 |
| Microsoft Teams       | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/)                                                                                 |
| No-code workflow + AI | [Rootly](/backend/08-incident-response/vendors/rootly/)                                                                                           |
| Postmortem only       | [Jeli](/backend/08-incident-response/vendors/jeli/)                                                                                               |
| Status page only      | [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/) |

選對需求形狀比選 vendor 重要：startup 一開始走 Slack-native incident.io、規模上來 alert storm 多了再評 PagerDuty AIOps、Atlassian 重度用戶 Opsgenie bundle 划算。

## 不在本頁內的主題

- 各 integration 完整 setup / Pricing 細節 / AIOps ML 內部演算法
- Response Play 跟 Process Automation 的具體 playbook 實作（Rundeck DSL）
- Jeli 的 narrative + interview workflow（屬 postmortem 章節）

## 案例回寫

PagerDuty 公開 customer 多為大型 SaaS / 平台、下列案例可作為「paging 設計如何影響事故 detect → ack → mitigate 時間 + 怎麼跟 07 detection 鏈起來」的閱讀脈絡：

| 案例                                                                                                                                                       | 跟 PagerDuty 的關係（對照啟示）                                                                                                             |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| [GitHub cases](/backend/08-incident-response/cases/github/)                                                                                                | 大型平台事故的多輪 paging 與輪值、Event Orchestration grouping 設計 + 跨 service escalation                                                 |
| [Cloudflare cases](/backend/08-incident-response/cases/cloudflare/)                                                                                        | 控制面 vs data plane 的 paging 分軌、不同 severity 走不同 schedule + Response Play                                                          |
| [Slack cases](/backend/08-incident-response/cases/slack/)                                                                                                  | 通訊平台失效時 paging 通道的退路、PagerDuty mobile push 是 Slack-first IR 的 fallback                                                       |
| [Datadog cases](/backend/08-incident-response/cases/datadog/)                                                                                              | 觀測平台事故的 self-paging 與外部 fallback、AIOps clustering 避免 self-incident alert storm                                                 |
| [Microsoft Storm-0558 Signing Key Chain](/backend/07-security-data-protection/red-team/cases/identity-access/microsoft-storm-0558-2023-signing-key-chain/) | Splunk Notable Event 進 PagerDuty incident、SOAR playbook 自動 rotate Azure AD app credential、approval gate 在 force re-auth 動作          |
| [Snowflake 2024 Credential Abuse](/backend/07-security-data-protection/red-team/cases/data-exfiltration/snowflake-2024-credential-abuse/)                  | 異常 query volume 進 PagerDuty、Process Automation 觸發 Snowflake user disable + IP block、Response Play 同步 page legal / customer success |
| [Microsoft 365 2023 Auth Incident](/backend/08-incident-response/cases/microsoft-365/2023-suite-wide-authentication-incident/)                             | 認證鏈事故跨多 service、Event Orchestration grouping + dynamic routing 把 auth alert 集中到 identity team schedule                          |

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)、[Incident Severity Trigger](/backend/08-incident-response/incident-severity-trigger/)
- 平行：[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)、[Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/)、[incident.io](/backend/08-incident-response/vendors/incident-io/)
- 下游：[Incident Decision Log](/backend/08-incident-response/incident-decision-log/)、[Jeli](/backend/08-incident-response/vendors/jeli/)（postmortem 接手）
- 跨類：[Splunk](/backend/07-security-data-protection/vendors/splunk/)（Notable Event source）、[Cloudflare WAF](/backend/07-security-data-protection/vendors/cloudflare-waf/)（WAF alert source）
- 官方：[PagerDuty Documentation](https://support.pagerduty.com/)
