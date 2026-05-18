---
title: "Grafana OnCall"
date: 2026-05-01
description: "OSS-friendly on-call 平台、Grafana Labs 維護、Apache 2.0、Grafana IRM bundle 把 OnCall + Incident 收進一個 alert-to-resolve 流程"
weight: 3
tags: ["backend", "incident-response", "vendor", "grafana-oncall", "oss", "on-call"]
---

Grafana OnCall 是 Grafana Labs 維護的 *OSS-friendly* on-call 平台、源自 2021 年收購的 Amixr.io、以 Apache 2.0 授權釋出。它承擔三段責任：*alert routing + schedule + escalation*（PagerDuty 的 OSS 替代）、*Grafana 生態 alert 收斂*（Grafana / Alertmanager / Mimir / Loki alert 進統一 routing）、*phone / SMS notification* 透過 Twilio 等 provider。2024 年起 Grafana Labs 推出 *Grafana IRM (Incident Response Management) bundle*、把 Grafana OnCall + Grafana Incident（前 Grafana Incident Response & Communications）綁成一個 alert-to-resolve workflow、定位明確對標 PagerDuty 跟 incident.io 的整合 IR 路線。

## 服務定位

Grafana OnCall 的核心定位是 *Grafana 生態內的 on-call layer*、不是獨立 IR platform。底層產品線：*Grafana OnCall OSS*（self-hosted、Helm chart、Apache 2.0）、*Grafana Cloud OnCall*（SaaS、含在 Grafana Cloud Pro/Advanced）、*Grafana IRM bundle*（OnCall + Incident 整合、2024+ 主推路線）。對非 Grafana-heavy 環境也能單獨用、但跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 比 ecosystem 廣度不及。

跟 PagerDuty 比、Grafana OnCall 走 *OSS-first + 預算敏感*、核心 schedule / escalation / phone-call 功能對齊、但 advanced workflow（global event orchestration、business service mapping、analytics depth）較弱。跟 [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) 比、Grafana OnCall 不綁 Atlassian 生態、適合已用 Grafana stack 的團隊。跟 [incident.io](/backend/08-incident-response/vendors/incident-io/) 比、Grafana IRM bundle 在 alert routing 強、但 Slack-native incident channel 體驗 incident.io 仍領先。

關鍵張力：*OSS 路徑的維運成本* ↔ *商業 SaaS 的 SLA*。Self-hosted OSS 要自管 PostgreSQL / Redis / Celery worker / Twilio account、出事故時自家 on-call 平台不能掛（chicken-and-egg）；Grafana Cloud OnCall 解這層、但脫離了 OSS 自管的成本優勢。中型團隊通常走 Grafana Cloud、小型 OSS-first 團隊走自管 + Twilio。

## 本章目標

讀完本頁、讀者能判斷：

1. 自管 Grafana OnCall（Helm chart）vs Grafana Cloud OnCall vs Grafana IRM bundle 的取捨
2. 配置 schedule / escalation chain / Twilio phone-call 的最短路徑
3. Grafana / Alertmanager / 自家 webhook 進 OnCall 的 routing 設計
4. 跟 SIEM（[Splunk](/backend/07-security-data-protection/vendors/splunk/) / Elastic）webhook 整合的 alert 收斂模式
5. 評估 Grafana OnCall vs [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) / [incident.io](/backend/08-incident-response/vendors/incident-io/) 取捨

## 最短判讀路徑

判斷 Grafana OnCall deployment 是否健康、最少看四件事：

- **Slack / Teams integration**：on-call notification 是否進團隊主 chat channel、ack / resolve 是否能直接在 Slack 操作不切換 UI、@here / @channel 跟 phone-call 是否分層（低風險 Slack only、高風險才打電話）
- **Escalation chain**：N step escalation 是否覆蓋 *primary → secondary → manager*、每階是否有 timeout（5min / 15min / 30min）、節假日 / 跨時區 schedule 是否走 *rotation* 而非單人值班、override 機制是否清楚
- **Webhook integration to SIEM**：[Splunk](/backend/07-security-data-protection/vendors/splunk/) / Elastic Notable Event 進 OnCall 的 webhook 是否走 *correlation rule 過濾後* 才轉發、HMAC / token auth 是否正確、failed delivery 是否有 retry 跟 dead-letter queue
- **Grafana dashboard alert routing**：Grafana / Alertmanager alert 是否走 *severity-based routing*（critical / warning / info 分流到不同 escalation chain）、alert grouping / deduplication 是否啟用避免 alert storm、跟 [observability-reliability-incident-loop](/backend/08-incident-response/observability-reliability-incident-loop/) 的 signal-to-incident 邊界是否定義

