---
title: "模組六：可靠性驗證流程"
date: 2026-05-01
description: "用 SRE 領域詞彙建問題節點、以服務級案例庫累積驗證脈絡，先建概念與案例庫再進實作交接"
weight: 6
---

可靠性驗證模組的核心目標是說明測試如何從單一函式擴展到整個後端系統。語言教材會處理 unit test、table-driven / parameterized test、race / async test 與 integration test；本模組負責 [CI pipeline](/backend/knowledge-cards/ci-pipeline)、壓力測試、fuzz campaign、chaos testing、SLO 與 [Release Gate](/backend/knowledge-cards/release-gate/)。

本輪規劃採問題驅動方法、用 SRE 領域 first-class 詞彙（SLI / SLO / Error Budget / Failure Mode / Chaos Hypothesis），把驗證議題拆成問題節點，蒐集公開 SRE 實踐作為服務級案例庫，再把控制面交接到 04（觀測）/ 05（部署）/ 08（事故）落地。

## Vendor / Platform 清單

實作工具見 [vendors](/backend/06-reliability/vendors/) — T1 收錄 CI（GitHub Actions / CircleCI）、Load test（k6 / Gatling / JMeter / Locust）、Chaos（Chaos Mesh / LitmusChaos / Gremlin / Toxiproxy）、SLO（Nobl9 / Sloth）共 12 個 vendor 骨架。跟 [cases/](/backend/06-reliability/cases/) 是不同維度（cases 是教學案例來源、vendors 是實作工具）。

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

- `backend/04-observability`：訊號定義、SLO 量測與 alert 治理實作。
- `backend/05-deployment-platform`：rollout、rollback、流量切換與環境管理實作。
- `backend/07-security-data-protection`：權限、稽核與高風險演練約束實作。
- `backend/08-incident-response`：事故指揮、分級與復盤的事中事後流程。

