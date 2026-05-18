---
title: "k6"
date: 2026-05-15
description: "用 scriptable scenario 建立 API、protocol 與 CI 友善壓測的效能工程工具"
weight: 1
tags: ["backend", "performance", "capacity", "vendor", "k6", "load-test"]
---

k6 的核心責任是把 workload model 轉成可重跑、可版本化、可接到 CI 的壓測 scenario。它適合 API、HTTP、gRPC、WebSocket 與 browser-style flow 的負載驗證，重點在用程式化腳本描述使用者行為、負載階段、threshold 與結果輸出。

## 定位

k6 適合把壓測納入工程流程。當團隊已經能描述 traffic shape、endpoint mix、arrival rate、think time 與 stop condition，k6 可以把這些模型寫成腳本，讓每次 release、capacity review 或 peak-event readiness 都能重跑同一組驗證。

這個定位讓 k6 接到三個主章。它從 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 接收流量模型，從 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 接收 ramp-up 與 knee point 判讀，從 [9.10 Production-Side 驗證](/backend/09-performance-capacity/production-validation/) 接收 canary、dark launch 或 production-like load test 的安全邊界。

## 適用場景

API 壓測是 k6 最穩定的入口。Checkout、login、search、order query、payment callback mock 與 internal API 都可以用 scenario 表達，並用 threshold 把 latency、error rate 與 throughput 轉成 pass / fail 訊號。

CI performance gate 是 k6 的常見價值。團隊可以在 merge、nightly、pre-release 或 game day 前跑固定 baseline，觀察 p95 / p99、error rate、throughput 與 regression trend，再把結果交給 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)。

Peak readiness rehearsal 適合用 k6 表達階段式負載。活動前可以用 ramping arrival rate 模擬 T-90、T-30、T-7、T-1 與 T-0 的負載階段，並把結果回寫到 [9.11 高峰事件準備](/backend/09-performance-capacity/peak-event-readiness/)。

## 選型判準

| 判準         | k6 的價值                                      | 需要補的能力                      |
| ------------ | ---------------------------------------------- | --------------------------------- |
| 腳本化       | scenario、threshold、setup / teardown 可版本化 | production traffic 抽樣與模型校正 |
| CI 友善      | CLI 與 artifact 容易接 pipeline                | 長期趨勢儲存與 release gate 語意  |
| API 導向     | HTTP / gRPC / WebSocket 等常見 API 場景清楚    | 複雜瀏覽器互動與端到端資料準備    |
| 團隊學習成本 | JavaScript 腳本容易被多數 backend 團隊接手     | 大型分散式 runner 與測試資料治理  |

腳本化價值來自可重跑。一次性的壓測只能回答當天配置能撐多少；可版本化 scenario 可以回答 release 後容量曲線有沒有漂移，並讓退化調查回到同一份 workload model。

CI 友善價值來自交接成本低。壓測結果要能轉成 artifact、threshold、trend 與 gate decision，才會從「工程師手動跑工具」變成 release 流程的一部分。

API 導向價值來自後端路徑明確。k6 很適合 checkout API、search API、internal API 與 webhook receiver；如果主要問題是完整 browser UX、第三方真實支付或多裝置同步，文章要把資料準備、side effect 與環境隔離另外寫清楚。

## 跟其他工具的取捨

k6 和 JMeter 的主要差異是工作方式。k6 偏程式化腳本、CLI、CI artifact 與工程流程；JMeter 偏 GUI、protocol plugin、既有企業測試流程與非工程團隊協作。

k6 和 Gatling 的主要差異是生態與語言。k6 使用 JavaScript-style 腳本，Gatling 偏 JVM / Scala / Java / Kotlin 生態；團隊語言能力與既有 pipeline 會影響維護成本。

k6 和 Locust 的主要差異是團隊技能與模型表達。Locust 使用 Python，對 Python 團隊與 custom user behavior 很自然；k6 的 threshold、CLI 與雲端 / Grafana 生態讓 release gate 整合更直接。

k6 和 Vegeta 的主要差異是場景複雜度。Vegeta 適合簡單 HTTP load、CLI workflow 與快速 saturation 探測；k6 適合較完整的 multi-step scenario、threshold 與長期 baseline。

## 操作成本

k6 的主要成本是 workload model 維護。腳本本身容易寫，真正的成本在 production endpoint mix、資料分布、tenant / region / user cohort、think time 與 peak shape 的持續校正。

Runner 成本會隨負載規模上升。單機 runner 適合小型 API baseline；跨 region、數十萬 RPS 或長時間 soak test 需要分散式 runner、網路成本、目標服務隔離與觀測儲存。

測試資料治理是高風險成本。Checkout、payment、order、email、notification 與 webhook 路徑都可能產生 side effect，因此 scenario 要明確定義 test tenant、idempotency key、mock boundary、cleanup 與 stop condition。

## Evidence Package

k6 結果應回寫到 evidence package。最小欄位包括 scenario version、target environment、time range、VUs / arrival rate、threshold、p95 / p99、error rate、throughput、target service saturation metric、known gap 與 owner。

| 欄位         | k6 證據來源                             |
| ------------ | --------------------------------------- |
| Source       | k6 summary、JSON output、dashboard link |
| Time range   | test start / end                        |
| Query link   | Grafana / Prometheus / APM 查詢連結     |
| Data quality | scenario coverage、test data freshness  |
| Confidence   | production similarity、runner capacity  |
| Known gap    | 未覆蓋 endpoint、未模擬第三方、資料偏差 |

Evidence package 的核心用途是讓 release gate 能判斷。k6 的 threshold pass 只是其中一個訊號；gate 還要看 target service 的 CPU、connection、DB latency、cache hit rate、queue lag 與 cloud cost。

## 案例回寫

k6 目前在 09 案例庫中主要作為工具類承接點，案例主角仍是負載形狀與驗證節奏。它可回寫到 [9.C15 Tixcraft 售票壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的 pre-event load test 判讀、[9.C1 Prime Day readiness](/backend/09-performance-capacity/cases/aws-prime-day-extreme-scale-2025/) 的 staged validation、[9.C28 FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的多模型壓測需求、[9.C2 GR8 Tech FIFA World Cup readiness](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 的 54000 TPS @ 25ms p95 驗證、以及 [9.C7 Lyft 8x peak](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) 跨 100+ 微服務的獨立 threshold 設計。

這些案例提供的是負載形狀與工程節奏。k6 頁引用案例時，要把 case 轉成 workload model、ramp-up、threshold、runner 規模與 stop condition，並讓工具回到可替換的承載選項 — 例如 GR8 Tech 25ms p95 是 threshold pass / fail 的硬目標、Lyft 的「8x 是特定服務、不是全部 8x」要拆成 per-service scenario。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 跨模組：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 官方：[Grafana k6 documentation](https://grafana.com/docs/k6/latest/)
