---
title: "Rootly"
date: 2026-05-01
description: "IR 自動化平台、no-code workflow + AI investigation、Slack-native + 200+ integration"
weight: 6
tags: ["backend", "incident-response", "vendor"]
---

Rootly 是 IR 平台、承擔三個責任：no-code workflow builder（拖拉式自動化）、AI 輔助 retrospective + timeline 整理、Slack / Teams 雙平台整合 + integration 數量最廣（200+）。產品迭代快、跟 [incident.io](/backend/08-incident-response/vendors/incident-io/) / [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) 三家構成 modern IR 平台主要選項。2023+ 加入 Rootly AI 模組做 incident enrichment 與 retrospective auto-draft、把 IR 平台從 *workflow 自動化* 推到 *AI-assisted investigation*。

## 服務定位

Rootly 的核心定位是 *Slack-native IR platform + no-code automation engine*、目標客戶是「想最大化降低 incident response toil」的 AI-first / engineering-led 組織。產品主軸：*no-code workflow builder*（IFTTT-style condition / action 鏈、不需工程 deploy）+ *Rootly AI*（incident summarization / enrichment / retrospective auto-draft）+ *Slack / Teams 雙平台對等支援*。

跟 [PagerDuty](/backend/08-incident-response/vendors/pagerduty/) 比、PagerDuty 是 alerting-first（on-call schedule + escalation 為核心）、Rootly 是 IR-process-first（incident workflow + retro 為核心）、兩家常一起用（PagerDuty 負責 page、Rootly 接 declare 後的 process）。跟 [incident.io](/backend/08-incident-response/vendors/incident-io/) 比、incident.io 走 *opinionated minimal*（流程固定、學習快）、Rootly 走 *configurable maximal*（workflow 可深度客製、學習曲線稍陡）。跟 [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) 比、FireHydrant 在 service catalog / runbook 結構更剛、Rootly 在 AI + integration 廣度更領先。

關鍵張力：*no-code 客製深度* ↔ *配置複雜度* 是 Rootly 客戶最大的 trade-off — workflow 可以做得很深，但配多了會出現 *workflow loop / 通知爆量 / AI summary 失準*，需要有人定期 review workflow inventory。

## 本章目標

讀完本頁、讀者能判斷：

1. 用 no-code builder 設計 incident workflow（trigger / condition / action）
2. 配置 severity matrix + role assignment
3. 用 Rootly AI 輔助 timeline + retrospective、了解 AI 失準的邊界
4. 整合 200+ tool（觀測 / cloud / collaboration / ticket / paging）
5. 評估 Rootly vs incident.io / FireHydrant / PagerDuty 的取捨

## 最短判讀路徑

判斷 Rootly deployment 是否健康、最少看四件事：

- **Slack workflow 入口統一**：`/rootly declare` 是否唯一 declare 入口、severity / service / role 是否在 declare 時就 bind、Slack channel naming convention（`inc-YYYY-MM-DD-slug`）跟 retention 是否設定
- **No-code automation 治理**：workflow 數量 / owner / 上次 review 時間是否有 inventory、有沒有 staging tenant 跑新 workflow、production workflow change 是否走 PR-like review
- **AI integration 邊界**：Rootly AI 用在哪些環節（incident summary / timeline enrichment / retrospective draft）、AI 輸出是否標記為 draft 而非 finalized、AI hallucination 的 human review gate 是否定義
- **SSO + audit + integration health**：SSO（Okta / Azure AD）+ audit log（誰改 workflow / 誰 close incident）是否開、Integration token 是否定期 rotate、Jira / Linear / GitHub PR / PagerDuty / Opsgenie 對接是否雙向同步

四件事任一缺失、就是 [Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/) 邊界的待補項目。

## 最短路徑

```bash
# 1. Slack / Teams install Rootly app
# 2. /rootly declare 建 test incident
# 3. 拖拉 workflow（severity → action）
# 4. Close + AI retrospective
```

