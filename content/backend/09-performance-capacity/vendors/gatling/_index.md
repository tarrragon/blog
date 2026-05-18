---
title: "Gatling"
date: 2026-05-15
description: "用 JVM DSL、simulation 與 injection profile 表達複雜 scenario 的效能工程工具"
weight: 3
tags: ["backend", "performance", "capacity", "vendor", "gatling", "load-test"]
---

Gatling 的核心責任是把複雜使用者流程寫成可維護的 JVM simulation。它適合 JVM 生態團隊、強型別 DSL、HTTP / WebSocket / JMS / MQTT 等 scenario，以及需要把 injection profile、assertion、report 與 CI pipeline 綁在一起的壓測流程。

## 服務定位

Gatling 是 *Scala-origin / 現以 Java DSL 為主流* 的 load testing 工具、跑在 JVM、async / non-blocking engine（基於 Akka / Netty）讓單一 injector node 就能驅動高 RPS。它跟 [k6](/backend/09-performance-capacity/vendors/k6/) / [JMeter](/backend/09-performance-capacity/vendors/jmeter/) / [Locust](/backend/09-performance-capacity/vendors/locust/) 的核心差異不在 *能不能壓出負載*、而在 *語言生態 + engine efficiency + scenario 表達力*：

- vs k6 — k6 走 Go runtime + JavaScript scripting、CLI / Grafana 生態友善；Gatling 走 JVM + Java/Scala/Kotlin DSL、適合既有 JVM 工具鏈與強型別 review
- vs JMeter — JMeter 走 GUI / XML test plan、適合非工程角色協作；Gatling 走 code-first、適合 PR / build pipeline / refactor 工作流
- vs Locust — Locust 走 Python coroutine、scripting 自由度高；Gatling 走 DSL + injection profile、scenario 結構化程度更高
- engine efficiency — async / non-blocking model 讓 Gatling 在單機可推到數萬 RPS、JMeter thread-per-user 在同等資源下 throughput 較低

產品線分兩層：*Gatling OSS*（開源 simulation runner + HTML report）與 *Gatling Enterprise*（前身 FrontLine、加上 distributed injector、cluster orchestration、live monitoring、long-term result storage、role-based access）。OSS 適合單機 baseline / CI smoke、Enterprise 適合 cross-region distributed / 大型活動前壓測 / 結果長期治理。

## 最短判讀路徑

判斷 Gatling 在壓測流程裡是否健康、最少看四件事：

- **Scala DSL vs Java DSL 版本**：Gatling 3.7+（2022）正式加 Java DSL、2024 後新專案多走 Java DSL；舊 Scala simulation 仍可跑、但團隊要決定 *維持 Scala 還是漸進改寫 Java*、避免雙語言治理
- **Injection profile 設計**：simulation 是否明確區分 *open model*（`rampUsersPerSec` / `constantUsersPerSec`、模擬真實 arrival）vs *closed model*（`atOnceUsers` / `rampUsers`、模擬 fixed user pool），對應 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 的 traffic shape
- **Assertion gate**：simulation 是否有 `assertions { global.responseTime.percentile3.lt(500) }` 這類 hard gate、CI 跑完直接 fail build；沒 assertion 的 simulation 只是壓測、不是 release gate
- **Enterprise vs OSS 邊界**：是否清楚知道哪些能力只 Enterprise 有（distributed injector / multi-region / long-term result storage / live dashboard）、避免用 OSS 拼湊 Enterprise 級需求

## 定位

Gatling 適合 code-first 且 JVM 能力強的團隊。當 workload model 需要多步驟 flow、資料 feeder、條件分支、session state 與明確 injection profile，Gatling 能用 simulation 把這些行為寫成工程 artifact。

這個定位讓 Gatling 接到 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 與 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)。它的價值在於把 traffic shape 寫進 injection profile，讓 ramp-up、constant users、stress peak 與 soak test 都能被版本化。

