---
title: "模組六：可靠性驗證流程"
date: 2026-05-01
description: "用 SRE 領域詞彙建問題節點、以服務級案例庫累積驗證脈絡，先建概念與案例庫再進實作交接"
weight: 6
---

可靠性驗證模組的核心目標是說明測試如何從單一函式擴展到整個後端系統。語言教材會處理 unit test、table-driven / parameterized test、race / async test 與 integration test；本模組負責 [CI pipeline](/backend/knowledge-cards/ci-pipeline)、壓力測試、fuzz campaign、chaos testing、SLO 與 [Release Gate](/backend/knowledge-cards/release-gate/)。

本輪規劃採問題驅動方法、用 SRE 領域 first-class 詞彙（SLI / SLO / Error Budget / Failure Mode / Chaos Hypothesis），把驗證議題拆成問題節點，蒐集公開 SRE 實踐作為服務級案例庫，再把控制面交接到可觀測性、部署平台與事故處理模組落地。

## 驗證角色

可靠性驗證的角色是把「系統會不會在真實壓力下失敗」變成可預演的工程問題。這一層不負責寫測試語法，也不負責定義服務功能，而是負責定義哪些失效值得被主動打破、哪一種訊號可以證明風險存在、哪一種門檻可以阻止變更往下流。

當讀者把驗證看成流程，就會自然分出三個層次。第一層是訊號，先知道要看什麼。第二層是演練，先知道要怎麼打。第三層是放行，先知道什麼情況需要暫停或退回。這三層分別對應可觀測性、可靠性驗證與交付平台的責任。

## 問題節點

問題節點先描述失效風險，再描述驗證手段。這樣寫的好處是，讀者能先理解「為什麼要驗證」，再看到「怎麼驗證」，讓工具名回到解題手段的位置。

| 節點               | 驗證問題                                           | 常見訊號                                      |
| ------------------ | -------------------------------------------------- | --------------------------------------------- |
| CI pipeline        | 測試是否真的攔住回歸、artifact 是否可重播          | flaky rate、test duration、build queue        |
| Load test          | 真實負載是否被模型覆蓋、瓶頸是否被提早暴露         | latency curve、throughput ceiling、error rate |
| Fuzz campaign      | 邊界輸入是否能觸發 crash、corpus 是否持續擴充      | crash reproduction、coverage delta            |
| Chaos testing      | 依賴失效後系統是否仍能維持服務、回復路徑是否可執行 | steady state drift、rollback success rate     |
| SLO / Error Budget | 可靠性是否已經被消耗、變更是否還能繼續推進         | burn rate、error budget remaining             |

這張表的責任是提供路由。每一列都要回到服務案例庫，從公開實踐找出真實世界的樣本，把問題節點和失效模式綁在一起。

## 案例庫讀法

案例庫的責任是提供幾種反覆出現的失效與驗證模式。Google、Netflix、Amazon、Stripe 與 Shopify 這五個 T1 案例，分別對應量化門檻、主動故障注入、隔離邊界、交易正確性與峰值準備。

當讀者遇到某個驗證節點卡住時，可以先問三個問題。第一，現在缺的是訊號還是門檻。第二，失敗是在單一服務內還是在依賴鏈上。第三，這種風險更像回歸、容量、變更還是恢復問題。這三個問題會把讀者導向不同案例頁，也會把讀者導回可觀測性、部署平台或事故處理的交接節點。

| 案例    | 主要用途                                                               | 常見回扣節點                                                                                                        |
| ------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Google  | 把可靠性制度化                                                         | SLO、[post-incident review](/backend/knowledge-cards/post-incident-review/)、[toil](/backend/knowledge-cards/toil/) |
| Netflix | 把故障注入制度化                                                       | chaos、steady state、FIT                                                                                            |
| Amazon  | 把隔離與 [blast radius](/backend/knowledge-cards/blast-radius/) 制度化 | cell、shard、static stability                                                                                       |
| Stripe  | 把交易正確性制度化                                                     | idempotency、canary、migration                                                                                      |
| Shopify | 把峰值準備與演練制度化                                                 | capacity planning、resiliency matrix                                                                                |

## Vendor / Platform 清單

實作工具見 [vendors](/backend/06-reliability/vendors/) — T1 收錄 CI（GitHub Actions / CircleCI）、Load test（k6 / Gatling / JMeter / Locust）、Chaos（Chaos Mesh / LitmusChaos / Gremlin / Toxiproxy）、SLO（Nobl9 / Sloth）共 12 個 vendor 骨架。跟 [cases/](/backend/06-reliability/cases/) 是不同維度（cases 是教學案例來源、vendors 是實作工具）。

