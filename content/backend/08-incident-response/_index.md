---
title: "模組八：事故處理與復盤"
date: 2026-05-01
description: "用 IR 領域詞彙建問題節點、以服務級案例庫累積事故脈絡，先建概念與案例庫再進實作交接"
weight: 8
tags: ["backend", "incident-response", "operations"]
---

事故處理模組的核心目標是把「事故發生時的臨場反應」轉成可演練、可交接、可復用的團隊流程。本模組採問題驅動方法、用 IR 領域 first-class 詞彙（ICS / Severity / [post-incident review](/backend/knowledge-cards/post-incident-review/) / Game Day），把事故議題拆成問題節點，蒐集公開事故報告作為案例庫，再把控制面交接到可觀測性、部署平台、可靠性驗證與資安約束落地。

## 事故角色

事故處理的角色是把「出了問題之後怎麼做」變成可預期的協作節奏。這一層不負責追究誰做錯，也不負責寫修復程式，而是負責把啟動、分工、止血、通訊、復原與復盤串成同一條路徑。

當一個事故被定義成流程，讀者才會看懂 severity 是路由，ICS 是角色分工，[post-incident review](/backend/knowledge-cards/post-incident-review/) 是下一次演練與改進的輸入。這些詞彙的責任，是讓事故從臨場反應變成可交接的制度。

## 問題節點

問題節點先描述事故環節，再描述決策責任。這樣做可以讓讀者先知道哪裡出現風險，再知道應該把判讀輸給哪個角色或流程。

| 節點               | 事故問題                                                | 常見訊號                                                                                   |
| ------------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Severity & Trigger | 事故是否已經跨過啟動門檻、是否需要升級處理              | [impact scope](/backend/knowledge-cards/impact-scope/)、user pain、business risk           |
| Command Model      | 誰在指揮、誰在記錄、誰在修復、誰在對外通訊              | role assignment、handoff latency                                                           |
| Containment        | 現在應該先止血、降級還是回復                            | [blast radius](/backend/knowledge-cards/blast-radius/)、degradation success rate           |
| Communication      | 內外部要怎麼更新、多久更新一次、哪些細節先說            | status cadence、customer confusion                                                         |
| Review & Workflow  | 事故後要補什麼流程、哪些 runbook 要重寫、哪個演練要重跑 | [action item closure](/backend/knowledge-cards/action-item-closure/)、repeat incident rate |

這張表的目的是讓事故先變成路由。當路由成立後，服務案例庫才有意義，因為案例可以直接提供真實時間線、對外更新與復原節奏。

## 案例庫讀法

案例庫的責任是保留不同型態的事故節奏。AWS S3、Cloudflare、GitHub、GCP、Atlassian、Roblox 與 Fastly 這些 T1 案例，各自代表控制面、路由、資料一致性、多租戶復原與 edge 擴散的不同樣本。

讀這些案例時，先看它是哪一種事故，再看它如何收斂。第一步是判斷事故屬於控制面還是資料面。第二步是看影響面是否還在擴大。第三步是看對外通訊與內部復原是否同步。這三步會把讀者導向不同的案例頁，也會把讀者導回可觀測性、部署平台、可靠性驗證或資安約束的交接節點。

| 案例       | 主要用途                      | 常見回扣節點                                                                                 |
| ---------- | ----------------------------- | -------------------------------------------------------------------------------------------- |
| AWS S3     | 控制面失效如何擴散到整個區域  | [blast radius](/backend/knowledge-cards/blast-radius/)、recover order                        |
| Cloudflare | edge 配置與路由如何全球擴散   | configuration push、rollback                                                                 |
| GitHub     | replication 與 control plane  | status update、failover boundary                                                             |
| GCP        | 全球控制面與 identity 依賴    | staged rollout、service health                                                               |
| Atlassian  | 多租戶誤刪與長尾復原          | [incident command system](/backend/knowledge-cards/incident-command-system/)、customer comms |
| Roblox     | prolonged recovery 與廠商協作 | root cause discovery、return to service                                                      |
| Fastly     | 客戶配置觸發供應商 bug        | propagation speed、rollback                                                                  |

## 第一輪案例驅動路由

