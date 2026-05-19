---
title: "PagerDuty → incident.io：「On-call」是個 retconned word、同名不同 contract"
date: 2026-05-19
description: "PagerDuty → incident.io 不是 schema translation — 兩家的「on-call」字面相同、contract 不同（alert routing vs IR coordination + Slack-native + retrospective）。本文走 Type E paradigm shift、6 維 audit 顯示 paradigm / schema / operational 三軸 High、用 4-phase partial migration（不收斂、Phase 1-2 多數 org 停留）、5 個 production 踩雷（雙系統 state drift / severity 翻譯失真 / schedule layer 漏 / Slack channel 過載 / retrospective 斷層）、跟 PagerDuty Process Automation / AIOps 沒對應的 capability gap"
tags: ["backend", "incident-response", "vendor", "migration", "type-e", "paradigm-shift"]
---

「On-call」是個被 retconned 的詞。PagerDuty 用了十年定義它為 *alert routing + schedule + escalation* — 重點是「誰會被叫醒」。incident.io 2023 年推出 On-call 模組時保留了同一個詞、但 contract 變了：On-call 在 incident.io 是 *IR coordination + Slack-native workflow + retrospective integration* 的 paging 入口 — 重點是「被叫醒之後做什麼」。

這個語意 retroactive 是這篇 migration playbook 必須先講清楚的事。讀者打開比較表會看到「PagerDuty 有 schedule、incident.io 有 schedule、PagerDuty 有 escalation policy、incident.io 有 escalation policy」、以為這是一場 schema translation 文。實際上 schema 翻譯只是其中一個工作塊、更難的是 *org 的事故行為從「等 PagerDuty 叫」變成「在 Slack channel 內跑 lifecycle」*。

## 為什麼是 Type E（不是 Type A）

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/#6-維-diff-dimension-audit)：

| 維度        | 評     | 說明                                                                                                   |
| ----------- | ------ | ------------------------------------------------------------------------------------------------------ |
| Schema      | High   | service / escalation policy / schedule / integration 跟 incident / role / action / catalog 沒 1:1 對應 |
| Operational | High   | alert routing → Slack-native IR coordination + retrospective workflow                                  |
| Paradigm    | High   | 「alert someone」 → 「coordinate full incident lifecycle from declare to retro」                       |
| Components  | Medium | incident.io 整合 Slack / Linear / Jira / Confluence 變 multi-component                                 |
| App change  | Medium | webhook / integration key / IaC 都要改                                                                 |
| Topology    | Low    | 都是 cloud SaaS、無 sharding / region 議題                                                             |

三軸 High（schema / operational / paradigm）。按優先序 schema > paradigm > operational、預設會選 Type A。但這條優先序是 *audience-dependent heuristic* — 對「我要把 PagerDuty config 翻譯成 incident.io」的讀者選 Type A、對「我要把事故管理 paradigm 從 paging-first 變成 Slack-first」的讀者選 Type E。

決定因素是 *讀者最關心什麼*。從 PagerDuty 出發評估 incident.io 的 org 通常 *已經有 Slack channel 跑 IR* 的痛感（雙系統 state drift / context switching cost / Slack bot 補 PagerDuty 的能力斷裂）、進來找的是 paradigm 統一、不是欄位翻譯。schema translation 是工作量、但不是讀者來找答案的問題。所以選 **Type E paradigm shift** 結構、schema translation 抽出獨立段補充。

## 為什麼遷：IM-native coordination 的拉力

事故反應在已經 Slack 中心的 org 是 *從 Slack 自然發生* 的 — 觀測 alert 進 Slack、SRE 開 thread、PM 跳進來問影響、customer-facing team 在 incident channel 看通報、所有上下文都在 IM 內。PagerDuty 在這個 reality 下變成 *第二個 system of record*：incident 開在 PagerDuty 也開在 Slack、PagerDuty timeline 跟 Slack scroll 是兩條時間線、status update 要 mirror 兩次、責任分派在 Slack 講但要在 PagerDuty 點。

PagerDuty 注意到這個問題、後加了 Status Updates / Slack integration / Postmortem 模組想把 Slack 拉回 PagerDuty。但結構性還是 *PagerDuty 是主、Slack 是 mirror* — incident object 的 source of truth 在 PagerDuty、Slack 的訊息只是 attachment。對 *Slack-first* 的 org 來說這個 ownership 反了：Slack channel 才是事故進行中的 ground truth、PagerDuty incident 應該是 paging 入口的 artifact。

