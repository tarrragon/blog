---
title: "模組九：效能工程與容量規劃"
date: 2026-05-12
description: "把『目前配置能撐多少、要加多少機器』變成可量化、可驗證、可改進的工程流程"
weight: 9
tags: ["backend", "performance", "capacity"]
---

效能工程與容量規劃模組的核心目標是回答兩個工程問題：目前的服務配置能承載多少負載，以及面對預期或意外的流量增長時要加多少資源。語言教材會處理 algorithm、hot path 與 memory profile 等程式層效能；本模組負責 workload modeling、壓測工具選型、saturation discovery、瓶頸定位、容量規劃、成本邊界、效能可觀測性與改進閉環。

本模組跟 [模組六：可靠性驗證流程](/backend/06-reliability/) 是 sibling 工程紀律。06 看「失敗模式如何被驗證」，走 SLO、Error Budget、Failure Mode、Chaos Hypothesis 的詞彙；09 看「正常負載如何被量化與規劃」，走 Workload、Saturation、Capacity、Cost、Throughput、Latency 的詞彙。兩個模組共用案例庫但讀法不同：06 從案例讀「失敗模式驗證」、09 從案例讀「容量量化實踐」。

## 教材定位

效能工程的角色是把「我不知道目前配置能撐多少」這個常見焦慮，變成可量測、可重播、可改進的工程流程。

多數後端服務不會每天遇到高併發，真正的工程問題是平常運作時的容量地圖。平常運作正常時，目前的配置距離 saturation 還有多遠；當意外流量出現時，現有配置能撐到 autoscaling 介入嗎；要加機器時，怎麼算出該加多少、加在哪一層；加了機器之後，怎麼確認瓶頸真的被移除了。

這四個問題不需要假設高併發場景，而是要求系統在任何配置下都能回答「現在的容量地圖長什麼樣」。沒有這張地圖，加機器是猜測、不加機器是賭運氣、改架構是恐慌。

## 教材邊界

| 類型       | 放在語言教材                                                         | 放在本模組                                                                      |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 程式層效能 | algorithm、data structure、hot path、memory profile、micro benchmark | workload model、production traffic replay、end-to-end load test                 |
| 並發模型   | goroutine、event loop、thread pool、connection pool 的程式邊界       | 並發設計如何決定 saturation 與 connection pressure 邊界                         |
| Profiling  | runtime profiler、flame graph、heap dump 解讀                        | continuous profiling 接入、profile diff 作為 regression 定位                    |
| 容量量測   | resource metric API、process memory、GC pause 訊號                   | saturation metric、USE method、RED method、cost dashboard                       |
| 容量規劃   | （不負責）                                                           | peak forecast、headroom model、growth curve、autoscaling sizing、cost ceiling   |
| 壓測工具   | （不負責）                                                           | k6、JMeter、Gatling、Locust、Vegeta、production traffic replay 工具的選型與整合 |

## 問題節點

問題節點先描述「不知道答案會發生什麼」，再描述「怎麼建立答案」。讀者能先理解這個問題為什麼重要，再看到怎麼處理。

| 節點                      | 工程問題                                   | 觀察訊號                                                         |
| ------------------------- | ------------------------------------------ | ---------------------------------------------------------------- |
| Workload Modeling         | 壓測模型是否貼近 production traffic shape  | percentile distribution、cohort mix、burst pattern               |
| Load Test Tooling         | 該用哪種工具、怎麼整合 CI 跟 staging       | tool capability vs workload shape、CI 整合成本                   |
| Saturation Discovery      | 配置距離飽和還有多少 headroom              | throughput plateau、latency knee、resource saturation            |
| Bottleneck Localization   | 瓶頸在哪一層、是 app / DB / cache / broker | resource utilization、queue depth、connection exhaustion         |
| Capacity Planning         | 要加多少機器、加在哪一層                   | peak forecast、headroom budget、growth curve                     |
| Cost Engineering          | 容量擴張的成本曲線、降級的成本邊界         | cost per request、autoscaling cost ceiling、over-provision waste |
| Performance Observability | 容量訊號怎麼看、跟 SLO 怎麼接              | saturation metric、cost attribution、SLO budget                  |
| Improvement Loop          | 從壓測到 release 怎麼閉環                  | profile diff、regression gate、canary perf signal                |
| Production Validation     | 怎麼在 production 安全驗證新配置           | shadow traffic、dark launch、canary perf check                   |
| Peak Event Readiness      | 預知的流量事件怎麼準備                     | event capacity forecast、pre-warm checklist、rollback path       |

