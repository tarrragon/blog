---
title: "模組八：事故處理與復盤"
date: 2026-05-01
description: "用 IR 領域詞彙建問題節點、以服務級案例庫累積事故脈絡，先建概念與案例庫再進實作交接"
weight: 8
---

事故處理模組的核心目標是把「事故發生時的臨場反應」轉成可演練、可交接、可復用的團隊流程。本模組採問題驅動方法、用 IR 領域 first-class 詞彙（ICS / Severity / Postmortem / Game Day），把事故議題拆成問題節點，蒐集公開事故報告作為案例庫，再把控制面交接到 04（觀測）/ 05（部署）/ 06（驗證）/ 07（資安約束）落地。

## Vendor / Platform 清單

實作工具見 [vendors](/backend/08-incident-response/vendors/) — T1 收錄 On-call（PagerDuty / Opsgenie / Grafana OnCall）、IR 平台（incident.io / FireHydrant / Rootly）、Status page（Atlassian Statuspage / Instatus）、Postmortem（Jeli）共 9 個 vendor 骨架。跟 [cases/](/backend/08-incident-response/cases/) 是不同維度（cases 是公開事故案例來源、vendors 是實作工具）。

## 規劃方向

本輪規劃的核心是把模組從「章節列表」升級成「問題節點 + 服務級案例庫」兩層結構：

1. **問題節點先行**：8.1-8.10 主章定義事故環節的問題、判讀訊號與責任邊界，不綁特定 stack。
2. **服務級案例庫**：以公開事故報告（AWS / Cloudflare / GitHub / GCP / Atlassian / Roblox / Fastly 等）作 cases，每個服務一個資料夾、累積架構脈絡與多次事故的 longitudinal pattern。
3. **資安事故是其中一類**：跟 07 的交接點維持，但 07 的紅藍隊框架不外推到本模組 — IR 自有 Severity / ICS / Postmortem 等 first-class 詞彙、不需要藉攻防隱喻表達。

不經實作即可推進的理由：事故處理的價值在「協作節奏與決策模型」，這層跟具體服務技術解耦，公開 post-mortem 案例豐富，符合先建概念層的條件。

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以事故環節問題為主體。

1. 先定義事故環節問題與責任邊界。
2. 再定義判讀訊號（影響面、擴散速率、降級空間）與升級條件。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應服務的事故案例。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由對應模組承接，確保概念層與實作層分工清晰。

- `backend/04-observability`：訊號偵測、判讀與告警治理實作。
- `backend/05-deployment-platform`：切換、回滾、流量控制與隔離實作。
- `backend/06-reliability`：事故前驗證、演練與回復排練實作。
- `backend/07-security-data-protection`：權限、稽核與高風險操作約束實作。