incident.io 設計上把這個關係翻過來：Slack channel 是 IR ground truth、incident object 是 channel 的 metadata 投影。declare incident 在 Slack、role 指派在 Slack bot prompt、status update 在 channel reply、retrospective 從 channel 訊息自動 stitch — incident.io dashboard 是 *管理視圖*、不是事故 *進行視圖*。On-call 模組加進來後、連 paging 入口也跟 IR coordination 收斂到同一個 system of record。

這個 pull 是這條 migration 的 *driver*。schema 翻譯只是把這條 pull 落地的工作。

## 4-phase partial migration（不收斂）

Type E paradigm shift 的特徵是 *不收斂* — 多數 org 不會把 PagerDuty 全退役、會停在某個 phase 變成穩定的 hybrid。下面 4 phase 是 *常見演進路徑*、不是 *必要完成步驟*：

### Phase 1：Slack-first response（paging 留 PagerDuty）

incident.io 接 PagerDuty incident webhook、PagerDuty 開 incident → incident.io 自動開 Slack channel、跑 response lifecycle（declare / role / status / close / retro）。PagerDuty 仍管 paging schedule + escalation、incident.io 管 response coordination。

這個 phase 的工作主要塊是：

- incident.io 跟 PagerDuty 雙向 webhook 接（PD incident.trigger → IO open channel、IO incident.resolved → PD ack）
- Slack workspace 整合（permissions、channel naming、stakeholder broadcast channel）
- Severity 對應表（PagerDuty P1-P5 對 incident.io SEV1-SEV4、語意 reconcile）
- 跑 2-4 週 dual ops、訓練 SRE 在 Slack 內跑 lifecycle、不要回 PagerDuty 點 timeline

完成標準：incident commander 不再需要進 PagerDuty UI、status update / role 指派 / action item 都在 Slack。

### Phase 2：Catalog + service ownership migrate

把 PagerDuty 的 service registry（service / team / escalation policy 關聯）抽出進 incident.io 的 Catalog。Catalog 是 incident.io 的 *service metadata source of truth*、把 service 跟 team / Slack channel / Linear project / runbook URL 綁在一起、incident 發生時自動推薦 role 跟通知 stakeholder。

工作主要塊：

- 從 PagerDuty API export service / team / escalation policy（REST endpoint `/services`、`/teams`、`/escalation_policies`）
- Schema mapping：PagerDuty service → incident.io catalog entry、escalation policy → 暫時不動（留在 PagerDuty）
- 補 PagerDuty 沒有的欄位：Slack channel、Linear project、runbook URL、tier（catalog 比 PagerDuty service 多 metadata 維度）
- Service ownership reconcile（PagerDuty 的 team grant 通常跟 GitHub team / IAM group 不一致、Catalog 是重新對齊機會）

完成標準：incident 發生時自動知道 owner team 跟對應 Slack channel、不需要人查。

### Phase 3：Schedule + escalation 移到 incident.io On-call

PagerDuty 的 schedule + escalation policy 改進 incident.io On-call。這是 *paging 入口的 ownership 轉移* — Phase 1 是 PD 觸發 IO response、Phase 3 是 IO 直接收 alert source 觸發 paging。

工作主要塊：

- Alert source 改線：Splunk / Datadog / Cloudflare WAF / cloud control plane 的 webhook 從 PagerDuty Event API 改成 incident.io webhook endpoint、deduplication key / severity mapping 重做
- Schedule 重建：PagerDuty schedule layer model（多 layer 疊加 + restriction + override）跟 incident.io schedule rule（單純 weekly rotation + override）不是 1:1、複雜 schedule 要重新設計
- Escalation policy 重建：PagerDuty 的 multi-step escalation + level-based timeout 對應 incident.io 的 escalation path、policy 比 PagerDuty 簡單但要重新測 failover 行為
- Mobile app 切換：on-call 人員裝 incident.io app、PagerDuty app 保留作為 backup paging（Phase 4 才完全捨棄）

完成標準：日常 paging 全走 incident.io、PagerDuty 留作 fallback 或退役。

### Phase 4：Retrospective + 完全退役 PagerDuty

把 retrospective workflow 切到 incident.io 內建的 post-incident flow、捨棄 PagerDuty Postmortems / Jeli 整合。incident.io 的 retro template 從 Slack channel 訊息自動 stitch timeline、action item 推 Linear / Jira、learning review 結構化。

工作主要塊：

- 既有 Jeli / PagerDuty Postmortems 歷史 export（PagerDuty REST 不直接給 postmortem export、要從 Jeli web app 手動 export）
- Retrospective template 對應到 org 既有的 post-incident review 結構
- Action item lifecycle 整合（incident.io 推 Linear / Jira → close → retrospective 自動標 done）