四件事任一缺失、就是 [drills-and-oncall-readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 的待補項目。

## 日常操作與決策形狀

**Schedule + escalation chain**：rotation 走 *weekly* / *daily* / *custom*、可掛 calendar import（iCal / Google Calendar）做休假 override。Escalation chain 是 *N step + timeout* 結構（例：notify primary → 5min no ack → notify secondary → 15min no ack → notify manager + phone-call）。反例是 *single-step chain* — 一個人 ack 不到整個 incident 卡住、production chain 至少要 3 step + 跨時區 fallback。

**Alert grouping + Notification**：alert source 包含 *Alertmanager*（Prometheus / Mimir）、*Grafana alert*（unified alerting 推送）、*generic webhook*（自家 app / SIEM）、*Sentry / Datadog 等第三方*。Grouping 用 *integration template* 寫 Jinja2 抽欄位（service / severity / region）做 deduplication。Notification channel 分層：Slack / Teams 走低成本通知、Twilio phone-call / SMS 留給 P0 / P1、Mobile push 走 Grafana IRM mobile app。

**Grafana 生態整合**：Grafana Cloud 帳號內 OnCall 直接啟用、不另外 deploy。Grafana unified alerting 推 alert 到 OnCall integration、Loki / Tempo 的 metric-from-log / trace-anomaly alert 一條 pipeline 進 OnCall。對應 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/) 的 alert 出口。Grafana SLO（Service Level Objective）違反 burn rate threshold 也可直接路由到 OnCall escalation。

**Grafana IRM bundle**（2024+）：Grafana 把 OnCall（alert routing）+ Incident（incident lifecycle / war room / timeline）打包、目標是把 *alert paged → IC declared → channel created → timeline auto-recorded → post-incident review* 收進一個 console。對 Grafana-heavy 環境的吸引力是 *少一個 vendor seam*；對 Slack-native 團隊則跟 incident.io / FireHydrant 競爭、要看 Slack 體驗深度。

**OnCall webhook 整合 SIEM / 第三方**：generic webhook integration 接 [Splunk](/backend/07-security-data-protection/vendors/splunk/) Notable Event、Elastic Security alert、Datadog monitor、自家 app exception。Webhook payload 走 *integration template* 轉成 OnCall alert 欄位、加 routing label 進對應 escalation chain。注意 *webhook auth* 走 token / HMAC、不要用 anonymous webhook 接外網 — 對應 [incident-workflow-automation-boundary](/backend/08-incident-response/incident-workflow-automation-boundary/) 的入口治理。

**Maintenance mode**：planned maintenance window 期間 suppress alert、避免 deploy / DB migration 觸發大量假 alert。設定 *integration-level mute* 或 *route-level mute*、附 reason 跟 expiry time、不要無限期 mute（容易遺忘變盲點）。

**Mobile app**：Grafana IRM mobile app（iOS / Android）支援 push notification + ack / resolve / 加 note、replace 部分電話需求。但 phone-call 不可完全廢除 — 手機靜音 / 深夜值班 push 不一定醒、P0 仍需 Twilio 多次呼叫升級。

**自管部署**：Helm chart 部署、依賴 *PostgreSQL*（state）+ *Redis*（cache / Celery broker）+ *Celery worker*（background job）+ *Twilio account*（phone / SMS）+ TLS domain。Production checklist：PostgreSQL 走 managed service（RDS / Cloud SQL）避免自管 DB on-call 平台兩層 chicken-and-egg、Redis 走 managed、Helm values 走 GitOps 版控、Twilio account 走獨立 sub-account 避免 quota 跟其他服務搶。

## 核心取捨表