## 適用場景

JVM 團隊適合用 Gatling 承接壓測。Java、Scala 或 Kotlin 團隊能把 simulation 當成一般程式碼 review，並用既有 build、dependency、CI 與 artifact 流程維護。

複雜 scenario 適合用 Gatling 表達。登入、搜尋、加入購物車、checkout、payment mock、order query 這類 multi-step flow 可以用 session 與 feeder 管理資料。

高品質 report 適合 release review。Gatling 的 report 能幫 reviewer 看到 response time distribution、request group、error 與 injection profile，適合在 release gate 中保留可讀證據。

## 選型判準

| 判準              | Gatling 的價值            | 需要補的能力                        |
| ----------------- | ------------------------- | ----------------------------------- |
| JVM DSL           | simulation 可 code review | Scala / Java / Kotlin 維護能力      |
| Injection profile | 負載階段可精準表達        | production traffic shape 校正       |
| Session / feeder  | 多步驟資料與狀態容易管理  | 測試資料治理與敏感資料遮罩          |
| Report            | release review 可讀性高   | 長期趨勢儲存與 cross-run comparison |

JVM DSL 價值來自可維護性。壓測 scenario 如果需要被長期 review、重構、抽 helper 或接 build pipeline，Gatling 的 code-first workflow 會比 GUI test plan 更適合工程團隊。

Injection profile 價值來自負載形狀精準。團隊可以把 steady load、spike、ramp、open model 與 closed model 放到 simulation 中，讓 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的 knee point 判讀更可重現。

## 跟其他工具的取捨

Gatling 和 k6 的主要差異是語言與生態。Gatling 適合 JVM 團隊與強型別 simulation；k6 適合 JavaScript-style scripting、CLI workflow 與 Grafana 生態。

Gatling 和 JMeter 的主要差異是維護模式。Gatling 偏 code review、build pipeline 與 simulation abstraction；JMeter 偏 GUI、plugin 與跨角色測試資產。

Gatling 和 Locust 的主要差異是自訂語言。Locust 適合 Python 團隊與任意 Python client；Gatling 適合 JVM 團隊與 report / injection profile 的結構化壓測。

Gatling 和 Vegeta 的主要差異是 scenario 深度。Vegeta 適合快速 HTTP pressure test；Gatling 適合需要 session、feeder、assertion 與多 request group 的長期測試。

## 操作成本

Gatling 的主要成本是 JVM 團隊能力。非 JVM 團隊要承擔語言、build tool、dependency 與 simulation pattern 的學習成本；這個成本只有在 scenario 複雜度夠高時才划算。

測試資料成本來自 feeder 與 session。多步驟 flow 需要 account、cart、order、token、region 與 tenant 資料，資料過期或分布偏差會讓壓測結果失真。

Enterprise / distributed 成本要提前評估。單機 Gatling 適合中小型 baseline；跨 region、大型活動前驗證或長時間 soak test 需要 runner topology、結果集中與雲端成本治理。

## Evidence Package

Gatling 結果應回寫到 evidence package。最小欄位包括 simulation version、injection profile、feeder source、target environment、assertion、response time distribution、error rate、throughput、target service saturation metric、known gap 與 owner。

| 欄位         | Gatling 證據來源                             |
| ------------ | -------------------------------------------- |
| Source       | simulation code、HTML report、dashboard link |
| Time range   | test start / end                             |
| Query link   | APM / metrics / logs 查詢連結                |
| Data quality | feeder freshness、scenario coverage          |
| Confidence   | production similarity、runner capacity       |
| Known gap    | 未覆蓋 flow、資料偏差、下游 mock 限制        |

Evidence package 的核心用途是讓 simulation 可回放。Reviewer 要能從 report 回到 injection profile、scenario code、feeder 與目標環境，才有辦法判斷一次壓測是容量訊號還是測試設計偏差。

## 核心取捨表