## 從章節到實作的 chain

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)，那層展開機制 / 邊界 / context-dependence。例：`[incident-command-system]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組——`04-observability`（訊號）/ `05-deployment-platform`（切換 / 回滾）/ `06-reliability`（演練 / 回復排練）/ `07-security-data-protection`（權限 / 稽核）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

## 跟既有模組的串接

本模組是 04 → 06 → 08 閉環的收口、承接 07 的概念判讀、把問題地圖轉成可執行事故節奏。資安事故僅是事故的一個子集、其他多數事故是可用性 / 容量 / 變更類。

**04↔06↔08 閉環交接基線**：

- **來自 [模組四 觀測性](/backend/04-observability/)**：訊號（SLO burn / error rate / latency spike）是事故啟動條件、判讀脈絡的主要來源。
- **餵給 [模組四 觀測性](/backend/04-observability/)**：postmortem 揭露的偵測缺口（訊號太晚、cardinality 不足、symptom-based alert 缺）回寫到 04 訊號治理。
- **來自 [模組六 可靠性](/backend/06-reliability/)**：事前演練（game day / DR rehearsal / chaos experiment）作為事中決策的肌肉記憶與 runbook 來源。
- **餵給 [模組六 可靠性](/backend/06-reliability/)**：postmortem action items 回寫成新 chaos / DR 演練題目、事故型態變成 6.4 / 6.7 的場景輸入。
- **詳細閉環說明**：見 [8.11 Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

**07 資安交接基線**：

- 來自 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)：承接身分事件分級與收斂順序。
- 來自 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)：承接入口事件止血、隔離與驗證節奏。
- 來自 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)：承接外送事件通報與影響盤點節奏。
- 來自 [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)：承接證據結構與復盤責任閉環。
- 來自 [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)：承接事故案例如何回寫控制面。

## 主章規劃

| 章節                                                                                                  | 主題                   | 核心責任                                                                                  |
| ----------------------------------------------------------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------------------- |
| [8.1 事故分級與啟動條件](/backend/08-incident-response/incident-severity-trigger/)                    | Severity & Trigger     | 建立統一分級與啟動門檻                                                                    |
| [8.2 事故指揮與角色分工](/backend/08-incident-response/incident-command-roles/)                       | Command Model          | 定義 commander、owner、scribe、[on-call](/backend/knowledge-cards/on-call) 協作           |
| [8.3 止血、降級與回復策略](/backend/08-incident-response/containment-recovery-strategy/)              | Containment & Recovery | 把短期止血與正式回復拆成可執行步驟                                                        |
| [8.4 事故通訊與狀態更新](/backend/08-incident-response/incident-communication/)                       | Incident Communication | 建立內外部通訊節奏與格式                                                                  |
| [8.5 復盤與改進追蹤](/backend/08-incident-response/post-incident-review/)                             | Post-Incident Review   | 把 RCA 與 action items 變成可驗證閉環                                                     |
| [8.6 演練與值班能力建設](/backend/08-incident-response/drills-and-oncall-readiness/)                  | Drills & Readiness     | 用 game day 與值班訓練提升反應品質                                                        |
| [8.7 失敗模式審查（Failure Mode Audit）](/backend/08-incident-response/attacker-view-incident-risks/) | Failure Mode Audit     | 用擴散路徑、回復瓶頸與交接斷點檢查事故設計（原「攻擊者視角」改名為領域 first-class 詞彙） |
| [8.8 事故報告轉 workflow](/backend/08-incident-response/incident-report-to-workflow/)                 | Case to Workflow       | 把事故故事轉成可執行、可驗證、可演練的流程                                                |

下一輪規劃補的問題節點：

| 章節（規劃） | 主題                                                 | 核心責任                                                                            |
| ------------ | ---------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 8.9          | 事故型態庫入口                                       | 把跨服務的共通事故型態（cascading / split-brain / control-plane failure）抽成型態卡 |
| 8.10         | Stakeholder 通訊與外部狀態頁                         | 把 customer impact、status page、補償政策串成節奏                                   |
| 8.11         | Observability / Reliability / Incident Response 閉環 | 把 04 / 06 / 08 三個模組的雙向反饋串成可判讀循環                                    |

## 服務案例庫規劃

服務作為案例單位、累積架構脈絡與多次事故的 longitudinal pattern。每個服務一個資料夾、收錄該服務的事故時間線、共通失敗模式與引用源。資料夾位置：`content/backend/08-incident-response/cases/{vendor-service}/`。

### T1（必寫、公開素材豐富、教學價值高）

| 服務                                                          | 教學重點                                                      |
| ------------------------------------------------------------- | ------------------------------------------------------------- |
| [aws-s3](/backend/08-incident-response/cases/aws-s3/)         | 2017 typo / 2021 us-east-1 / blast radius、區域依賴擴散       |
| [cloudflare](/backend/08-incident-response/cases/cloudflare/) | 2019 regex CPU / 2020 BGP / 2023 R2 / configuration push 風險 |
| [github](/backend/08-incident-response/cases/github/)         | 2018-10 MySQL split-brain / Actions outages、跨區資料一致性   |
| [gcp](/backend/08-incident-response/cases/gcp/)               | Load Balancer / IAM 全球控制面失效                            |
| [atlassian](/backend/08-incident-response/cases/atlassian/)   | 2022 多租戶誤刪 14 天、IR 公開度極高、跨團隊協作教科書        |
| [roblox](/backend/08-incident-response/cases/roblox/)         | 2021 73 小時、Consul + 流量模式根因、long-tail recovery       |
| [fastly](/backend/08-incident-response/cases/fastly/)         | 2021-06 全球分鐘級配置 push 事故                              |

### T2（補不同型態）

| 服務                                                      | 教學重點                                          |
| --------------------------------------------------------- | ------------------------------------------------- |
| [slack](/backend/08-incident-response/cases/slack/)       | 通訊節奏、外部狀態頁設計                          |
| [datadog](/backend/08-incident-response/cases/datadog/)   | 2023 multi-region、監控供應商自己掛、客戶觀測落差 |
| [stripe](/backend/06-reliability/cases/stripe/)           | 金流影響量化、idempotency 與 API 兼容（住於 06）  |
| [discord](/backend/08-incident-response/cases/discord/)   | Gateway scale-out 事故、capacity surprise         |
| [azure-ad](/backend/08-incident-response/cases/azure-ad/) | Identity 控制面失效、藍圖式 cascading             |

### T3（補完，視時間）

| 服務                                                                | 教學重點                                 |
| ------------------------------------------------------------------- | ---------------------------------------- |
| [heroku](/backend/08-incident-response/cases/heroku/)               | Router 層失效、PaaS multi-tenant 路由    |
| [linkedin](/backend/06-reliability/cases/linkedin/)                 | Capacity 與 on-call structure（住於 06） |
| [reddit](/backend/08-incident-response/cases/reddit/)               | Pi Day 2023 k8s 升級事故                 |
| [microsoft-365](/backend/08-incident-response/cases/microsoft-365/) | 企業 SaaS 套件事故、PIR 格式             |

## 既有可引用卡片

- [runbook](/backend/knowledge-cards/runbook/)
- [alert runbook](/backend/knowledge-cards/alert-runbook/)
- [runbook link](/backend/knowledge-cards/runbook-link/)
- [on-call](/backend/knowledge-cards/on-call/)
- [playbook](/backend/knowledge-cards/playbook/)
- [game day](/backend/knowledge-cards/game-day/)
- [symptom-based alert](/backend/knowledge-cards/symptom-based-alert/)
- [alert fatigue](/backend/knowledge-cards/alert-fatigue/)
- [downtime](/backend/knowledge-cards/downtime/)
- [degradation](/backend/knowledge-cards/degradation/)
- [failover](/backend/knowledge-cards/failover/)
- [fallback plan](/backend/knowledge-cards/fallback-plan/)
- [replay runbook](/backend/knowledge-cards/replay-runbook/)
- [incident severity](/backend/knowledge-cards/incident-severity/)
- [incident command system](/backend/knowledge-cards/incident-command-system/)
- [escalation policy](/backend/knowledge-cards/escalation-policy/)
- [incident timeline](/backend/knowledge-cards/incident-timeline/)
- [blast radius](/backend/knowledge-cards/blast-radius/)
- [rollback strategy](/backend/knowledge-cards/rollback-strategy/)
- [post-incident review](/backend/knowledge-cards/post-incident-review/)
- [RCA](/backend/knowledge-cards/rca/)
- [RTO](/backend/knowledge-cards/rto/)
- [RPO](/backend/knowledge-cards/rpo/)
- [MTTR](/backend/knowledge-cards/mttr/)

## 模組完成狀態

主章 8.1-8.8 骨架已建立、8.9-8.10 規劃中。服務案例庫（T1）骨架建立、個別 case 內容待補。本模組目前處於規劃階段。

## 下一輪推演大綱

| 階段 | 產出              | 責任                                                            | 回寫位置                               |
| ---- | ----------------- | --------------------------------------------------------------- | -------------------------------------- |
| 1    | T1 服務骨架       | 建 7 個 T1 服務的 `cases/{service}/_index.md` 規劃骨架          | `cases/`                               |
| 2    | 8.7 改名落實      | 把「攻擊者視角」改名「失敗模式審查」、用 IR 領域詞彙重寫        | `8.7`                                  |
| 3    | 8.9 事故型態庫    | 把 cascading / split-brain / control-plane 等抽成型態卡         | `8.9`                                  |
| 4    | T1 第一個服務內容 | 從 `aws-s3` 或 `cloudflare` 起頭、寫服務 _index 加 2-3 incident | `cases/aws-s3/` 或 `cases/cloudflare/` |
| 5    | 8.10 通訊節奏     | 把 stakeholder、status page、補償政策串成節奏                   | `8.10`                                 |
| 6    | 跨模組回寫        | 把 case 教訓回寫到 06 演練題目 / 04 訊號 / 05 切換              | `8.8` + `7.16`                         |

推演資產化的完成條件是讓讀者能從一個事故壓力出發，找到對應問題節點、服務 case 與回寫章節。完成後事故模組才進入穩定維護狀態。

## Tripwire

- 寫 T1 服務第 3 個時、若 case 之間無共通分類軸 → 改用單服務獨立檔，不開資料夾。
- 寫到第 9 主章發現章節覆蓋 60%+ → 軸線過於相似、合併或重切。
- 進服務實作模組時 routing chain 走不通 → 回頭補對應主章。