## 日常操作與決策形狀

### No-code workflow builder

子議題：

- Trigger（severity / status / time）→ Action（page / message / ticket）
- Branch / condition / parallel
- Custom field bind

**IFTTT-style 邏輯**：workflow 是 *trigger → condition → action* 的 DAG、可以 branch / parallel / loop（loop 要小心、見排錯）。典型 production workflow：「severity SEV1 declared → page on-call via PagerDuty + create Jira ticket + post status page draft + invite security lead to Slack channel」。複雜度上限是「能 express 在 UI 拖拉上」、超過這個複雜度應該寫 webhook 接外部 orchestrator。

### AI retrospective + Slack/Teams workflow

子議題：

- 自動 timeline from Slack messages
- AI summary（what happened / contributing factor）
- 同 incident.io / FireHydrant Slack workflow
- Teams 平等支援
- Mobile app

**Rootly AI 的能力邊界**：AI 從 Slack channel 訊息抽 timeline、產生 *contributing factor* draft、列 *action item* candidate。產出是 *draft、不是 finalized retrospective* — IR lead 應該逐項驗證再 publish、AI hallucination 在 contributing factor / blame attribution 段最常出現（見排錯段）。

## 核心取捨表

| 取捨維度         | Rootly                                 | incident.io                   | FireHydrant                       | PagerDuty                        |
| ---------------- | -------------------------------------- | ----------------------------- | --------------------------------- | -------------------------------- |
| 核心定位         | No-code workflow + AI investigation    | Opinionated Slack-native IR   | Service catalog + runbook 結構    | Alerting + on-call schedule      |
| 客製化深度       | 高 — workflow builder + custom field   | 中 — 流程相對固定             | 中高 — runbook + catalog 模型清晰 | 中 — escalation 配置強、流程較輕 |
| AI 能力          | Rootly AI（summary / enrich / retro）  | AI 摘要（較新、範圍較窄）     | 較少強調 AI                       | AIOps（alert grouping）          |
| 平台支援         | Slack + Teams 對等                     | Slack-first（Teams 較弱）     | Slack + Teams                     | Slack / Teams / Mobile / Email   |
| Integration 廣度 | 200+（業界最廣）                       | 中（Slack ecosystem 為主）    | 中高                              | 最廣（paging ecosystem）         |
| 學習曲線         | 中陡 — 配置選項多                      | 緩 — 流程少                   | 中 — service model 要先想清楚     | 中 — escalation policy 要先設計  |
| 適合場景         | AI-first / 想自動化 toil / Slack-heavy | 小到中型、想快上手 + 流程一致 | 中大型、service ownership 清楚    | 任何需要強 paging 的團隊         |
| 退場成本         | 中 — workflow / custom field 量會綁    | 低 — 流程相對標準             | 中 — service catalog 綁定深       | 高 — schedule + integration 量大 |

選 Rootly 的核心訴求：*Slack-native IR + 想用 no-code + AI 把 incident process toil 自動化最大化*、且能投入時間維護 workflow inventory（避免 workflow sprawl）。需要重 paging 的團隊通常 Rootly + PagerDuty 並用（Rootly 不取代 PagerDuty 的 schedule + escalation）。

## 進階主題（按需閱讀）

### Rootly AI 深入

子議題：incident summary（給 stakeholder broadcast 用）、enrichment（自動補 service owner / recent deploy / related incident）、retrospective auto-draft（timeline + contributing factor + action item）。AI 輸出是 *draft*、需要 human review gate 才 publish。對 [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/) 的影響是「快、但要驗」、不能把 AI draft 直接當成 source of truth。

### No-code workflow 進階

子議題：condition expression（field / value / operator）、parallel branch、wait / delay、custom webhook action 接外部 orchestrator。複雜 workflow 應該 *先在 staging tenant 跑*、production workflow change 走 review。Workflow loop（A workflow 觸發 B、B 觸發 A）會在 misconfig 時出現、見排錯段。