這張表的責任是路由。當讀者卡住時，先問三個問題：是模型還是訊號的問題、是量測還是規劃的問題、是技術瓶頸還是成本邊界的問題。這三個問題會把讀者導向不同主章。

## 跟既有模組的分工

| 既有模組                                        | 09 與其分工                                                                                                                |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| [00 服務選型](/backend/00-service-selection/)   | 00 提供需求量化輸入（traffic / data / failure cost），09 把這些輸入翻成壓測模型與容量計畫                                  |
| [04 可觀測性](/backend/04-observability/)       | 04 提供 metric / dashboard / SLO baseline，09 定義 saturation metric、USE / RED 訊號、cost attribution 需求                |
| [05 部署平台](/backend/05-deployment-platform/) | 05 處理 autoscaling、HPA、load balancer 的平台實作，09 提供 capacity 規劃輸入（要 scale 到多少、什麼條件觸發）             |
| [06 可靠性驗證](/backend/06-reliability/)       | 06 看失敗模式（chaos / error budget / SLO），09 看正常負載（workload / saturation / capacity），共享 6.2 / 6.9 / 6.13 入口 |
| [08 事故處理](/backend/08-incident-response/)   | 08 處理 capacity-related incident 的事中事後，09 提供事前演練與容量門檻                                                    |

跟 06 的邊界要特別清楚。06.2 load-testing、6.9 capacity-cost、6.13 perf regression gate 留下「在驗證流程中的角色」入口；09 負責「壓測理論、模型、工具、瓶頸定位、容量規劃、成本邊界」的深化。當讀者問「load test 在 release gate 的判讀條件」屬 06；問「load test 的 workload model 怎麼設計、工具怎麼選、瓶頸怎麼定位」屬 09。

## 從章節到實作的 chain