| 取捨維度              | Grafana OnCall                                | PagerDuty                                 | Opsgenie                                 | incident.io                            |
| --------------------- | --------------------------------------------- | ----------------------------------------- | ---------------------------------------- | -------------------------------------- |
| 計費模型              | OSS 自管免費 / Cloud 含在 Grafana Cloud 套餐  | Per-user / 月、advanced tier 加價         | Per-user / 月（Atlassian 套餐）          | Per-user / 月、Slack-native focus      |
| 部署模型              | Self-hosted (Helm) / Grafana Cloud SaaS       | SaaS only                                 | SaaS only                                | SaaS only                              |
| 授權                  | Apache 2.0 OSS                                | 商業 SaaS                                 | 商業 SaaS                                | 商業 SaaS                              |
| Advanced workflow     | 基本 schedule + escalation、analytics 較弱    | 業界最強（global orchestration / RBA）    | 中等（Atlassian Jira / Confluence 整合） | Slack incident channel + post-incident |
| Integration ecosystem | Grafana / Alertmanager 強、第三方靠 webhook   | 700+ 原生 integration                     | Atlassian 生態深、Jira / Confluence 一線 | Slack-native、深度有限但體驗好         |
| Phone / SMS           | Twilio（自配 account / OSS 路徑要自管）       | 內建、跨地區 carrier 覆蓋廣               | 內建、Atlassian 計費                     | 內建、focus 在 Slack ack 多於電話      |
| Slack 體驗            | Slack integration 基本（notify / ack）        | Slack integration 完整                    | Slack integration 中等                   | Slack-native、incident channel 自動建  |
| 跨平台 IR             | Grafana IRM bundle（OnCall + Incident）2024+  | PagerDuty Incident Workflows              | Jira Service Management incident         | incident.io Catalog + workflow         |
| 適合場景              | Grafana-heavy / OSS-first / 預算敏感          | Enterprise / 跨產品線 / 高 SLA            | 已用 Atlassian / Jira Service Management | Slack-first / startup-to-midsize       |
| 退場成本              | 低 — OSS 路徑可帶走 config、Cloud 也有 export | 中-高 — escalation policy / workflow 量多 | 中 — Atlassian 套餐綁定                  | 中 — Slack workflow 客製化深度         |

選 Grafana OnCall 的核心訴求：*OSS-friendly / 預算敏感 / Grafana 生態已是觀測平台主力*、能接受 advanced workflow 較弱（或預期不需要）、自管路徑能投入 PostgreSQL / Redis / Twilio account 維運。Enterprise + 高 SLA + 跨產品線 ecosystem 廣度需求仍走 PagerDuty。

## 進階主題

**Grafana IRM bundle 的整合決策**：OnCall（alert routing）+ Incident（incident channel / timeline / post-mortem）打包後、IR workflow 收在一個 console。決策點是 *是否已用 Slack 做 incident channel*、若團隊 Slack incident workflow 成熟、IRM Incident 的 channel 自動建可能跟現有 [incident-communication](/backend/08-incident-response/incident-communication/) 模式衝突；若還沒成熟、IRM bundle 是最短路徑。

**OnCall webhook 整合 SIEM 的 alert 收斂模式**：[Splunk](/backend/07-security-data-protection/vendors/splunk/) ES Notable Event / Elastic Security alert 不該直接打 OnCall — 噪音太大會造成 [alert-fatigue-and-signal-quality](/backend/07-security-data-protection/blue-team/alert-fatigue-and-signal-quality/) 問題。實務做法：SIEM 端先走 *correlation rule + risk-based threshold*、只有 high-confidence finding 才 webhook 到 OnCall、低風險走 Slack notification channel 給 SOC analyst triage。

**Maintenance mode 跟 deploy 流程的整合**：deploy pipeline 在 production rollout 前 call OnCall API 開 maintenance window（mute 特定 integration / route）、deploy 完成或失敗 rollback 後關閉。避免 deploy 期間 false alert 把 on-call 叫醒、但要設 *max maintenance duration*（例 1hr 自動 expire）避免長 window 變盲點。

**OSS 自管的 chicken-and-egg**：自管 OnCall 部署本身的 monitoring 不能依賴 OnCall — OnCall 掛了 alert 進不來、on-call 不知道 OnCall 掛了。實務做法：OnCall infra 的 monitoring 走另一條 *bootstrap alert*（直接 Twilio API call + email-to-pager fallback）、或保留小規模 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) free tier 做 backstop。

## 排錯與失敗快速判讀

