---
title: "6.1 CI pipeline"
date: 2026-04-23
description: "CI pipeline 的分層策略、artifact 管理、flaky 治理與 release gate 輸入"
weight: 1
tags: ["backend", "reliability"]
---

## 概念定位

[CI pipeline](/backend/knowledge-cards/ci-pipeline/) 把快速回饋、慢速驗證與可重現產物切成不同層，讓每次變更都能在一致條件下被判讀。

這一層關心的是「變更能不能被穩定驗證」。pipeline 的價值在於分層、隔離與可追蹤，讓 flaky 訊號不會直接污染放行判斷。

## 核心判讀

CI 的健康度先看回饋節奏，再看訊號品質。fast path 應該覆蓋最常見的破壞面，slow path 負責深層驗證，artifact 則要能從同一份輸入重播。

判讀時先看四件事：

- stage 是否按成本與風險分層
- artifact 是否重用，不是每次從 source 重建
- environment variables 是否封裝，避免跨環境漂移
- flaky test 是否有治理路徑，而不是只靠 retry

## 分層策略

CI 分層的責任是讓不同成本的驗證跑在不同時機，讓最常見的破壞面最快被攔住，高成本驗證只在值得時跑。

### Fast path

fast path 在每次 push 觸發，目標是 5 分鐘內回饋。涵蓋 lint、type check、unit test 與 [contract](/backend/knowledge-cards/contract/) test。這一層只驗證單一變更的語法與邏輯正確性，不碰外部依賴。

fast path 結果可信的條件是測試不依賴外部狀態。當 unit test 需要真實 DB 或 broker，它就不再屬於 fast path — 移到 slow path，或用 contract test 替代跨服務驗證。

### Slow path

slow path 在 merge request 觸發，允許較長執行時間（15-45 分鐘）。涵蓋 integration test、security scan、load baseline 與跨服務 schema 相容性。這一層用真實依賴驗證變更在服務邊界上的行為。

Microsoft 的[變更治理實踐](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/)把變更按風險分層，高風險變更（schema migration、payment path、config rollout）走更完整的 slow path，低風險變更只需 fast path 通過。這種分層讓 CI 資源集中在真正需要深層驗證的變更上，同時維持低風險變更的交付速度。

### Scheduled path

scheduled path 定期（每日或每週）執行，涵蓋 full regression、[fuzz campaign](/backend/06-reliability/fuzz-campaign/)、chaos smoke test 與長時間 soak test。這一層驗證的是累積退化，而不是單次變更的破壞。

scheduled path 的判讀不看單次 pass/fail，而是看趨勢：coverage delta 是否持續下降、fuzz corpus 是否收斂、regression 新增 failure 是否集中在特定模組。

## Artifact 管理

Artifact 讓同一份 build output 能從 CI 一路到 staging 到 production，每一步都可重播。

immutable artifact 的核心約束是 build 一次、部署多次。CI 產出的 container image 或 binary 帶版本標籤（commit hash + build number），後續環境不重新 build，只替換 config。這樣才能確保 staging 驗證通過的產物跟 production 部署的產物是同一份。

cache 策略影響 CI 回饋速度與可信度的平衡。dependency cache（npm / go mod / pip）加速 build，但需要定期 invalidation 避免過期依賴殘留。build output cache 則需要嚴格的 key 設計，確保 source 變更後不會沿用舊 artifact。

Stripe 的[零停機遷移實踐](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)對 artifact 有額外要求：交易路徑的變更需要 artifact 能重播到相同狀態，確保 [idempotency](/backend/knowledge-cards/idempotency/) 驗證在 CI 與 production 看到一致的行為。

## Flaky test 治理

flaky test 的責任是讓 CI 訊號維持可信度。當 flaky 率持續上升，團隊會開始忽略 CI 結果，pipeline 從可靠性 gate 退化成形式流程。

### 識別

flaky 識別靠 retry 分析。當同一個 test case 在同一份 commit 上連續跑出不同結果，那就是 flaky 候選。按連續失敗 / 成功交替的頻率排序，比按失敗率排序更能抓到高噪音來源。

### 隔離

quarantine queue 是把已識別的 flaky test 從 gate-blocking path 移到 non-blocking path。quarantine 的目的是保護 gate 判讀可信度，同時維持 flaky 修復的追蹤壓力。quarantine 不是永久停靠 — 超過修復期限的 flaky test 必須決定是修復還是刪除。

### 判讀門檻

flaky 率超過 5% 時，CI gate 的訊號開始失真：團隊無法確定 failure 是真回歸還是 flaky。超過 10% 時，CI pipeline 實質上失去 gate 功能 — retry 變成常態，failure 預設被忽略。此時應暫停新功能開發，集中修復 flaky backlog。這些門檻是基於中大型測試套件（500+ test cases）的經驗值。測試套件較小時，單一 flaky test 的比率衝擊更大，門檻應更低。

## Environment 隔離

CI 環境的隔離程度決定了測試結果的可信度下限。