| 取捨維度        | Gatling                                                  | k6                                   | JMeter                                      | Locust                               |
| --------------- | -------------------------------------------------------- | ------------------------------------ | ------------------------------------------- | ------------------------------------ |
| 語言 / DSL      | Java / Kotlin / Scala DSL（JVM）                         | JavaScript（Go runtime）             | GUI / XML test plan（JVM）                  | Python（coroutine / gevent）         |
| Engine model    | Async / non-blocking（Akka + Netty）                     | Async（Go goroutine）                | Thread-per-user（同步）                     | Async coroutine                      |
| 單機 RPS 上限   | 高（數萬 RPS）                                           | 高（數萬 RPS）                       | 中（thread overhead）                       | 中（GIL + coroutine）                |
| Scenario 表達力 | 強（session / feeder / 條件分支內建）                    | 中（JS function 自寫）               | 中（GUI 拖拉 + listener）                   | 中（Python class + task）            |
| Report quality  | 高（HTML report 內建、distribution / group 詳細）        | 中（CLI 摘要 + Grafana 串接）        | 中（GUI listener、不適合 headless）         | 中（web UI 即時、無 historical）     |
| CI integration  | 強（Maven / Gradle / sbt + assertion gate）              | 強（CLI + JSON output）              | 中（CLI mode 可、但 GUI-first）             | 強（CLI + Python ecosystem）         |
| Distributed     | OSS 自建 / Enterprise 內建                               | k6 Cloud / OSS 自建                  | 自建（master-slave）                        | 自建（master-worker）                |
| 商業版本        | Gatling Enterprise（前 FrontLine）                       | Grafana Cloud k6                     | 無（純 OSS）                                | 無（純 OSS）                         |
| 適合場景        | JVM 團隊、複雜 scenario、release gate、高 RPS efficiency | 全棧團隊、CLI workflow、Grafana 生態 | 跨角色團隊、legacy test plan、protocol 多樣 | Python 團隊、自訂 client、輕量 setup |

選 Gatling 的核心訴求：*JVM 團隊 + 複雜 scenario（session / feeder / 多 group）+ 高 RPS 單機效率 + HTML report 作為 release gate 證據*。Java DSL 在 2024 後降低了 Scala 學習門檻、讓 Java/Kotlin 後端團隊不必再為了壓測導入 Scala。

## 進階主題

**Gatling Enterprise（前 FrontLine）**：商業版加 *distributed injector cluster*（跨 region / 跨 cloud 推大型負載）、*live monitoring dashboard*（real-time RPS / response time 趨勢、不用等 simulation 結束看 HTML）、*long-term result storage*（cross-run comparison、retention policy）、*role-based access*（QA / dev / SRE 不同權限）。對只跑單機 baseline 的團隊 OSS 已夠；要跑黑五 / 春晚級活動前壓測或多 region 同時施壓、需要 Enterprise 或自建 distributed topology。

**Java DSL 取代 Scala 成主流（2022-2024）**：Gatling 3.7（2022）正式釋出 Java DSL、3.9+ 文件 Java / Kotlin / Scala 三語並列、2024 後新教學多以 Java 為主。對 Java 後端團隊降低 onboarding 成本、但要注意 *Gatling 2.x → 3.x* 的 Scala syntax 不向後相容（`scenario` builder、`http` config、`feed` 用法都改寫）— 舊 simulation 升級時等於改寫一遍。

**Distributed execution（OSS）**：OSS 沒有內建 cluster orchestration、要靠 *multiple injector + result aggregation*：每台 injector 跑同一份 simulation（按 user count 切割）、結束後把 `simulation.log` 蒐集到一處用 `gatling.sh` 重跑 report stage。常見補位是用 Kubernetes Job + 共享 PVC、或直接走 Gatling Enterprise。