- **Webhook 沒觸發 / alert 沒進來**：integration URL 錯（環境變數沒帶 base URL）、token / HMAC auth 設錯、source 端 webhook payload format 不對（沒走 integration template mapping）— 檢查 OnCall integration log + source webhook delivery log 對齊
- **Slack notification stuck / 不出現**：Slack OAuth token 過期、Slack workspace permission 變更、OnCall Slack bot 沒被 invite 進 channel — 重 OAuth + 確認 bot membership
- **Twilio quota 用完 / phone-call 失敗**：Twilio account balance 不足 / 沒升級 trial / 地區 carrier 限制 — 看 Twilio dashboard balance + delivery log、A2P 10DLC 註冊跟地區 toll-free 預先設定
- **Schedule overlap / on-call 漏排班**：rotation override 配錯、calendar import 沒同步、時區誤判（UTC vs local）— 用 OnCall schedule preview 跑 7-day forward 檢查
- **Notification delay / 來得慢**：provider latency（Twilio / Slack / FCM push）、Celery worker queue backlog（自管路徑）、escalation timeout 設太長 — 自管路徑檢查 Celery queue length + worker count
- **Self-hosted upgrade gotcha**：Helm chart major upgrade 帶 DB schema migration、跳版升級失敗、PostgreSQL extension 缺 — 走 staging environment 跑 migration + 備 rollback DB snapshot、不直接 production helm upgrade
- **Maintenance mode 沒到期 / 變盲點**：mute 沒設 expiry / reason、deploy 完成沒清 mute — maintenance window 強制設 max duration、weekly review mute 清單

## 何時改走其他服務

| 需求形狀               | 改走                                                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 進階 IR workflow / RBA | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)                                                                                     |
| Atlassian 生態 / Jira  | [Opsgenie](/backend/08-incident-response/vendors/opsgenie/)                                                                                       |
| Slack-native incident  | [incident.io](/backend/08-incident-response/vendors/incident-io/)                                                                                 |
| 商業 SLA / Enterprise  | PagerDuty / Opsgenie                                                                                                                              |
| Post-incident learning | [Jeli](/backend/08-incident-response/vendors/jeli/)（PagerDuty 收購）                                                                             |
| Status page (對外溝通) | [Atlassian Statuspage](/backend/08-incident-response/vendors/atlassian-statuspage/) / [Instatus](/backend/08-incident-response/vendors/instatus/) |

## 不在本頁內的主題

- Twilio account 申請 / A2P 10DLC 註冊 / 地區 carrier 設定細節
- Helm chart values 完整 reference（看官方 docs）
- Grafana Cloud OnCall pricing tier 對照
- Grafana unified alerting 規則語法（屬 observability 範圍、見 [Grafana Stack](/backend/04-observability/vendors/grafana-stack/)）
- Grafana Incident 的 channel / timeline 細節（屬 IRM bundle 另一半、本頁聚焦 OnCall）

## 案例回寫

Grafana OnCall 在 08 案例庫沒有直接 vendor-level 事件、本案例庫的多數事故主角是 Slack / GitHub / Cloudflare / AWS 等基礎設施。Grafana OnCall 的對照位置在 *OSS-first organization / Grafana-heavy 監控環境* 的 IR routing 設計、相關 case 的啟示如下：

| 案例方向                                                                                                   | 跟 Grafana OnCall 的關係（對照啟示）                                                                          |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| OSS-first / Grafana-heavy 觀測環境                                                                         | Alertmanager / Mimir / Loki alert 進 OnCall 是最短整合路徑、escalation chain 走 Grafana SLO burn rate trigger |
| 預算敏感的中型團隊                                                                                         | Self-hosted OnCall + Twilio account 是 PagerDuty 的 OSS 替代、要算 PostgreSQL / Redis 維運成本是否真的省      |
| Slack-only IR workflow vs Grafana IRM                                                                      | Grafana IRM bundle 把 incident channel 收進 console、跟 incident.io / Slack-native workflow 二選一            |
| Vendor 依賴出事（[vendor-dependency-incident](/backend/08-incident-response/vendor-dependency-incident/)） | OnCall 自身是 vendor、自管路徑要設 bootstrap alert、Cloud 路徑要評估 Grafana Labs SLA 跟 backup paging        |

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)、[Incident Workflow Automation Boundary](/backend/08-incident-response/incident-workflow-automation-boundary/)
- 平行：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)、[Opsgenie](/backend/08-incident-response/vendors/opsgenie/)、[incident.io](/backend/08-incident-response/vendors/incident-io/)、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)、[Rootly](/backend/08-incident-response/vendors/rootly/)
- 下游：[Grafana Stack](/backend/04-observability/vendors/grafana-stack/)（alert source）、[Observability ↔ Reliability ↔ Incident Loop](/backend/08-incident-response/observability-reliability-incident-loop/)
- 跨模組：[Splunk](/backend/07-security-data-protection/vendors/splunk/)（SIEM webhook → OnCall）、[Vendor Dependency Incident](/backend/08-incident-response/vendor-dependency-incident/)（OnCall 自身 vendor 風險）
- 官方：[Grafana OnCall Documentation](https://grafana.com/docs/oncall/)