第一輪 T1 案例已補到「每個服務至少一篇可引用事故頁」。這些案例的用途不是堆疊事件，而是把 04 的觀測證據、06 的驗證邊界、08 的指揮與通訊串成同一條教學路徑。

| 事故案例                                                                                                                     | 主要判讀問題                     | 優先回讀章節                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| [Cloudflare 2019 Regex CPU Outage](/backend/08-incident-response/cases/cloudflare/2019-regex-cpu-outage/)                    | 規則推送如何秒級擴散             | [4.21](/backend/04-observability/rule-level-cpu-signal-governance/)、[6.24](/backend/06-reliability/rule-rollout-safety-gate/)         |
| [AWS S3 2017 US-EAST-1](/backend/08-incident-response/cases/aws-s3/2017-us-east-1-service-disruption/)                       | 共享子系統恢復順序與通訊入口依賴 | [8.3](/backend/08-incident-response/containment-recovery-strategy/)、[8.4](/backend/08-incident-response/incident-communication/)      |
| [GitHub 2018 Oct21](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/)                          | 一致性優先下的 fail-forward 決策 | [8.19](/backend/08-incident-response/incident-decision-log/)、[6.22](/backend/06-reliability/steady-state-definition/)                 |
| [GCP 2019 Network Incident](/backend/08-incident-response/cases/gcp/2019-us-network-congestion-multi-service-incident/)      | 區域網路壅塞如何跨產品擴散       | [4.20](/backend/04-observability/observability-evidence-package/)、[8.22](/backend/08-incident-response/incident-evidence-write-back/) |
| [Atlassian 2022 Multi-tenant Outage](/backend/08-incident-response/cases/atlassian/2022-april-multi-tenant-deletion-outage/) | 長事故的分批恢復與客戶通訊       | [8.20](/backend/08-incident-response/customer-impact-assessment/)、[8.4](/backend/08-incident-response/incident-communication/)        |
| [Roblox 2021 Prolonged Outage](/backend/08-incident-response/cases/roblox/2021-oct-prolonged-core-infra-outage/)             | 根因定位延遲與長尾恢復治理       | [8.12](/backend/08-incident-response/ic-handoff-long-incident/)、[6.22](/backend/06-reliability/steady-state-definition/)              |
| [Fastly 2021 Global Edge Outage](/backend/08-incident-response/cases/fastly/2021-june-global-edge-config-triggered-outage/)  | 有效配置觸發潛藏 bug 的全球擴散  | [6.24](/backend/06-reliability/rule-rollout-safety-gate/)、[8.4](/backend/08-incident-response/incident-communication/)                |

若要繼續擴案例，不要只沿同一家公司加事件；先回到 [0.14 企業選型案例圖譜](/backend/00-service-selection/enterprise-selection-case-atlas/) 補「企業型態 × 規模階段」覆蓋，再把新增事故映射到本章的問題節點（8.1-8.5、8.18-8.22），才能同時強化案例多樣性與教學路由。

第一批缺口回填建議先做三條事故題目：FinTech 補交易中斷時的 impact 分級與對外通訊節奏（回寫 8.1、8.10、8.20）；Gaming 補高峰活動期間的 multi-incident 協調與長事故交接（回寫 8.12、8.14）；Healthcare 補資料與服務雙重事件的 evidence triage 與責任分流（回寫 8.17、8.18、8.19）。

| 產業案例類型 | 事故回寫重點                               | 章節路由                                                                                                                                                                                                      |
| ------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FinTech      | 交易中斷分級、對外更新節奏、客戶影響量化   | [8.1](/backend/08-incident-response/incident-severity-trigger/)、[8.10](/backend/08-incident-response/stakeholder-communication/)、[8.20](/backend/08-incident-response/customer-impact-assessment/)          |
| Gaming       | 活動高峰多事故協調、跨時區接班與復原節奏   | [8.12](/backend/08-incident-response/ic-handoff-long-incident/)、[8.14](/backend/08-incident-response/multi-incident-coordination/)                                                                           |
| Healthcare   | 資料與服務雙軌事件分流、證據分級與決策紀錄 | [8.17](/backend/08-incident-response/security-vs-operational-incident/)、[8.18](/backend/08-incident-response/incident-intake-evidence-triage/)、[8.19](/backend/08-incident-response/incident-decision-log/) |