**HTML report 與 release gate**：simulation 跑完自動產 HTML report、含 *response time percentile distribution*（mean / p50 / p95 / p99 / max）、*per-request-group breakdown*、*active users over time*、*error log*。release gate 的標準做法是：CI job 跑 simulation → assertion gate fail 直接 break build → HTML report 存成 build artifact 供 reviewer 翻查、配合 [Evidence Package](/backend/04-observability/observability-evidence-package/) 治理。

**CI integration 模式**：Jenkins / GitLab CI / GitHub Actions 都靠 `mvn gatling:test` / `gradle gatlingRun` / `sbt gatling:test` 入口、CI 設定 *baseline simulation*（每 PR 跑、catch regression）+ *release simulation*（release branch / nightly 跑、長時間 soak）。staging environment 跑壓測時要隔離噪音來源（其他 QA 流量 / cron job）、否則 RPS 數字會被污染。

## 排錯與失敗快速判讀

- **Scala learning curve 拖累進度**：團隊沒人會 Scala、被 implicit / case class / pattern match 卡住 — 改用 Java DSL（3.7+）或 Kotlin DSL、保留 Gatling 表達力但去除 Scala 學習成本
- **Gatling 2.x → 3.x 升級 simulation 全紅**：`bootstrap` import path / `scenario` builder API / `feed` 語法都變了 — 走 *新專案直接 3.x、舊專案維持 2.x* 雙軌、或安排專門 sprint 改寫、避免邊跑邊踩雷
- **JVM heap OOM / GC pause 拖慢 RPS**：高 RPS 下 default heap 不夠、Young Gen GC 頻繁 — 調 `-Xmx4G -Xms4G`、用 G1GC / ZGC、監控 injector 的 GC log 跟 CPU、不是只看 target service
- **Injection profile 設計錯導致誤判 saturation**：用 `atOnceUsers(1000)` 壓 closed model 但實際 traffic 是 open arrival、結果 knee point 找錯 — 看 production traffic shape、open model 用 `constantUsersPerSec` / `rampUsersPerSec`、closed model 才用 `atOnceUsers`
- **Single injector node 撞 client-side bottleneck**：injector CPU / network / file descriptor / source port 用滿、看起來 target saturate 其實是 injector saturate — 監控 injector resource、scale out 成 distributed 或走 Enterprise
- **Feeder data 過期 / 分布偏差**：用同一份 `users.csv` 反覆壓、cache hit rate 失真、production 看不到的 cache miss 路徑沒被測 — feeder 走 `random` / `shuffle`、定期 regenerate、覆蓋 long-tail key
- **HTML report 看起來綠但 production 出事**：assertion gate 只設 average response time、p99 / error rate 沒設、release 後尖峰時段才爆 — assertion 要明確設 p95 / p99 + error rate threshold、不只看 mean

## 案例回寫

Gatling 適合回寫多步驟與多負載模型案例。它可接 [9.C28 FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的直播與投注雙模型、[9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 token / admission flow、[9.C17 BookMyShow ticketing](/backend/09-performance-capacity/cases/bookmyshow-indian-ticketing-platform/) 的售票流程壓力、[9.C4 DraftKings Aurora 金融帳本](/backend/09-performance-capacity/cases/draftkings-aurora-financial-ledger/) 的「比賽期讀爆量 + payout 時寫爆量」雙峰錯位，以及 [9.C2 GR8 Tech](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 的「投注 / 結算 / 賠率更新」三類請求 group 的 injection profile。

這些案例的重點是 scenario 與 injection profile。Gatling 頁引用案例時，要把業務流程拆成 request group、session state、feeder、assertion 與 stop condition — 例如 DraftKings 雙峰錯位要寫成兩個 scenario 平行注入、各自有獨立 assertion budget。

## 下一步路由

- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[JMeter](/backend/09-performance-capacity/vendors/jmeter/)、[Locust](/backend/09-performance-capacity/vendors/locust/)
- 官方：[Gatling documentation](https://docs.gatling.io/)