多數 org 停在 Phase 2 或 Phase 3。完整 Phase 4 退役 PagerDuty 不是必要、且常見的選擇是 *PagerDuty 留作 backup paging route* 或 *特定 integration 持續用*（見下一段 capability gap）。

## 5 個 production 踩雷

實際遷過程踩過的 5 個典型問題：

### 1. 雙系統 state drift（Phase 1 最常見）

PagerDuty incident.trigger → incident.io 開 channel、但 PagerDuty 上 incident 被自動 resolve（例如 monitoring tool 認為 issue cleared）後、incident.io 沒收到對應 webhook、Slack channel 還 active 顯示 in-progress。修法是雙向 webhook 都要接（PD resolved → IO 自動 close channel），但 webhook 失序的場景仍要有 nightly reconcile job 對比兩邊狀態。

### 2. Severity 翻譯失真

PagerDuty 的 P1-P5 跟 incident.io 的 SEV1-SEV4 不是 5:4 對應、是兩個獨立 schema。同一個事故在 PagerDuty 是 P2（高優先但非全面 outage）、進 incident.io 可能變 SEV2（部分服務影響）或 SEV1（依 incident.io custom severity 定義）。Phase 1 雙系統並行時 SRE 在 Slack 看到 SEV1 跑進 war room mode、PagerDuty 同 incident 是 P2 沒拉 stakeholder bridge — 同事故兩邊嚴重度不同步、回應節奏錯亂。修法是事先寫死 mapping table（PD P1 → IO SEV1、PD P2 → IO SEV2、不 case-by-case 判斷），並在 Phase 3 後讓 incident.io severity 變唯一 source of truth。

### 3. Schedule layer 漏 holiday override / restriction layer

PagerDuty schedule 是 layer model — primary rotation（layer 1） + secondary rotation（layer 2） + holiday override（layer 3） + restriction（每層 time-of-day 限制）可以疊加。Export 出來只看 layer 1 通常會漏 holiday override 跟 restriction layer、incident.io schedule rule 是單一 rotation + override list、不 cover 多 layer 疊加。修法是 export 時用 PagerDuty API `/schedules/{id}` 的完整 layer + final_schedule 一起拉、用 incident.io schedule 的 override list 模擬 layer 疊加、複雜 schedule（例如 follow-the-sun + 4 region + holiday override）可能要拆成多個 incident.io schedule 用 escalation chain 串。

### 4. Slack channel 過載

incident.io 預設每個 incident 開一個 channel。Phase 1 啟用後 SRE 一週收 50+ channel notification、即使 P3 / P4 也開 channel、Slack sidebar 被淹沒。修法是 incident type 設計時把低 severity（SEV3 / SEV4）改成 *don't auto-create channel* 或 *use shared low-severity channel*、只 SEV1 / SEV2 開獨立 channel。incident.io 有這個 configuration、但預設不開、要主動設定。

### 5. Retrospective 切換時歷史 learning 斷層

從 Jeli / PagerDuty Postmortems 切到 incident.io retro 後、過去 2 年 postmortem 留在原系統、search 跨不到、新 retro template 跟舊的結構不同、learning review 的 trend analysis 斷層。修法是 Phase 4 前先 export 既有 postmortem 為 markdown 進 GitHub Wiki / Confluence 集中保存、incident.io retro 自動 export 到同位置、retro search 不依賴 vendor lock-in。

## Schema translation 主要工作量塊

雖然 Type E 結構不以 schema translation 為主、但 translation 工作量塊在 Phase 2-3 仍佔多數時間：

| 來源（PagerDuty）          | 目標（incident.io）      | 註                                                    |
| -------------------------- | ------------------------ | ----------------------------------------------------- |
| Service                    | Catalog entry            | 增加 Slack channel / Linear project metadata          |
| Team                       | Catalog team             | 多對應 GitHub team / IAM group                        |
| Escalation policy          | Escalation path          | 比 PD 簡單、複雜 escalation 要拆                      |
| Schedule（multi-layer）    | Schedule + override list | 不是 1:1、複雜 schedule 要拆多個                      |
| Integration（webhook）     | Webhook endpoint         | 全部 alert source 要重 wire                           |
| Incident workflow          | Incident type + role     | 重新設計、不直接翻譯                                  |
| Event Orchestration rule   | Workflows                | incident.io workflows 比 EO 簡單、複雜 routing 要外接 |
| AIOps / Process Automation | （無對應）               | 見 capability gap 段                                  |
| Postmortem / Jeli          | Post-incident flow       | template 重寫、歷史保存獨立                           |