各章節交付三樣：問題節點、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation。

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)，那層展開機制、邊界、context-dependence。例：`[saturation point]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組，包括可觀測性（saturation metric / cost dashboard）、部署平台（autoscaling policy / HPA sizing）、可靠性（perf regression gate / SLO budget）與事故處理（capacity incident playbook）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

## 主章規劃

| 章節                                                                                       | 主題                      | 核心責任                                                               |
| ------------------------------------------------------------------------------------------ | ------------------------- | ---------------------------------------------------------------------- |
| [9.1 壓測理論與系統行為](/backend/09-performance-capacity/performance-theory/)             | Performance Theory        | Little's Law、queueing theory、USL、saturation curve 的工程意義        |
| [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)               | Workload Modeling         | 把 production traffic shape 翻成可重播的壓測模型                       |
| [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)                    | Load Test Tooling         | k6 / JMeter / Gatling / Locust / Vegeta / Production Replay 的選型判讀 |
| [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)         | Saturation Discovery      | 找出 throughput plateau 與 latency knee 的方法                         |
| [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)              | Bottleneck Localization   | 從 app 到 DB、cache、broker、第三方 quota 的逐層定位                   |
| [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)                    | Capacity Planning         | peak forecast、headroom、growth curve、autoscaling sizing              |
| [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/)            | Cost Engineering          | cost per request、cost curve、降級成本、over-provisioning trade-off    |
| [9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/)            | Performance Observability | saturation metric、USE / RED method、cost dashboard                    |
| [9.9 Performance Improvement Loop](/backend/09-performance-capacity/improvement-loop/)     | Improvement Loop          | 壓測 → profile → fix → re-test → release gate 的閉環                   |
| [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/)       | Production Validation     | shadow traffic、dark launch、canary、production-like load test         |
| [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)                | Peak Event Readiness      | 活動、季節性流量、推廣事件的 capacity readiness 流程                   |
| [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/) | SLO Coupling              | performance budget 跟 SLO / error budget 的對接                        |

> 12 個主章已完成首輪正文。後續工作是補 `vendors/` 工具入口、提升案例回寫密度，並校正各章與 06 reliability 的分工。

主章撰寫順序：9.1 → 9.2 → 9.4 → 9.5 → 9.6 → 9.3 → 9.8 → 9.9 → 9.7 → 9.10 → 9.11 → 9.12。理論與模型先行，工具落地放在 saturation 與 bottleneck 概念成熟之後，最後處理成本與 production 驗證的進階主題。

## 案例庫規劃

案例庫主軸採「AWS Customer Success Stories」公開案例。這層案例提供具體流量、實例、延遲、成本數字，比一般 engineering blog 更接近實戰判讀。完整索引、讀法與規劃中案例見 [9.C 案例正文](/backend/09-performance-capacity/cases/)。

### 已發佈案例

| 章節                                                                                     | 主題                            | 負載形狀                                 |
| ---------------------------------------------------------------------------------------- | ------------------------------- | ---------------------------------------- |
| [9.C1](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/)         | AWS Prime Day 2025 dogfood      | 可預期極端峰值（SQS 1.66 億 msg/sec）    |
| [9.C2](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)       | GR8 Tech 體育博彩 AI 預測式擴容 | 事件型不可預期峰值（54K TPS @ 25ms p95） |
| [9.C3](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) | Coinbase 超低延遲交易           | 無峰值低延遲（100K msg/sec、sub-ms）     |

三篇對應三種負載形狀，讀完可以開始把自己的服務歸類，再回到對應主章規劃容量地圖。

### 規劃中案例（補不同視角與規模）

| 候選來源     | 預期教學重點                                        |
| ------------ | --------------------------------------------------- |
| Lyft / Slack | 微服務 + Auto Scaling、事件型流量的擴容粒度治理     |
| Riot Games   | EKS 多集群（246 cluster）治理、跨地區延遲與成本平衡 |
| FanDuel      | 直播流量 + 投注峰值的雙重峰值對齊                   |
| Hotstar      | 即時 live streaming 全球峰值（1860 萬同時觀看）     |
| Zoom         | COVID 期間 30 倍成長（1000 萬 → 3 億 DAU）          |

### Engineering Blog 補充候選

當 AWS 案例缺乏某些工程紀律的深度（例如 chaos hypothesis、cell-based architecture 細節），補引 engineering blog 作為交叉驗證。候選來源：Shopify BFCM、Netflix Tech Blog、Amazon Builders' Library、Google SRE Book、LinkedIn Engineering、Stripe Engineering、Cloudflare Blog、Discord Engineering、Uber Engineering、Pinterest Engineering 等。這層不另開資料夾，補在主章「案例對照」段。

## 跨語言適配評估

效能工程使用方式會受語言的並發模型、runtime overhead、profiler 工具鏈與 client library 成熟度影響。

1. 同步 thread-based runtime（Java、C#、傳統 Python / Ruby）：[connection pool](/backend/knowledge-cards/connection-pool/) 是首要瓶頸、blocking I/O 會把 thread 鎖住、壓測時要量 thread saturation 跟 pool exhaustion。
2. async / event-loop runtime（Node.js、Python asyncio、Tokio）：要量 event loop lag、避免 CPU-bound work 阻塞 loop、[backpressure](/backend/knowledge-cards/backpressure/) 失控時 throughput 跟 latency 會同時崩。
3. Goroutine 或 lightweight task runtime（Go、Erlang）：goroutine 廉價但下游連線、檔案 handle、broker channel 仍是昂貴資源、要量「廉價並發 → 昂貴資源」的轉換點。
4. JIT 語言（JVM、.NET）：warmup 期 latency 高、壓測要區分 cold 與 warm 階段、profile diff 要排除 GC noise。
5. AOT 語言（Go、Rust、C++）：[cold start](/backend/knowledge-cards/cold-start/) 較快、但 GC（Go）或 allocator 行為仍影響長時間 latency。
6. 動態語言（Python、Ruby、PHP）：interpreter overhead 是基線、要先排除 framework 預設配置的隱性成本（worker model、GIL、autoload）。

## 服務分類規範

每個討論具體壓測工具或容量服務的章節（k6、JMeter、Gatling、Locust、Vegeta、Grafana k6 Cloud、AWS Distributed Load Testing、Datadog Synthetics、Akamas），都必須包含「成本權衡與機會成本」段落，至少回答：

1. 這個工具降低哪一種風險（容量未知、缺少持續驗證、缺少瓶頸定位）。
2. 工具本身的維運成本：runner、artifact、結果儲存、CI 整合成本。
3. 在大規模壓測下會增加哪些雲端成本（流量費、跨區、目標服務的容量壓力）。
4. 團隊需要承擔哪些前置成本：workload model 設計、結果判讀、baseline 維護。
5. 若選擇更簡單方案（人工 ad-hoc 壓測），會承擔哪些風險。
6. 什麼條件出現時，原本的工具選擇應該被重新評估。

## Vendor 清單

實作工具見 [vendors](/backend/09-performance-capacity/vendors/) — 已建立 k6 / JMeter / Gatling / Locust / Vegeta 五個壓測工具頁、GoReplay / Service Mesh Mirroring / AWS VPC Traffic Mirroring 三個 production traffic replay 頁，Datadog Continuous Profiler / Pyroscope / Parca 三個 continuous profiling 頁，以及 Akamas / Vantage / CloudHealth / AWS Cost Explorer 四個 capacity / cost analysis 頁。跟 [06 vendors](/backend/06-reliability/vendors/) 的差異：06 收錄壓測工具是為了「驗證流程的工具鏈」、09 收錄是為了「效能工程的工具鏈」、選型角度不同。具體撰寫順序見 [0.17 後端真實服務討論大綱](/backend/00-service-selection/service-entity-discussion-outline/)。

Deep article（工具自身的配置、故障、容量）跟 migration playbook（跨工具遷移流程）的撰寫進度見 [vendors/](/backend/09-performance-capacity/vendors/) 的「內容覆蓋進度」段。

## 09 模組專屬知識卡片

09 模組已建立 22 張效能工程與容量規劃專屬卡片、覆蓋理論基礎、量測方法、規劃決策、production 驗證與 SLO 治理四個面向。

**理論基礎（5 張）**：

- [Little's Law](/backend/knowledge-cards/little-law/) — 並發、到達率、逗留時間的數學關係
- [Universal Scalability Law](/backend/knowledge-cards/universal-scalability-law/) — 擴容到某點後 throughput 反向下降的數學模型
- [Saturation Point](/backend/knowledge-cards/saturation-point/) — linear / knee / cliff 三段曲線的臨界點
- [USE Method](/backend/knowledge-cards/use-method/) — 資源層 Utilization / Saturation / Errors
- [RED Method](/backend/knowledge-cards/red-method/) — 請求層 Rate / Errors / Duration

**Workload 與容量規劃（8 張）**：

- [Workload Model](/backend/knowledge-cards/workload-model/) — production traffic shape 量化模型
- [Tail Latency](/backend/knowledge-cards/tail-latency/) — p99 / p999 長尾為何比平均更能反映 saturation
- [Hot Partition](/backend/knowledge-cards/hot-partition/) — 分散式 KV 的隱性 saturation
- [Peak Forecast](/backend/knowledge-cards/peak-forecast/) — 預期峰值的預測方法
- [Headroom Budget](/backend/knowledge-cards/headroom-budget/) — 容量規劃的安全餘量
- [Growth Curve](/backend/knowledge-cards/growth-curve/) — 五種典型成長形狀
- [Predictive Scaling](/backend/knowledge-cards/predictive-scaling/) — 預測式擴容
- [Scheduled Scaling](/backend/knowledge-cards/scheduled-scaling/) — 已知時間表預先擴容

**Production 驗證（5 張）**：

- [Shadow Traffic](/backend/knowledge-cards/shadow-traffic/) — production traffic 複製驗證
- [Dark Launch](/backend/knowledge-cards/dark-launch/) — UI 入口暫不開放的發布模式
- [Canary Perf Check](/backend/knowledge-cards/canary-perf-check/) — canary 階段的 latency 退化檢查
- [Profile Diff](/backend/knowledge-cards/profile-diff/) — 兩次 profile 對比找退化原因
- [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/) — production 持續低 overhead profile

**成本與 SLO（4 張）**：

- [Cost Per Request](/backend/knowledge-cards/cost-per-request/) — 雲端成本 unit economics
- [Performance Budget](/backend/knowledge-cards/performance-budget/) — 跟 error budget 並列的效能退化額度
- [Latency Budget](/backend/knowledge-cards/latency-budget/) — end-to-end latency 拆到每 stage 配額
- [SLO Baseline Drift](/backend/knowledge-cards/slo-baseline-drift/) — SLO 需要重新校準的現象

## 既有可引用卡片

從其他模組沿用的卡片：

- [Load Test](/backend/knowledge-cards/load-test/)
- [Throughput](/backend/knowledge-cards/throughput/)
- [Consumer Capacity](/backend/knowledge-cards/consumer-capacity/)
- [Connection Pool](/backend/knowledge-cards/connection-pool/)
- [Backpressure](/backend/knowledge-cards/backpressure/)
- [Load Shedding](/backend/knowledge-cards/load-shedding/)
- [Rate Limit](/backend/knowledge-cards/rate-limit/)
- [Cold Start](/backend/knowledge-cards/cold-start/)
- [Thundering Herd](/backend/knowledge-cards/thundering-herd/)
- [Bulkhead](/backend/knowledge-cards/bulkhead/)
- [SLI / SLO](/backend/knowledge-cards/sli-slo/)
- [Error Budget](/backend/knowledge-cards/error-budget/)
- [Metric Cardinality](/backend/knowledge-cards/metric-cardinality/)
- [Game Day](/backend/knowledge-cards/game-day/)
- [Blast Radius](/backend/knowledge-cards/blast-radius/)
- [Autoscaling](/backend/knowledge-cards/autoscaling/)

## 模組方法

問題驅動方法的核心是讓案例退到證據角色，讓知識網以「容量量化問題」為主體。

1. 先定義效能或容量問題的責任邊界。
2. 再定義判讀訊號（saturation curve、cost curve、percentile distribution）與門檻條件。
3. 接著定義交接路由與前置控制面。
4. 最後在問題觸發時引用對應服務案例。

## 規劃方向

本模組的核心是把模組架構為「容量量化問題 + 服務級實踐案例」兩層結構。

1. **問題節點先行**：9.1-9.12 主章已建立理論、模型、工具、saturation、瓶頸、容量、成本、可觀測性、改進閉環、production 驗證、高峰準備與 SLO 對接的基礎。
2. **服務級案例庫**：以公開效能與容量實踐（Shopify BFCM / Netflix scale / Amazon cost / Google performance budget / LinkedIn capacity planning）作 cases，每個服務累積容量規劃脈絡。
3. **跟 06 共用案例但不同讀法**：服務 case 同一批、但 06 讀「失敗模式驗證」、09 讀「容量量化實踐」、避免重複案例蒐集成本。

不經實作即可推進的理由：效能工程的價值在「容量地圖建立與成本邊界判讀」，這層跟具體框架解耦，performance engineering 公開素材成熟，符合先建概念層的條件。

## Tripwire

- 寫到第 6 章發現持續繞回 06 已有章節 → 軸線過於相似、合併回 06 或重切。
- 案例庫跟 06 cases/ 重疊度 > 70% → 改共用 06 案例、不另起一份。
- 工具章節寫起來像 vendor 比較表、缺判讀邏輯 → 改寫成「workload model → 工具選型」的決策章節。
- 9.6 capacity planning 跟 9.7 cost engineering 變成兩篇都在講同一個 trade-off → 合併。
- 9.10 production validation 跟 [06.20 experiment safety boundary](/backend/06-reliability/experiment-safety-boundary/) 內容開始重疊 → 明確分工：9.10 走「正常負載驗證」、6.20 走「故障注入安全邊界」。
- 寫 T1 服務第 3 個時、若 case 之間無共通分類軸 → 改用單服務獨立檔，不開資料夾。

## 模組完成狀態

模組主章與案例庫已完成首輪正文，`vendors/` 已建立壓測工具、production traffic replay 與 continuous profiling 第一批工具頁。後續工作排序：先補 capacity / cost analysis 工具頁，再提高 9.7-9.12 對案例的回寫密度，最後整理跟 06 reliability 共用案例的分工。

---

_文件版本：v0.1.0_
_最後更新：2026-05-12_
_系列狀態：主章首輪完成，進入工具入口與案例回寫補強_
