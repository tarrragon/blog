---
title: "PagerDuty → Opsgenie：Atlassian 全家桶整合 vs Opsgenie 2027 EOL 的 vendor consolidation 取捨"
date: 2026-05-19
description: "PagerDuty → Opsgenie 是 Type A phased schema translation、但 Atlassian 已宣布 Opsgenie 2027-04 EOL — 這條 migration 只在 Atlassian-heavy org + 明確 JSM unification roadmap 下成立、本質是 PD → Opsgenie → JSM Cloud 的雙 hop migration。本文走 6 維 audit（Schema Medium-High 其他 Low）、PagerDuty ↔ Opsgenie ↔ JSM field mapping 對照、5 production 踩雷（escalation step / Heartbeat 缺對應 / integration key dedup 重設 / schedule 時區 / Atlassian Identity SSO 整合）、何時直接走 PD → JSM 跳過 Opsgenie"
tags: ["backend", "incident-response", "vendor", "migration", "type-a", "phased-translation"]
---

| PagerDuty 物件          | Opsgenie 對應        | JSM Cloud 對應（2027 後） | 翻譯難度       |
| ----------------------- | -------------------- | ------------------------- | -------------- |
| Service                 | Integration          | Service registry          | 低             |
| Escalation Policy       | Escalation           | Escalation                | 中             |
| Schedule（layer model） | Schedule（rotation） | Schedule                  | 中-高          |
| User                    | User                 | Atlassian Account         | 中（IdP 整合） |
| Team                    | Team                 | JSM Team                  | 低             |
| Event API v2            | Alert API            | JSM REST API              | 中             |
| Event Orchestration     | Policy               | Routing rule              | 中-高          |
| Status Page             | Statuspage（同產品） | Statuspage                | 低             |
| Postmortem              | （無原生）           | （Confluence template）   | 高（要外接）   |