### Runner 隔離

shared runner 會把不同 PR 的測試跑在同一台機器上。當 integration test 需要佔用 port、寫入 local state 或消耗大量記憶體，跨 job 干擾就會出現。ephemeral runner（每次 job 用乾淨環境）消除這類問題，但成本更高。判斷點是測試是否依賴 local state — 有依賴就用 ephemeral。

### Secret 管理

CI secret（API key、DB credential、cloud token）需要按環境隔離。staging secret 不應該在 PR pipeline 可用，production secret 不應該在 staging pipeline 可用。secret 洩露的常見路徑是 CI log 輸出與 artifact 殘留 — 兩處都需要遮罩。

### Load test 資源池

LinkedIn 的[容量 headroom 實踐](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)把自動化壓測接進 CI。當 load test 跑在 CI 環境時，需要獨立資源池，避免壓測流量影響其他 pipeline job 的執行速度與穩定性。load test runner 的 quota 跟一般 CI runner 分開管理。

## CI 作為 Release Gate 輸入

CI 的最終產出不只是 pass/fail，而是一組可供 [release gate](/backend/knowledge-cards/release-gate/) 判讀的 evidence。

| 產出                | 判讀用途                        | 下游消費者                                                                          |
| ------------------- | ------------------------------- | ----------------------------------------------------------------------------------- |
| pipeline status     | 所有 stage 是否通過             | [6.8 release gate](/backend/06-reliability/release-gate/)                           |
| test coverage delta | 本次變更是否降低覆蓋率          | [6.13 perf regression gate](/backend/06-reliability/performance-regression-gate/)   |
| artifact checksum   | 部署產物是否與 CI 產出一致      | [6.23 evidence handoff](/backend/06-reliability/verification-evidence-handoff/)     |
| flaky rate snapshot | gate 判讀可信度是否在可接受範圍 | [6.18 reliability metrics](/backend/06-reliability/reliability-metrics-governance/) |

Google 的 [error budget 政策](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)把 CI 定位成 release gate 的前置訊號來源：CI pipeline 產出的 evidence 直接進入 error budget 判讀流程。當 budget 消耗加速時，CI gate 的門檻隨之提高 — 從只需 fast path 通過，升級到要求 slow path 全部通過加人工 review。

## 案例對照

- [Google](/backend/06-reliability/cases/google/error-budget-policy-and-release-gating/)：CI pipeline status 是 error budget 政策的前置訊號，budget 消耗速度直接影響 CI gate 門檻高低。
- [Microsoft](/backend/06-reliability/cases/microsoft/change-management-and-reliability-governance/)：按變更風險分層走不同 CI path，高風險變更需要更完整的 slow path 驗證。
- [LinkedIn L1](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/)：容量 headroom 綁值班分層，CI 回饋是容量決策的輸入。
- [LinkedIn L2](/backend/06-reliability/cases/linkedin/automated-load-testing-and-capacity-forecasting/)：自動化壓測接進 CI，load test 需要獨立資源池避免干擾其他 pipeline job。
- [Stripe](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/)：交易路徑的 idempotency 測試在 CI 跑，artifact 必須能重播到相同狀態。

## 判讀訊號

| 訊號                                      | 意義                                | 行動建議                                                                |
| ----------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------- |
| CI 時長 > 30 min                          | fast path 混入了 slow path 測試     | 重新分層，把 integration test 移到 merge gate                           |
| fast / slow 沒分層                        | 每次 push 跑全部測試，回饋太慢      | 拆 fast path（< 5 min）與 slow path（< 45 min）                         |
| flaky 率 > 5%                             | gate 判讀可信度開始下降             | 啟動 quarantine + 集中修復週期                                          |
| artifact 每次重建                         | 無法確認 staging 跟 production 同份 | 改成 build once、deploy many                                            |
| env var 跨環境寫死                        | staging 與 prod 行為不同            | 改用 per-environment secret injection                                   |
| retry 成功率 > 20% 且被視為 pipeline 通過 | 真回歸被 flaky retry 遮蓋           | retry pass 不等於 gate pass，需人工確認                                 |
| flaky test 無 owner、修復靠志願者         | test 跟 team 責任未對齊             | 建立 test ownership registry、每個 test file 或 suite 有明確 owner team |

## 交接路由

- [6.10 contract testing](/backend/06-reliability/contract-testing/)：把跨服務契約納入 CI fast path
- [6.13 perf regression gate](/backend/06-reliability/performance-regression-gate/)：把效能 baseline 變成 CI slow path gate
- [6.15 environment parity](/backend/06-reliability/environment-parity/)：CI 環境隔離是 parity 的前置條件
- [6.16 test data](/backend/06-reliability/test-data-management/)：把 fixture / seed 納入 CI artifact 管理
- [6.8 release gate](/backend/06-reliability/release-gate/)：CI evidence 是 release gate 的主要輸入
- [6.23 evidence handoff](/backend/06-reliability/verification-evidence-handoff/)：CI artifact checksum 進入證據交接