進入工具比較前，先回到 [觀測、可靠性與事故服務選型](/backend/00-service-selection/operations-control-service-selection/) 判斷目前缺的是驗證層能力，還是缺少可觀測性的訊號 baseline 或事故處理的接手流程。可靠性工具選型要以「能否安全驗證失敗」為主軸，CI、load、chaos 或 SLO 工具名稱只是落地選項。

## 規劃方向

本輪規劃的核心是把模組從「驗證手段列表」升級成「失敗風險節點 + 服務級案例庫」兩層結構：

1. **問題節點先行**：6.1-6.5 主章已建立、補 6.6（SLO/Error Budget）/ 6.7（DR & Rollback Rehearsal）/ 6.8（Release Gate & Change Cadence）/ 6.9（Capacity & Cost）等節點，不綁特定框架。
2. **服務級案例庫**：以公開 SRE 實踐（Google / Netflix / Amazon / Stripe / Shopify 等）作 cases，每個服務一個資料夾、累積架構脈絡與多次驗證案例。
3. **資安驗證是其中一類**：跟 07 的交接點維持，但 07 的紅藍隊框架不外推到本模組 — SRE 自有 Failure Mode / Pre-mortem / FMEA / Chaos Hypothesis 等 first-class 詞彙、不需要藉攻防隱喻表達。

不經實作即可推進的理由：可靠性的價值在「失敗模式預判與驗證設計」，這層跟具體框架解耦，SRE 公開素材成熟，符合先建概念層的條件。

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以失敗風險為主體。

1. 先定義驗證環節問題與失敗風險邊界。
2. 再定義判讀訊號（容量門檻、退化曲線、依賴失效模式）與門檻條件。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應服務的 SRE 案例。

## 模組分工定位

本模組提供觀念、判讀與路由。實作細節由對應模組承接，確保概念層與實作層分工清晰。

- `backend/04-observability`：可觀測性模組，負責訊號定義、SLO 量測與 alert 治理實作。
- `backend/05-deployment-platform`：rollout、rollback、流量切換與環境管理實作。
- `backend/07-security-data-protection`：權限、稽核與高風險演練約束實作。
- `backend/08-incident-response`：事故處理模組，負責事故指揮、分級與復盤的事中事後流程。