### Ticket / PR / paging integration

子議題：Jira / Linear 雙向同步（incident close 同步 ticket、ticket update 帶回 Slack）、GitHub PR 自動連 incident（commit message 含 incident ID）、PagerDuty / Opsgenie alerting layer 對接（page 從 PagerDuty 來、process 在 Rootly 跑）。Integration token 失效是常見 silent failure、需要 monitoring。

### Integration 廣度

子議題：觀測（Datadog / Grafana / New Relic / Honeycomb）/ Cloud（AWS / GCP / Azure）/ Collaboration（Slack / Teams / Zoom）/ Ticket（Jira / Linear / GitHub）/ Status page

### Service catalog + Custom field

子議題：service / team / customer metadata、custom field 帶業務 context、workflow trigger by field

### On-call 模組

子議題：Rootly OnCall（schedule + escalation）、跟 IR workflow 同 app

## 排錯快速判讀

- **Workflow 行為不符**：trigger / condition 邏輯錯、看 workflow run log
- **AI summary / retrospective 失準**：Slack noise 多、AI 對 contributing factor / blame attribution hallucinate — 手動補 timeline、AI 輸出標記為 draft、由 IR lead 逐項驗證才 publish
- **Workflow loop / 通知爆量**：A workflow 觸發 B、B 又觸發 A、Slack 訊息或 ticket 暴衝 — 在 staging tenant pre-test、production workflow change 走 review、加 rate limit / loop detection
- **Slack notification overload**：每個 severity 都 broadcast 全公司 channel — 設 severity threshold、SEV3 以下走 team channel、SEV1/2 才 broadcast
- **Integration token 失效**：rotate / OAuth re-auth、加 integration health monitoring（token expiry alert）
- **Slack channel 亂**：naming convention（`inc-YYYY-MM-DD-slug`）/ retention 沒設、舊 incident channel 累積成千

## 何時改走其他服務

| 需求形狀            | 改走                                                              |
| ------------------- | ----------------------------------------------------------------- |
| Slack-only / 簡潔   | [incident.io](/backend/08-incident-response/vendors/incident-io/) |
| Microsoft Teams     | [FireHydrant](/backend/08-incident-response/vendors/firehydrant/) |
| Paging-first        | [PagerDuty](/backend/08-incident-response/vendors/pagerduty/)     |
| Learning-focused    | [Jeli](/backend/08-incident-response/vendors/jeli/)               |
| 自建 Slack workflow | Slack + GitHub Issues / Linear                                    |

## 不在本頁內的主題

- AI model / training detail / Pricing / 200+ integration 個別 setup

## 案例回寫

**Rootly 主打 Slack-native + AI-assisted IR**：本案例庫尚無直接揭露 Rootly 使用細節的事故；可參照的閱讀脈絡是「Slack-centric 協作 + 自動化 retro + AI-first 組織想 minimize IR toil」的服務事故。

| 案例                                                        | 對應主題                                       |
| ----------------------------------------------------------- | ---------------------------------------------- |
| [Slack cases](/backend/08-incident-response/cases/slack/)   | Slack-native IR 平台在通訊平台自身事故下的回退 |
| [Reddit cases](/backend/08-incident-response/cases/reddit/) | mid-size 平台升級事故的 retro 結構（對照素材） |

待補 candidate：NVIDIA / Figma / Canva 等 Rootly 公開 customer story。

## 下一步路由

- 上游：[Drills and On-call Readiness](/backend/08-incident-response/drills-and-oncall-readiness/)
- 平行：[incident.io](/backend/08-incident-response/vendors/incident-io/)、[FireHydrant](/backend/08-incident-response/vendors/firehydrant/)、[PagerDuty](/backend/08-incident-response/vendors/pagerduty/)
- 下游：[8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)