這張對照表是 PagerDuty → Opsgenie migration 的 *表面 schema mapping*、但表前必須先處理一個前提：**Atlassian 2025 公開宣布 Opsgenie 將在 2027-04 EOL**、現有 Opsgenie 客戶會被遷往 [Jira Service Management Premium / Enterprise](https://www.atlassian.com/software/jira/service-management) 內建的 on-call 能力。這條 migration 不是 PagerDuty ↔ Opsgenie 的 vendor swap、是 *PagerDuty → Opsgenie → JSM Cloud* 的雙 hop migration。

## 誰應該考慮這條 migration

| 適用條件                                                       | 不適用                                                                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 已是 Atlassian-heavy ecosystem（JSM / Confluence / Bitbucket） | 純 Slack-first org（考慮 [→ incident.io](/backend/08-incident-response/vendors/pagerduty/migrate-to-incident-io/)） |
| 已買 JSM Premium / Enterprise、Opsgenie 是 entitled benefit    | 新案、無 Atlassian 基礎                                                                                             |
| 願意走 PD → Opsgenie → JSM 雙 hop（或直接跳 JSM）              | 不想多次 migration、想一步到位                                                                                      |
| Atlassian Identity / Cloud admin 已成熟                        | SSO / IdP 跟 Atlassian 沒整合好                                                                                     |
| OSS / 自管不可行（compliance / 規模）                          | 規模 < 20 SRE（[Grafana OnCall](/backend/08-incident-response/vendors/grafana-oncall/) 或 PagerDuty Lite 已足夠）   |

對 *新案*：不要選 Opsgenie standalone。直接評估 PagerDuty → JSM Premium 一次到位、或 PagerDuty → incident.io（如果 Slack-first 是 driver）。

對 *已是 Opsgenie 客戶但從 PagerDuty 遷入的 org*（少見、通常是 acquisition consolidation）：本文仍適用、但要把 Phase 5 EOL 路徑放在規劃裡。

## 為什麼是 Type A（schema 為主）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#6-維-diff-dimension-audit)：

| 維度        | 評          | 說明                                                                                   |
| ----------- | ----------- | -------------------------------------------------------------------------------------- |
| Schema      | Medium-High | escalation policy / schedule / integration / API endpoint 都有 mapping、但概念對應度高 |
| Operational | Low         | 同為 alert routing + on-call schedule 平台、ops 模型一致                               |
| Paradigm    | Low         | 同 paging-first paradigm                                                               |
| Components  | Low         | 都是 SaaS 平台、no multi-tool decomposition                                            |
| App change  | Medium      | webhook URL / integration key 要換、application code 改動少                            |
| Topology    | Low         | 都是 cloud SaaS                                                                        |

Schema = Medium-High（其他 Low） → **Type A phased translation**。比標準 Type A 11-12 章短、因 paradigm 不變、不需要重新訓練 SRE 行為。

## Driver：Atlassian vendor consolidation

從 PagerDuty 遷入 Opsgenie 的核心 driver 是 *Atlassian 全家桶整合* — 已經買 JSM + Confluence + Bitbucket + Statuspage 的 org、再買 PagerDuty 等於多一條 SaaS 採購線、SSO 配置、billing 對接、user provisioning 重複。Opsgenie（或未來 JSM Premium 內建 on-call）走 Atlassian Identity、跟 JSM ticket / Confluence runbook / Statuspage component 同一個身份體系、incident 跟 ticket / status update 跨產品聯動不用 webhook chain。

這條 consolidation 拉力的具體形態：

- **單一 SSO + provisioning**：Atlassian Cloud admin 一處 manage user / group / SSO、不需要 PagerDuty 獨立 SCIM + IdP 配置
- **Ticket ↔ incident bi-directional**：JSM ticket 升級成 incident、incident 自動建 ticket、close incident 自動 close ticket、不用 PagerDuty Jira integration plugin
- **Runbook 跟 incident channel 同產品**：Confluence runbook 從 Opsgenie alert 直接 link、不用維護兩套權限
- **Status Page 共用 component model**：Statuspage 已是 Atlassian 產品、Opsgenie incident 觸發 Status Page update 不用 webhook（內部 event）
- **Billing 整合**：Atlassian Cloud subscription bundle、CFO 不用對 5 條獨立 SaaS invoice

這條 driver 在 PagerDuty 後加的 Status Updates / Jira plugin / Postmortems 模組下被部分削弱、但本質仍是 *Atlassian 是主、PagerDuty 是外掛* vs *全部都在 Atlassian* 的差別。

## Type A phased migration（5 phase）

### Phase 1：Schema 對照 + 識別差異

把 PagerDuty 當前 config 完整 export（API endpoint `/services`、`/escalation_policies`、`/schedules`、`/users`、`/teams`、`/integrations`、`/event_orchestrations`）、對照上方 schema mapping table、識別 *無 1:1 對應的物件*：

- Event Orchestration rule 對 Opsgenie 的 Policy + Routing rule（複雜 routing 要拆）
- Schedule layer model 對 Opsgenie 的 Rotation + Override（layer 疊加要展平）
- PagerDuty AIOps / Process Automation 對 Opsgenie 的 *無對應* — 要評估是否丟掉這條能力

完成標準：寫出 PagerDuty config inventory + Opsgenie target spec、確認所有物件都有 mapping path（即使是「捨棄」也算 mapping）。

### Phase 2：Schedule + Escalation 移植

PagerDuty schedule 是 layer 疊加（primary + secondary + override + restriction）、Opsgenie 是 *單一 rotation list + override*。簡單 schedule（單一 weekly rotation + 偶爾 override）直接對應、複雜 schedule（follow-the-sun + holiday + restriction time-of-day）要展平：

- PagerDuty `/schedules/{id}` 拉完整 `final_schedule`、用 *實際輪值結果* 重建 Opsgenie rotation
- 多層 schedule 在 Opsgenie 拆成多個 rotation、用 escalation chain 串
- Restriction layer 在 Opsgenie 沒對應、要在 rotation rule 內 inline 時段限制

Escalation policy 多 step + level-based timeout 在 Opsgenie 是 *step-based escalation*、直接對應、但每步 timeout 跟 acknowledge behavior 要 retest。

完成標準：on-call rotation 在 Opsgenie 跑一週、跟 PagerDuty parallel 對比實際 paging 行為一致（同一個 alert 兩邊都叫到對的人）。

### Phase 3：Integration / Webhook 改線

每個 alert source（Splunk / Datadog / Cloudflare WAF / cloud control plane / synthetic monitor）的 webhook URL 從 PagerDuty Event API 換成 Opsgenie Alert API：

- Endpoint：`https://events.pagerduty.com/v2/enqueue` → `https://api.opsgenie.com/v2/alerts`
- Auth：PagerDuty `routing_key` → Opsgenie API key（per-integration）
- Deduplication：PagerDuty `dedup_key` → Opsgenie `alias`（行為相同、欄位名不同）
- Severity mapping：PagerDuty `severity`（info/warning/error/critical） → Opsgenie `priority`（P1-P5）

這 phase 的工作量主要塊不是 schema 翻譯、是 *每個 integration 都要重新測 deduplication + severity*。新 integration key 配上去後第一週要密切監控、避免 dedup key 重設導致同事故開 100 個 incident。

完成標準：所有 alert source 都接 Opsgenie、PagerDuty 端 alert volume 降為 0。

### Phase 4：Cutover + dual ops period

2-4 週 dual ops：alert 都進 Opsgenie 為主、PagerDuty 留作 backup paging（同樣 alert 也 mirror 進 PD、但 SRE response 全在 Opsgenie）。確認沒漏 alert、escalation 行為正確、Atlassian 整合（JSM ticket / Confluence runbook / Statuspage） wire 通。

完成標準：dual ops 4 週無漏 alert、SRE 沒回去 PagerDuty UI 操作。

### Phase 5：PagerDuty 退役 + Opsgenie → JSM EOL 路徑規劃

PagerDuty 退役後立即進入 *Opsgenie 2027 EOL 倒數*。這 phase 不是 PD migration 的尾巴、是 *下一條 migration 的起點*：

- 2025-2026：Atlassian 推 JSM Premium 的 on-call 能力、提供 Opsgenie → JSM 遷移工具
- 2026-2027：實際遷 Opsgenie → JSM、schedule / integration / API 改線
- 2027-04：Opsgenie EOL、所有 traffic 必須在 JSM

完成標準：PagerDuty 帳號取消、Opsgenie deployment 健康運作 + JSM unification roadmap 寫進 2026-2027 SRE OKR。

## 5 個 production 踩雷

### 1. Escalation step routing 行為差異

PagerDuty escalation policy 的 step timeout 是 *每步獨立 acknowledge window*（step 1 等 5 分鐘沒人 ack → step 2 等 5 分鐘沒人 ack → ...）、Opsgenie escalation 的行為類似但 *step 之間的 notification cumulative behavior* 不同 — Opsgenie 預設 step 2 觸發後 step 1 的人 *仍會收到 notification*（除非設定 step 1 not yet acknowledged 才繼續）。修法是寫測試 case 對比 alert 在兩邊 escalation 過程的 notification timeline、調整 Opsgenie escalation rule 的 acknowledge propagation 設定到跟 PD 一致。

### 2. Heartbeat monitoring 在 PagerDuty 沒對應

Opsgenie Heartbeat 是 *被動 monitoring* — service 必須定期 ping 一個 endpoint、超過 interval 沒 ping 就觸發 alert、用來監控 cron job / scheduled task 是否還在跑。PagerDuty 沒原生 Heartbeat、通常用 external service（Healthchecks.io / Dead Man's Snitch）。從 PD 遷入 Opsgenie 時、把這些 external service 收回 Opsgenie Heartbeat、減少 SaaS 數量。但反向（從 Opsgenie 遷出時要先把 Heartbeat dependency 外接）是不同問題、不在本篇 scope。

### 3. Integration key 改線時 deduplication 重設

PagerDuty `dedup_key` → Opsgenie `alias` 行為相同、但 *新 integration key 上線後第一個 alert 不會跟舊 PD incident 對應* — 同一個事故在 PD 上是 incident #5234、在 Opsgenie 上是新 alert 從零開始。Phase 3 切換時間點如果剛好遇到 active incident、會分裂成兩個系統內各自的 incident、SRE confusion。修法是 cutover 時間點選擇在 *known quiet period*（一般是週末早上、避開 deploy 時段）、並接受第一個切換期間有手動 reconcile 的工作。

### 4. Schedule 時區處理

PagerDuty schedule 的 timezone 是 *per-layer* 設定（layer 1 可以 PST、layer 2 可以 GMT）、Opsgenie rotation timezone 是 *per-schedule* 設定。Follow-the-sun schedule（亞太 / 歐洲 / 美洲三層）在 PD 是三 layer 各自 timezone、在 Opsgenie 要拆成三個 schedule 各自設定 timezone 用 escalation 串。Daylight saving transition 是另一個高風險點 — PD 跟 Opsgenie 在 DST 切換週的行為要分別測試。

### 5. Atlassian Identity SSO 整合

如果 org 既有 SSO（Okta / Azure AD）已經跟 PagerDuty 整合、遷 Opsgenie 時要 *重新對接 Atlassian Identity*。Atlassian Cloud 的 SSO 是在 Atlassian admin 層設定、跟個別產品（Opsgenie / JSM）獨立。常見問題：

- PagerDuty user email 不一定等於 Atlassian account email（有人用 work email 註冊 PD、用 personal email 註冊 Atlassian）
- SCIM provisioning rule 要重寫、group / role mapping 重新設計
- Just-in-time user provisioning behavior 不同（PD 是即時、Atlassian 可能需要 admin 手動 approve）

修法是 Phase 1 schema mapping 時就把 user identity reconcile 列為獨立工作塊、不要假設 email 唯一對應。

## 容量與成本對照

| 項目             | PagerDuty                    | Opsgenie                             | JSM Premium（2027 後）         |
| ---------------- | ---------------------------- | ------------------------------------ | ------------------------------ |
| 計費模式         | Per-user / month、tier-based | Per-user / month、Free tier ≤ 5 user | JSM seat + on-call entitlement |
| Atlassian bundle | 獨立 SaaS                    | Atlassian Cloud subscription         | JSM Premium / Enterprise 內建  |
| AIOps            | Enterprise + add-on          | 弱（無原生 ML grouping）             | （roadmap）                    |
| Heartbeat        | 不適用                       | 內建                                 | 內建                           |
| Status Page      | 內建（Business tier+）       | Statuspage（同 Atlassian、單獨計費） | Statuspage 整合                |
| 隱性 EOL 風險    | 無                           | 2027-04 EOL                          | Atlassian 主推                 |

實際 TCO 對比 *不能只看 per-seat price* — 必須加上：

- Atlassian Cloud bundle discount（多產品同訂閱通常有 15-25% 折扣）
- PagerDuty AIOps + Process Automation 是否在用（如果在用、Opsgenie 沒對應、要外接成本）
- 雙 hop migration（PD → Opsgenie → JSM）的累計工程成本 vs 單 hop（PD → JSM 跳過 Opsgenie）

## 何時跳過 Opsgenie 直接 PD → JSM

對 *已是 Atlassian-heavy org* 但 *尚未用 Opsgenie* 的場景、Opsgenie 2027 EOL 表示 PD → Opsgenie → JSM 雙 hop 不划算。直接 PD → JSM Premium：

- 等 Atlassian 2026 公開 JSM 內建 on-call 的完整能力、確認 feature parity 跟 Opsgenie 相當
- 規劃 PD → JSM 一次 migration、結構接近本篇但 target 換成 JSM
- 風險：JSM 內建 on-call 在 2026 仍可能成熟度不夠、決策時點要看 Atlassian 公開 roadmap

對 *已是 Opsgenie 客戶* 的場景、本篇的 PD → Opsgenie 路徑仍適用、但 Phase 5 EOL 路徑規劃是必要 deliverable、不是 optional。

## 下一步路由

- 平行 batch：[PagerDuty → incident.io](/backend/08-incident-response/vendors/pagerduty/migrate-to-incident-io/)（Type E、Slack-first paradigm shift）/ [Atlassian Statuspage → Instatus](/backend/08-incident-response/vendors/atlassian-statuspage/migrate-to-instatus/)（Type B drop-in）
- 同 batch Type A：（待補、本篇是 batch 唯一 Type A）
- 上游：[8.10 Incident Workflow Automation Boundary](/backend/08-incident-response/incident-workflow-automation-boundary/)
- 下游：未來 Opsgenie → JSM Premium migration（2026-2027 寫）
- vendor 對照：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [Opsgenie](/backend/08-incident-response/vendors/opsgenie/) / [incident.io](/backend/08-incident-response/vendors/incident-io/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type A phased translation 結構說明）