## Vendor / Platform 清單

實作工具見 [vendors](/backend/08-incident-response/vendors/) — T1 收錄 On-call（PagerDuty / Opsgenie / Grafana OnCall）、IR 平台（incident.io / FireHydrant / Rootly）、Status page（Atlassian Statuspage / Instatus）、Postmortem（Jeli）共 9 個 vendor 骨架。跟 [cases/](/backend/08-incident-response/cases/) 是不同維度（cases 是公開事故案例來源、vendors 是實作工具）。

進入工具比較前，先回到 [觀測、可靠性與事故服務選型](/backend/00-service-selection/operations-control-service-selection/) 判斷目前缺的是響應層能力，還是缺少可觀測性的證據來源或可靠性驗證的事前演練。事故工具選型要以「事故能否被接住、分工、通訊與回寫」為主軸，on-call 或 IR 平台功能清單只是落地選項。

## 規劃方向

本輪規劃的核心是把模組從「章節列表」升級成「問題節點 + 服務級案例庫」兩層結構：

1. **問題節點先行**：8.1-8.10 主章定義事故環節的問題、判讀訊號與責任邊界，不綁特定 stack。
2. **服務級案例庫**：以公開事故報告（AWS / Cloudflare / GitHub / GCP / Atlassian / Roblox / Fastly 等）作 cases，每個服務一個資料夾、累積架構脈絡與多次事故的 longitudinal pattern。
3. **資安事故是其中一類**：跟 07 的交接點維持，但 07 的紅藍隊框架不外推到本模組 — IR 自有 Severity / ICS / [post-incident review](/backend/knowledge-cards/post-incident-review/) 等 first-class 詞彙、不需要藉攻防隱喻表達。

不經實作即可推進的理由：事故處理的價值在「協作節奏與決策模型」，這層跟具體服務技術解耦，公開 post-mortem 案例豐富，符合先建概念層的條件。

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以事故環節問題為主體。

1. 先定義事故環節問題與責任邊界。
2. 再定義判讀訊號（影響面、擴散速率、降級空間）與升級條件。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應服務的事故案例。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由對應模組承接，確保概念層與實作層分工清晰。

- `backend/04-observability`：可觀測性模組，負責訊號偵測、判讀與告警治理實作。
- `backend/05-deployment-platform`：切換、回滾、流量控制與隔離實作。
- `backend/06-reliability`：可靠性驗證模組，負責事故前驗證、演練與回復排練實作。
- `backend/07-security-data-protection`：權限、稽核與高風險操作約束實作。