## 從章節到實作的 chain

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)、那層展開機制 / 邊界 / context-dependence。例：`[circuit-breaker]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組，包括可觀測性（訊號 / SLO）、部署平台（rollout / rollback）、資安與資料保護（權限約束）與事故處理（事故閉環）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

## 跟既有模組的串接

本模組是「觀測 → 驗證 → 事故」閉環的中段、承接資安概念判讀、同時餵給事故處理閉環。資安驗證僅是驗證的一個子集、其他多數驗證是容量 / 變更 / 依賴類。

**觀測、驗證與事故閉環交接基線**：

- **來自 [可觀測性平台](/backend/04-observability/)**：SLO / SLI 量測 baseline、production 訊號是 chaos hypothesis 與 SLO 政策的依據。沒有可信訊號就沒有可信驗證。
- **餵給 [可觀測性平台](/backend/04-observability/)**：驗證需求驅動訊號設計 — chaos experiment 需要新 metric、load test 需要新 dashboard、SLO 政策需要新 alert rule。
- **餵給 [事故處理與復盤](/backend/08-incident-response/)**：把事前演練結果作為事中決策素材、game day 暴露的 runbook 缺口直接補進值班與演練能力建設。
- **來自 [事故處理與復盤](/backend/08-incident-response/)**：事故 [post-incident review](/backend/knowledge-cards/post-incident-review/) action items 回寫成新 chaos / DR 演練題目。
- **詳細閉環說明**：見 [Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

**07 資安交接基線**：

- 來自 [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)：承接資料外送與回復排序的驗證場景。
- 來自 [7.7 稽核追蹤與責任邊界](/backend/07-security-data-protection/audit-trail-and-accountability-boundary/)：承接事件證據完整性與回查演練。
- 來自紅隊 [7.R4 資源濫用與可用性破壞](/backend/07-security-data-protection/red-team/resource-abuse/)：承接壓力放大路徑與降級回復驗證。
- 來自 [7.23 資安與可靠性的共同控制面](/backend/07-security-data-protection/security-and-reliability-shared-controls/)：承接 rollback、containment、degradation 共用語意。

## 與語言教材的分工

語言教材處理測試程式如何寫得可讀、可重現、可定位。Backend reliability 模組處理測試如何在 CI、環境、資料庫、broker、網路與部署流程中被執行。

## 跨語言適配評估

可靠性驗證使用方式會受語言的測試框架、fixture 生態、並發測試能力、型別系統、fuzz 支援與容器化工具影響。同步 runtime 要測 thread pool、[connection pool](/backend/knowledge-cards/connection-pool) 與 [timeout](/backend/knowledge-cards/timeout)；async runtime 要測 event loop blocking、task cancellation 與 [backpressure](/backend/knowledge-cards/backpressure)；動態語言要用 [contract](/backend/knowledge-cards/contract/) test 與 runtime validation 補足 schema 風險；強型別語言要把型別安全延伸到外部 payload 與 migration 相容性。

## 主章規劃

| 章節                                                                                              | 主題                          | 核心責任                                                                                       |
| ------------------------------------------------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------- |
| [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)                                           | CI Pipeline                   | 分層測試、快慢測試與 artifact 管理                                                             |
| [6.2 Load test](/backend/06-reliability/load-testing/)                                            | Load Test                     | 定義 workload、吞吐與延遲基準                                                                  |
| [6.3 Fuzz campaign](/backend/06-reliability/fuzz-campaign/)                                       | Fuzz Campaign                 | 建立輸入邊界、corpus 與 crash reproduction                                                     |
| [6.4 Chaos testing](/backend/06-reliability/chaos-testing/)                                       | Chaos Testing                 | 模擬 broker、DB、network 與節點故障                                                            |
| [6.5 失敗模式預判（Pre-mortem 與 FMEA）](/backend/06-reliability/attacker-view-validation-risks/) | Failure Mode Pre-mortem       | 用驗證盲區、演練缺口與門檻失真檢查 release 風險（原「攻擊者視角」改名為 SRE first-class 詞彙） |
| [6.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/)                         | SLO & Error Budget            | 把可靠性目標轉成可驗證量測與凍結條件                                                           |
| [6.7 DR 演練與 Rollback Rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)                | DR & Rollback Rehearsal       | 把回復路徑變成定期可重播流程                                                                   |
| [6.8 Release Gate 與變更節奏](/backend/06-reliability/release-gate/)                              | Release Gate                  | 把驗證、migration、相容性納入放行判準                                                          |
| [6.9 容量與成本邊界](/backend/06-reliability/capacity-cost/)                                      | Capacity & Cost               | 把容量規劃跟成本約束變成驗證輸入                                                               |
| [6.10 Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)                 | Contract Testing              | 把跨服務 / API / event schema 契約變成可驗證 artifact                                          |
| [6.11 Migration Safety 與 DB Rollout](/backend/06-reliability/migration-safety/)                  | Migration Safety              | 把 schema migration 變成可逆、可漸進的 rollout 流程                                            |
| [6.12 Idempotency 與 Replay 驗證](/backend/06-reliability/idempotency-replay/)                    | Idempotency & Replay          | 把重試 / 重播 / 冪等從口頭約定變成可驗證屬性                                                   |
| [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)          | Perf Regression Gate          | 把效能 baseline 從一次性壓測變成持續 release gate                                              |
| [6.14 Dependency Reliability Budget](/backend/06-reliability/dependency-reliability-budget/)      | Dependency Budget             | 把內外依賴可靠性納入 SLO 計算與設計約束                                                        |
| [6.15 Environment Parity 與漂移控制](/backend/06-reliability/environment-parity/)                 | Environment Parity            | 把 staging / preprod / prod 差異作為一級風險治理                                               |
| [6.16 Test Data Management](/backend/06-reliability/test-data-management/)                        | Test Data Management          | 把 fixture / seed / production-like data 作為跨模組共用 artifact                               |
| [6.17 Feature Flag / Dark Launch Governance](/backend/06-reliability/feature-flag-governance/)    | Feature Flag Governance       | 把 feature flag 從上線工具升級為有 lifecycle / debt 治理的 artifact                            |
| [6.18 Reliability Metrics Governance](/backend/06-reliability/reliability-metrics-governance/)    | Reliability Metrics           | DORA / SPACE / CFR 等可靠性指標的選用、量測與治理                                              |
| [6.19](/backend/06-reliability/reliability-readiness-review/)                                     | Reliability Readiness Review  | 把上線前、重大變更前與高風險操作前的可靠性準備度變成可檢查門檻                                 |
| [6.20](/backend/06-reliability/experiment-safety-boundary/)                                       | Experiment Safety Boundary    | 定義 chaos、load test、DR drill 的 blast radius、停止條件與權限約束                            |
| [6.21](/backend/06-reliability/reliability-debt-backlog/)                                         | Reliability Debt Backlog      | 把反覆事故、演練缺口與手動修復累積成可排序、可關閉的 reliability debt                          |
| [6.22](/backend/06-reliability/steady-state-definition/)                                          | Steady State Definition       | 在 chaos 與 failover 前先定義系統應維持的穩定狀態與可接受退化                                  |
| [6.23](/backend/06-reliability/verification-evidence-handoff/)                                    | Verification Evidence Handoff | 把 SLO、load、chaos、DR 與 readiness 結果包成 release / incident 可用證據                      |

> 註：6.6、6.19、6.20、6.22 是本輪優先完成的可靠性前置控制面，承接 04 訊號前提並提供 08 事故流程可引用的驗證語意；其餘 6.7-6.18、6.21 仍待案例引用與細節補強。

## 個案前拓展空間

個案前拓展的責任是先建立驗證判準，再讓服務案例成為證據。可靠性驗證適合補「怎麼安全地驗證失敗」這類跨服務流程，不適合先把 Google / Netflix / Amazon 的故事直接展開。

| 拓展方向                     | 補充理由                                       | 先放位置 |
| ---------------------------- | ---------------------------------------------- | -------- |
| Reliability Readiness Review | 服務進入 production 前需要有可檢查的可靠性門檻 | 6.19     |
| Experiment Safety Boundary   | 故障注入與壓測需要明確 blast radius 與停止條件 | 6.20     |
| Reliability Debt Backlog     | 復盤與演練缺口需要形成可排序的改善 backlog     | 6.21     |
| Steady State Definition      | chaos 與 DR drill 需要先知道什麼狀態算穩定     | 6.22     |

本輪先完成其中三個前置章節：Reliability Readiness Review、Experiment Safety Boundary 與 Steady State Definition，並補強 6.6 SLO / Error Budget 政策。服務案例完成後，若教訓是「上線前準備不足」，回寫 Reliability Readiness Review；若是「實驗本身造成過大影響」，回寫 Experiment Safety Boundary；若是「反覆事故沒有被工程化」，回寫 Reliability Debt Backlog；若是「chaos 沒有穩態定義」，回寫 Steady State Definition。

## 下一輪撰寫順序

06 後續撰寫順序以「先定義可靠性政策、再定義上線準備、最後定義實驗安全」為主。可靠性驗證需要先承接 04 的訊號可信度，再把驗證結果交給 08 的事故入口、決策紀錄與復盤閉環。

| 順序 | 章節                                                                                         | 交付責任                                                     | 下游路由                                        |
| ---- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| 1    | [6.6 SLO 與 Error Budget 政策](/backend/06-reliability/slo-error-budget/)                    | 把 user journey、SLI、SLO 與 freeze 條件接成政策             | 6.8 release gate、8.1 severity trigger          |
| 2    | [6.19 Reliability Readiness Review](/backend/06-reliability/reliability-readiness-review/)   | 把上線、重大變更與高風險操作變成準備度門檻                   | 6.8 release gate、8.6 drills                    |
| 3    | [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)       | 定義 chaos、load、DR drill 的範圍與停止條件                  | 6.4 chaos testing、8.6 on-call readiness        |
| 4    | [6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)             | 定義實驗與事故共用的穩態與恢復完成條件                       | 6.20 experiment boundary、8.3 recovery          |
| 5    | [6.23 Verification Evidence Handoff](/backend/06-reliability/verification-evidence-handoff/) | 把驗證結果轉成 release gate、runbook 與事故流程可用 evidence | 4.20 evidence package、8.22 evidence write-back |

完成條件是每篇都能回答四件事：可靠性目標、驗證訊號、停止或凍結條件、事故或發布路由。這樣可靠性章節才會成為「觀測 → 驗證 → 事故」閉環的中段，而不是測試工具清單。

## 服務案例庫規劃

服務作為案例單位、累積架構脈絡與多次驗證實踐。每個服務一個資料夾、收錄該服務的 SRE 實踐、failure mode 與 chaos / DR 案例。資料夾位置：`content/backend/06-reliability/cases/{vendor-service}/`。

### T1（必寫、SRE 教學標竿）

| 服務                                              | 教學重點                                                                                                                |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| [google](/backend/06-reliability/cases/google/)   | SRE Book 原典 / SLI-SLO / [post-incident review](/backend/knowledge-cards/post-incident-review/) culture / error budget |
| [netflix](/backend/06-reliability/cases/netflix/) | Chaos Monkey / Simian Army / FIT 故障注入工具鏈                                                                         |
| [amazon](/backend/06-reliability/cases/amazon/)   | Cell-based architecture / shuffle sharding / blast radius                                                               |
| [stripe](/backend/06-reliability/cases/stripe/)   | Deploy strategy / Game day / canary 與 idempotency                                                                      |
| [shopify](/backend/06-reliability/cases/shopify/) | BFCM scaling / pod-based isolation / capacity planning                                                                  |

### T2（補不同視角）

| 服務                                                          | 教學重點                                                                   |
| ------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [linkedin](/backend/06-reliability/cases/linkedin/)           | Capacity planning / [on-call](/backend/knowledge-cards/on-call/) structure |
| [honeycomb](/backend/06-reliability/cases/honeycomb/)         | Observability-driven SRE / SLO 實作                                        |
| [cloudflare](/backend/08-incident-response/cases/cloudflare/) | Edge reliability engineering / 公開實踐（住於 08）                         |
| [microsoft](/backend/06-reliability/cases/microsoft/)         | Azure SRE / Resilience patterns                                            |

### T3（補完）

| 服務                                                  | 教學重點                                  |
| ----------------------------------------------------- | ----------------------------------------- |
| [spotify](/backend/06-reliability/cases/spotify/)     | Squad-based SRE / Backstage               |
| [pinterest](/backend/06-reliability/cases/pinterest/) | Storage capacity / cache reliability      |
| [meta](/backend/06-reliability/cases/meta/)           | 2021-10 BGP / Region failover / cell arch |

## 模組完成狀態

主章 6.1-6.5 骨架已建立、6.6-6.9 規劃中。服務案例庫（T1）已完成公開來源蒐集、個別 case 內容待展開。本模組目前處於規劃階段。

## 下一輪推演大綱

| 階段 | 產出              | 責任                                                            | 回寫位置                                |
| ---- | ----------------- | --------------------------------------------------------------- | --------------------------------------- |
| 1    | T1 服務內文       | 為 5 個 T1 服務補 2-3 個實踐卡與來源脈絡                        | `cases/{service}/`                      |
| 2    | 6.5 改名落實      | 把「攻擊者視角」改名「失敗模式預判」、用 SRE 詞彙重寫           | `6.5`                                   |
| 3    | 6.6 SLO 主章      | 把可靠性目標、量測、凍結條件變成可驗證問題節點                  | `6.6`                                   |
| 4    | 個案前拓展章      | 補 readiness、experiment safety、reliability debt、steady state | `6.19`-`6.22`                           |
| 5    | T1 第一個服務內容 | 從 `google` 或 `netflix` 起頭、寫服務 _index 加 2-3 個實踐卡    | `cases/google/` 或 `cases/netflix/`     |
| 6    | 6.7 DR 主章       | 把回復路徑變成可重播流程節點                                    | `6.7`                                   |
| 7    | 6.8 / 6.9 補完    | Release Gate 與容量成本變驗證輸入                               | `6.8` + `6.9`                           |
| 8    | 跨模組回寫        | 把 case 教訓接回可觀測性訊號、部署流程、資安約束與事故閉環      | Release Gate + shared controls + drills |

推演資產化的完成條件是讓讀者能從一個失敗風險出發，找到驗證節點、服務 case 與回寫章節。完成後可靠性模組才進入穩定維護狀態。

## Tripwire

- 寫 T1 服務第 3 個時、若 case 之間無共通分類軸 → 改用單服務獨立檔，不開資料夾。
- 寫到第 9 主章發現章節覆蓋 60%+ → 軸線過於相似、合併或重切。
- 進服務實作模組時 routing chain 走不通 → 回頭補對應主章。

## 既有可引用卡片

- [load test](/backend/knowledge-cards/load-test/)
- [chaos test](/backend/knowledge-cards/chaos-test/)
- [fuzz test](/backend/knowledge-cards/fuzz-test/)
- [idempotency](/backend/knowledge-cards/idempotency/)
- [schema migration](/backend/knowledge-cards/schema-migration/)