## Capability gap：PagerDuty 有但 incident.io 沒有

不是所有功能 incident.io 都有對應。Phase 3-4 推進前要先確認這些能力是否在用、是否願意捨棄或外接：

- **AIOps（intelligent grouping / noise reduction）**：PagerDuty Enterprise tier 用 ML 自動 group alert、incident.io 沒對應、grouping 靠 alert source 端 deduplication key
- **Process Automation（runbook automation）**：PagerDuty 收購 Rundeck、提供 automated remediation step、incident.io 沒對應、要外接 Tines / n8n / 自製 Lambda
- **Status Page 整合（PagerDuty 內建）**：PagerDuty 提供 Status Page 模組、incident.io status page 是 separate product、定價跟 feature 不同
- **Multi-region / 強合規（FedRAMP / IL5）**：PagerDuty 在金融 / 政府 / 高合規 deploy 成熟度高、incident.io SOC 2 + ISO 27001 但 FedRAMP 還在追

如果在用 AIOps + Process Automation 而且重要、不要做這個 migration、或保留 PagerDuty 作為 AIOps + Automation 後端、incident.io 處理 response coordination — Phase 1 永久 hybrid。

## 容量與成本對照

| 項目         | PagerDuty                                                   | incident.io                                                  |
| ------------ | ----------------------------------------------------------- | ------------------------------------------------------------ |
| 計費模式     | Per-user / month、tier-based（Pro / Business / Enterprise） | Per-user / month、On-call 模組另計                           |
| 隱性容量上限 | API rate limit（10K / minute）                              | Slack workspace seat 上限（IR participant ≤ workspace user） |
| AIOps 加價   | Enterprise tier + AIOps add-on                              | 不適用                                                       |
| Status page  | 內建（Business tier+）                                      | 獨立 product                                                 |
| Process Auto | Rundeck-based、separate pricing                             | 不適用                                                       |

實際成本對比需要 RFP — 50 人 SRE org 大致 PD Business + AIOps ~$30-40 / user / mo、incident.io Pro + On-call ~$25-35 / user / mo、cost 差距通常不是 migration 主因（是 paradigm fit + Slack-native）。

## 何時不要做這個 migration

- **Slack 不是 IR ground truth**：Discord / Teams primary 或 ticket system 為主的 org、incident.io Slack-first 設計無法落地
- **AIOps + Process Automation 是核心能力**：用了 PD AIOps 自動 group alert 跟 Rundeck 自動 remediation、且這條 chain 重要 — incident.io 沒對應
- **規模 < 20 SRE / 50 eng**：incident.io 的 catalog + opinionated workflow 設計給中大型 org、小團隊 PagerDuty Lite 或 Grafana OnCall 已經夠用
- **強合規場景（FedRAMP / IL5 / 金融 SOC 1 type II）**：PagerDuty 合規成熟度高、incident.io 在追、合規團隊不會 sign-off
- **不打算改變事故行為**：如果 org 只是想換廠商但不想改變 *事故在 Slack 跑 lifecycle* 的工作模式、這條 migration 的價值丟一半、不如走 [PagerDuty → Opsgenie](/backend/08-incident-response/vendors/opsgenie/migrate-from-pagerduty/)（Type A schema translation、同 paradigm）

## 下一步路由

- 平行 batch：[PagerDuty → Opsgenie](/backend/08-incident-response/vendors/opsgenie/migrate-from-pagerduty/)（Type A、同 paradigm 換廠商）/ [Atlassian Statuspage → Instatus](/backend/08-incident-response/vendors/atlassian-statuspage/migrate-to-instatus/)（Type B drop-in）
- 同 batch Type E：[JMeter → k6](/backend/09-performance-capacity/vendors/k6/migrate-from-jmeter/)（scripting paradigm shift）
- 上游：[8.10 Incident Workflow Automation Boundary](/backend/08-incident-response/incident-workflow-automation-boundary/)（automation handoff）
- 下游：[8.18 Post-Incident Review](/backend/08-incident-response/post-incident-review/)（incident.io retrospective workflow）
- vendor 對照：[PagerDuty](/backend/08-incident-response/vendors/pagerduty/) / [incident.io](/backend/08-incident-response/vendors/incident-io/)
- 方法論：[Migration Playbook Methodology](/posts/migration-playbook-methodology/)（Type E paradigm shift 結構說明）