## 從章節到實作的 chain

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)，那層展開機制 / 邊界 / context-dependence。例：`[incident-command-system]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組，包括可觀測性（訊號）、部署平台（切換 / 回滾）、可靠性驗證（演練 / 回復排練）與資安資料保護（權限 / 稽核）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

## 跟既有模組的串接

本模組是「觀測 → 驗證 → 事故」閉環的收口、承接資安概念判讀、把問題地圖轉成可執行事故節奏。資安事故僅是事故的一個子集、其他多數事故是可用性 / 容量 / 變更類。

**觀測、驗證與事故閉環交接基線**：

- **來自 [可觀測性平台](/backend/04-observability/)**：訊號（SLO burn / error rate / latency spike）是事故啟動條件、判讀脈絡的主要來源。
- **餵給 [可觀測性平台](/backend/04-observability/)**：[post-incident review](/backend/knowledge-cards/post-incident-review/) 揭露的偵測缺口（訊號太晚、cardinality 不足、symptom-based alert 缺）回寫到訊號治理。
- **來自 [可靠性驗證流程](/backend/06-reliability/)**：事前演練（game day / DR rehearsal / chaos experiment）作為事中決策的肌肉記憶與 runbook 來源。
- **餵給 [可靠性驗證流程](/backend/06-reliability/)**：[post-incident review](/backend/knowledge-cards/post-incident-review/) action items 回寫成新 chaos / DR 演練題目、事故型態變成 chaos 與 DR 演練的場景輸入。
- **詳細閉環說明**：見 [Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

**07 資安交接基線**：

- 來自 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)：承接身分事件分級與收斂順序。
- 來自 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)：承接入口事件止血、隔離與驗證節奏。
- 來自 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)：承接外送事件通報與影響盤點節奏。
- 來自 [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)：承接證據結構與復盤責任閉環。
- 來自 [7.16 從公開事故到工程 Workflow](/backend/07-security-data-protection/incident-case-to-control-workflow/)：承接事故案例如何回寫控制面。

## 主章規劃

| 章節                                                                                                          | 主題                                               | 核心責任                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| [8.1 事故分級與啟動條件](/backend/08-incident-response/incident-severity-trigger/)                            | Severity & Trigger                                 | 建立統一分級與啟動門檻                                                                                                                |
| [8.2 事故指揮與角色分工](/backend/08-incident-response/incident-command-roles/)                               | Command Model                                      | 定義 commander、owner、scribe、[on-call](/backend/knowledge-cards/on-call) 協作                                                       |
| [8.3 止血、降級與回復策略](/backend/08-incident-response/containment-recovery-strategy/)                      | Containment & Recovery                             | 把短期止血與正式回復拆成可執行步驟                                                                                                    |
| [8.4 事故通訊與狀態更新](/backend/08-incident-response/incident-communication/)                               | Incident Communication                             | 建立內外部通訊節奏與格式                                                                                                              |
| [8.5 復盤與改進追蹤](/backend/08-incident-response/post-incident-review/)                                     | Post-Incident Review                               | 把 [RCA](/backend/knowledge-cards/rca/) 與 action items 變成可驗證閉環                                                                |
| [8.6 演練與值班能力建設](/backend/08-incident-response/drills-and-oncall-readiness/)                          | Drills & Readiness                                 | 用 game day 與值班訓練提升反應品質                                                                                                    |
| [8.7 失敗模式審查（Failure Mode Audit）](/backend/08-incident-response/attacker-view-incident-risks/)         | Failure Mode Audit                                 | 用擴散路徑、回復瓶頸與交接斷點檢查事故設計（原「攻擊者視角」改名為領域 first-class 詞彙）                                             |
| [8.8 事故報告轉 workflow](/backend/08-incident-response/incident-report-to-workflow/)                         | Case to Workflow                                   | 把事故故事轉成可執行、可驗證、可演練的流程                                                                                            |
| [8.9 事故型態庫入口](/backend/08-incident-response/incident-pattern-library/)                                 | Incident Pattern                                   | 把跨服務的共通事故型態（cascading / split-brain / control-plane failure）抽成型態卡                                                   |
| [8.10 Stakeholder 通訊與外部狀態頁](/backend/08-incident-response/stakeholder-communication/)                 | Stakeholder Comms                                  | 把 [impact scope](/backend/knowledge-cards/impact-scope/)、[status page](/backend/knowledge-cards/status-page/)、補償政策串成節奏     |
| [8.11 觀測、驗證與事故閉環](/backend/08-incident-response/observability-reliability-incident-loop/)           | Cross-Module Loop                                  | 把可觀測性、可靠性驗證與事故處理的雙向反饋串成可判讀循環                                                                              |
| [8.12 IC Handoff 與長事故協調](/backend/08-incident-response/ic-handoff-long-incident/)                       | Handover                                           | 把 24h+ / 跨 timezone 事故的接班節奏變成可重複流程                                                                                    |
| [8.13 Repeated Incident 與 Toil 治理](/backend/08-incident-response/repeated-incident-toil/)                  | Repeated & Toil                                    | 把同型反覆事故與重複手動修復變成工程化治理對象                                                                                        |
| [8.14 Multi-incident Coordination](/backend/08-incident-response/multi-incident-coordination/)                | Multi-incident                                     | 把同時多事故的優先序、資源分配與 [incident command system](/backend/knowledge-cards/incident-command-system/) pool 協調變成可執行流程 |
| [8.15 Vendor / 第三方依賴事故處理](/backend/08-incident-response/vendor-dependency-incident/)                 | Vendor Incident                                    | 依賴方掛掉、自己無 control 時的決策模型                                                                                               |
| [8.16 Runbook Lifecycle 管理](/backend/08-incident-response/runbook-lifecycle/)                               | Runbook Lifecycle                                  | 把 runbook 變成有版本、有演練、會過期的 artifact                                                                                      |
| [8.17 Security vs Operational Incident 分流](/backend/08-incident-response/security-vs-operational-incident/) | Security vs Ops IR                                 | 把資安事故跟可用性事故的 IR 流程分支點明確化                                                                                          |
| [8.18](/backend/08-incident-response/incident-intake-evidence-triage/)                                        | Incident Intake & Evidence Triage                  | 把告警、客訴、支援回報與第三方狀態轉成同一個 intake / evidence 判讀流程                                                               |
| [8.19](/backend/08-incident-response/incident-decision-log/)                                                  | Incident Decision Log                              | 把事中假設、決策、證據、回退條件與責任人留下可復盤紀錄                                                                                |
| [8.20](/backend/08-incident-response/customer-impact-assessment/)                                             | Customer Impact Assessment                         | 把受影響用戶、功能、區域、金額、SLO 與補償判斷串成影響評估模型                                                                        |
| [8.21](/backend/08-incident-response/incident-workflow-automation-boundary/)                                  | Incident Workflow Automation Boundary              | 定義哪些事故流程適合自動化，哪些決策需要保留人工確認                                                                                  |
| [8.22](/backend/08-incident-response/incident-evidence-write-back/)                                           | Incident Evidence Write-back                       | 把事故證據、決策與復盤結論回寫到 observability、reliability 與 runbook                                                                |
| [8.23](/backend/08-incident-response/control-plane-decision-log-write-back/)                                  | Control Plane Decision Log and Write-back 實作示範 | 以 rule/config rollout 事故示範 decision log 與 write-back 的完整閉環                                                                 |

> 註：8.1-8.23 已完成概念層與第一篇實作示範正文，案例庫可支援 intake、decision、impact、write-back 的完整路由。後續重點為多事件對照與跨模組回寫精度提升。

## 個案前拓展空間

個案前拓展的責任是先建立事故案例的閱讀欄位。事故處理模組適合補 intake、evidence、decision、impact 與 automation boundary 這類跨事故骨架，不適合直接把公開事故故事當正文主軸。

| 拓展方向                              | 補充理由                                   | 先放位置 |
| ------------------------------------- | ------------------------------------------ | -------- |
| Incident Intake & Evidence Triage     | 事故來源可能是告警、客訴、支援或第三方狀態 | 8.18     |
| Incident Decision Log                 | 事中決策需要保留假設、證據、條件與責任人   | 8.19     |
| Customer Impact Assessment            | 對外通訊與補償需要更精準的影響評估模型     | 8.20     |
| Incident Workflow Automation Boundary | 自動化適合處理通知與欄位，決策仍需清楚邊界 | 8.21     |

本輪先完成這四個個案前拓展章，讓公開事故案例可以被拆成可重用素材。若案例重點是「事故從哪裡被發現」，回寫 Incident Intake & Evidence Triage；若重點是「事中決策如何形成」，回寫 Incident Decision Log；若重點是「客戶影響如何量化」，回寫 Customer Impact Assessment；若重點是「流程工具是否幫上忙」，回寫 Incident Workflow Automation Boundary。

## 後續深化方向

08 後續深化以「同服務多事件對照、decision/evidence 欄位標準化、跨模組閉環回寫」為主。事故處理承接 04 的觀測證據與 06 的驗證結果，並持續回寫上游控制面。

| 深化方向       | 主要責任                                               | 回寫路由                                                                                                                             |
| -------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| 多事件對照     | 同服務建立第二、第三事件對照，提煉失效模式             | [cases/](/backend/08-incident-response/cases/)                                                                                       |
| 欄位標準化     | intake / decision / impact / write-back 用同一欄位語言 | [8.18](/backend/08-incident-response/incident-intake-evidence-triage/)、[8.19](/backend/08-incident-response/incident-decision-log/) |
| 跨模組閉環回寫 | 把事故教訓回寫到觀測與驗證控制面                       | [4.20](/backend/04-observability/observability-evidence-package/)、[6.23](/backend/06-reliability/verification-evidence-handoff/)    |

## 實作探討入口

進入實作層時，08 建議先建最小 incident artifact 套組：`intake sheet + decision log + customer impact note + write-back record`，並固定連到 [4.20](/backend/04-observability/observability-evidence-package/) 與 [6.23](/backend/06-reliability/verification-evidence-handoff/)。

首篇示範已完成： [8.23 Control Plane Decision Log and Write-back 實作示範](/backend/08-incident-response/control-plane-decision-log-write-back/)。

完成條件是每篇都能回答四件事：輸入來源、判讀欄位、決策責任、回寫路由。這樣 08 才能把事故從臨場反應整理成可演練、可復盤、可交接的流程。

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
- [impact scope](/backend/knowledge-cards/impact-scope/)
- [rollback strategy](/backend/knowledge-cards/rollback-strategy/)
- [post-incident review](/backend/knowledge-cards/post-incident-review/)
- [action item closure](/backend/knowledge-cards/action-item-closure/)
- [RCA](/backend/knowledge-cards/rca/)
- [RTO](/backend/knowledge-cards/rto/)
- [RPO](/backend/knowledge-cards/rpo/)
- [MTTR](/backend/knowledge-cards/mttr/)
- [status page](/backend/knowledge-cards/status-page/)
- [stakeholder mapping](/backend/knowledge-cards/stakeholder-mapping/)
- [toil](/backend/knowledge-cards/toil/)

## 模組完成狀態

主章 8.1-8.23 已完成首輪正文，服務案例庫第一批正文已補齊（Cloudflare / AWS S3 / GitHub / GCP / Atlassian / Roblox / Fastly，以及 Slack / Datadog / Discord / Azure AD / Heroku / Reddit / Microsoft 365）。目前重點從「補案例檔案」轉為「補多事件對照與決策路徑精度」。

案例正文入口見 [事故案例庫](/backend/08-incident-response/cases/)。每篇案例至少要能回寫一個事故控制面章節（例如 8.18、8.19、8.20、8.21、8.22），避免只停在事故時間線描述。

第二批案例深挖已補 `AWS` 第二事件： [2021 US-EAST-1 Control Plane Degradation](/backend/08-incident-response/cases/aws-s3/2021-us-east-1-control-plane-degradation/)。這篇重點回寫 `8.3 / 8.4 / 8.20` 與 `4.18 / 4.20`，補齊 control plane 退化與通訊節奏的判讀。

深挖批次 B 已補 `Cloudflare` 第三事件： [2023 Workers KV Deployment Tool Misconfiguration](/backend/08-incident-response/cases/cloudflare/2023-workers-kv-deployment-tool-misconfiguration/)。這篇重點回寫 `8.19 / 8.22 / 6.24`，把控制面變更擴散與 decision log 的治理責任接回主章。

第三批案例補強已補 `AWS` 第三篇： [2023 Control Plane Accountability and Communication Pattern](/backend/08-incident-response/cases/aws-s3/2023-control-plane-accountability-and-communication-pattern/)。這篇重點回寫 `8.19 / 8.20 / 8.4 / 4.20`，補齊控制面事故的責任邊界與對外節奏樣式。

## 後續推演大綱

| 階段 | 產出           | 責任                                                              | 回寫位置                               |
| ---- | -------------- | ----------------------------------------------------------------- | -------------------------------------- |
| 1    | 案例深挖批次 A | 針對 T1 案例補第二事件或後續事件，強化同服務的決策演進對照        | `cases/cloudflare/`、`cases/aws-s3/`   |
| 2    | 案例深挖批次 B | 針對 T2/T3 案例補不同事故型態，避免只集中在單一故障類型           | `cases/{service}/`                     |
| 3    | 章節回寫補強   | 把案例中的 intake、decision、impact、automation 教訓回寫主章      | `8.18`、`8.19`、`8.20`、`8.21`、`8.22` |
| 4    | 跨模組路由校正 | 補齊 04/05/06/07 的交接連結，讓讀者可從事故案例直接跳到上游控制面 | 各章節「交接路由」段                   |

推演資產化的完成條件是讓讀者能從一個事故壓力出發，找到對應問題節點、服務 case 與回寫章節。完成後事故模組才進入穩定維護狀態。

## Tripwire

- 寫 T1 服務第 3 個時、若 case 之間無共通分類軸 → 改用單服務獨立檔，不開資料夾。
- 寫到第 9 主章發現章節覆蓋 60%+ → 軸線過於相似、合併或重切。
- 進服務實作模組時 routing chain 走不通 → 回頭補對應主章。