## 從章節到實作的 chain

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)、那層展開機制 / 邊界 / context-dependence。例：`[circuit-breaker]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組——`04-observability`（訊號 / SLO）/ `05-deployment-platform`（rollout / rollback）/ `07-security-data-protection`（權限約束）/ `08-incident-response`（事故閉環）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

## 跟既有模組的串接

本模組是 04 → 06 → 08 閉環的中段、承接 07 概念判讀、同時餵給 08 的事故閉環。資安驗證僅是驗證的一個子集、其他多數驗證是容量 / 變更 / 依賴類。

**04↔06↔08 閉環交接基線**：

- **來自 [模組四 觀測性](/backend/04-observability/)**：SLO / SLI 量測 baseline、production 訊號是 6.4 chaos hypothesis 與 6.6 SLO 政策的依據。沒有可信訊號就沒有可信驗證。
- **餵給 [模組四 觀測性](/backend/04-observability/)**：驗證需求驅動訊號設計 — chaos experiment 需要新 metric、load test 需要新 dashboard、SLO 政策需要新 alert rule。
- **餵給 [模組八 事故處理](/backend/08-incident-response/)**：把事前演練結果作為事中決策素材、game day 暴露的 runbook 缺口直接補進 8.6。
- **來自 [模組八 事故處理](/backend/08-incident-response/)**：事故 postmortem action items 回寫成新 chaos / DR 演練題目。
- **詳細閉環說明**：見 [8.11 Observability / Reliability / Incident Response 閉環](/backend/08-incident-response/observability-reliability-incident-loop/)。

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

| 章節                                                                                              | 主題                    | 核心責任                                                                                       |
| ------------------------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------- |
| [6.1 CI pipeline](/backend/06-reliability/ci-pipeline/)                                           | CI Pipeline             | 分層測試、快慢測試與 artifact 管理                                                             |
| [6.2 Load test](/backend/06-reliability/load-testing/)                                            | Load Test               | 定義 workload、吞吐與延遲基準                                                                  |
| [6.3 Fuzz campaign](/backend/06-reliability/fuzz-campaign/)                                       | Fuzz Campaign           | 建立輸入邊界、corpus 與 crash reproduction                                                     |
| [6.4 Chaos testing](/backend/06-reliability/chaos-testing/)                                       | Chaos Testing           | 模擬 broker、DB、network 與節點故障                                                            |
| [6.5 失敗模式預判（Pre-mortem 與 FMEA）](/backend/06-reliability/attacker-view-validation-risks/) | Failure Mode Pre-mortem | 用驗證盲區、演練缺口與門檻失真檢查 release 風險（原「攻擊者視角」改名為 SRE first-class 詞彙） |

下一輪規劃補的問題節點：

| 章節（規劃） | 主題                         | 核心責任                              |
| ------------ | ---------------------------- | ------------------------------------- |
| 6.6          | SLO 與 Error Budget 政策     | 把可靠性目標轉成可驗證量測與凍結條件  |
| 6.7          | DR 演練與 Rollback Rehearsal | 把回復路徑變成定期可重播流程          |
| 6.8          | Release Gate 與變更節奏      | 把驗證、migration、相容性納入放行判準 |
| 6.9          | 容量與成本邊界               | 把容量規劃跟成本約束變成驗證輸入      |

## 服務案例庫規劃

服務作為案例單位、累積架構脈絡與多次驗證實踐。每個服務一個資料夾、收錄該服務的 SRE 實踐、failure mode 與 chaos / DR 案例。資料夾位置：`content/backend/06-reliability/cases/{vendor-service}/`。

### T1（必寫、SRE 教學標竿）

| 服務                                              | 教學重點                                                    |
| ------------------------------------------------- | ----------------------------------------------------------- |
| [google](/backend/06-reliability/cases/google/)   | SRE Book 原典 / SLI-SLO / postmortem culture / error budget |
| [netflix](/backend/06-reliability/cases/netflix/) | Chaos Monkey / Simian Army / FIT 故障注入工具鏈             |
| [amazon](/backend/06-reliability/cases/amazon/)   | Cell-based architecture / shuffle sharding / blast radius   |
| [stripe](/backend/06-reliability/cases/stripe/)   | Deploy strategy / Game day / canary 與 idempotency          |
| [shopify](/backend/06-reliability/cases/shopify/) | BFCM scaling / pod-based isolation / capacity planning      |

### T2（補不同視角）

| 服務                                                          | 教學重點                                           |
| ------------------------------------------------------------- | -------------------------------------------------- |
| [linkedin](/backend/06-reliability/cases/linkedin/)           | Capacity planning / on-call structure              |
| [honeycomb](/backend/06-reliability/cases/honeycomb/)         | Observability-driven SRE / SLO 實作                |
| [cloudflare](/backend/08-incident-response/cases/cloudflare/) | Edge reliability engineering / 公開實踐（住於 08） |
| [microsoft](/backend/06-reliability/cases/microsoft/)         | Azure SRE / Resilience patterns                    |

### T3（補完）

| 服務                                                  | 教學重點                                  |
| ----------------------------------------------------- | ----------------------------------------- |
| [spotify](/backend/06-reliability/cases/spotify/)     | Squad-based SRE / Backstage               |
| [pinterest](/backend/06-reliability/cases/pinterest/) | Storage capacity / cache reliability      |
| [meta](/backend/06-reliability/cases/meta/)           | 2021-10 BGP / Region failover / cell arch |

## 模組完成狀態

主章 6.1-6.5 骨架已建立、6.6-6.9 規劃中。服務案例庫（T1）骨架建立、個別 case 內容待補。本模組目前處於規劃階段。

## 下一輪推演大綱

| 階段 | 產出              | 責任                                                         | 回寫位置                            |
| ---- | ----------------- | ------------------------------------------------------------ | ----------------------------------- |
| 1    | T1 服務骨架       | 建 5 個 T1 服務的 `cases/{service}/_index.md` 規劃骨架       | `cases/`                            |
| 2    | 6.5 改名落實      | 把「攻擊者視角」改名「失敗模式預判」、用 SRE 詞彙重寫        | `6.5`                               |
| 3    | 6.6 SLO 主章      | 把可靠性目標、量測、凍結條件變成可驗證問題節點               | `6.6`                               |
| 4    | T1 第一個服務內容 | 從 `google` 或 `netflix` 起頭、寫服務 _index 加 2-3 個實踐卡 | `cases/google/` 或 `cases/netflix/` |
| 5    | 6.7 DR 主章       | 把回復路徑變成可重播流程節點                                 | `6.7`                               |
| 6    | 6.8 / 6.9 補完    | Release Gate 與容量成本變驗證輸入                            | `6.8` + `6.9`                       |
| 7    | 跨模組回寫        | 把 case 教訓接回 04 訊號 / 05 部署 / 07 約束 / 08 事故閉環   | `6.8` + `7.23` + `8.6`              |

推演資產化的完成條件是讓讀者能從一個失敗風險出發，找到驗證節點、服務 case 與回寫章節。完成後可靠性模組才進入穩定維護狀態。

## Tripwire

- 寫 T1 服務第 3 個時、若 case 之間無共通分類軸 → 改用單服務獨立檔，不開資料夾。
- 寫到第 9 主章發現章節覆蓋 60%+ → 軸線過於相似、合併或重切。
- 進服務實作模組時 routing chain 走不通 → 回頭補對應主章。
