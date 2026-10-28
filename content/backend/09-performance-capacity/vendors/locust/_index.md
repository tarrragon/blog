---
title: "Locust 在效能容量的工具總覽：Python 的 user behavior、custom client、worker 擴展與施壓端觀測"
date: 2026-05-15
description: "要用 Locust 寫自訂 user behavior 或 custom client 做容量探測、判斷 worker 要開幾台、分辨飽和的是施壓端還是受測服務，或在 Locust 與 k6、Gatling、JMeter 之間選容量工程的工具時讀"
weight: 4
tags: ["backend", "performance", "capacity", "vendor", "locust", "load-test"]
---

Locust 的核心責任是用 Python 表達高度自訂的使用者行為與 protocol client。它適合 Python 團隊、需要自訂 client、需要 distributed worker、或 scenario 邏輯比工具內建 sampler 更複雜的壓測流程。

## 服務定位

Locust 適合把壓測寫成一般 Python 程式。當 workload model 需要呼叫 internal SDK、特殊 protocol、複雜資料準備、狀態機、隨機行為或自訂 client、Locust 可以直接使用 Python 生態來表達。底層架構是 *master + worker* 分散式 swarm、worker 之間用 Gevent green-thread（非 OS thread）模擬大量並發 user、master 負責 spawn rate、aggregation 跟 Web UI。

這個定位讓 Locust 接到 [9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/) 與 [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)。它能把特殊 client 與下游 dependency 放進同一個 user behavior、但也要求團隊處理 runner、資料與可重現性。

跟 [k6](/backend/09-performance-capacity/vendors/k6/)（JS / Go runtime）比、Locust 用 Python 換到 *自訂能力與生態相容*、但代價是單 worker capacity 低、CPU bound 容易先打到自己。跟 [JMeter](/backend/09-performance-capacity/vendors/jmeter/)（GUI / XML）比、Locust 偏 *code-first 工程團隊*、scenario 直接走 Git review、不靠 GUI plugin 拼裝。跟 [Gatling](/backend/09-performance-capacity/vendors/gatling/)（Scala DSL）比、Locust 換到 *Python team 友善 + 既有 domain library 重用*、但失去 JVM injection profile 的精細度與報表內建。

關鍵張力：*Python 表達力* ↔ *runner 效能上限*。Python team 想 reuse domain library、staging fixture、API client 寫壓測腳本時 Locust 是首選；代價是一個 worker 程序只用得到一顆 CPU，worker 的 CPU 先到頂時要加 worker 程序或機器，調 Locust 本身的參數換不到更多施壓量。一個 worker 送得出多少請求取決於 task 的內容、client 的種類（`HttpUser` 或 `FastHttpUser`）與機器，要在自己的施壓機上量（[Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/)）。

## 適用場景

Python 團隊適合用 Locust 長期維護壓測。既有 domain library、API client、fixture、資料產生器與驗證 helper 都可以被壓測腳本重用。

自訂 protocol 適合用 Locust。HTTP 之外、如果服務需要 gRPC、WebSocket、binary protocol、message broker client 或自家 SDK、Locust 可以直接接 Python library。

Distributed load 適合用 Locust worker 擴展。當單機 Python runner 遇到 CPU 或 connection bottleneck、可以用 master / worker 拆開負載產生能力。

## 本章目標

讀完本頁、讀者能判斷：

1. Locust 在壓測 stack 中承擔哪一段（user behavior modeling / load generation / distributed swarm）、哪些要外接（[Prometheus / Grafana](/backend/04-observability/) 觀測 worker 自身、APM 看目標 saturation）
2. User class / task weight / on_start lifecycle 的 ownership 設計（誰寫 locustfile、誰 review、誰調 spawn rate）
3. Distributed master-worker 部署的容量規劃（在自己的施壓機上量出單 worker 的上限、由目標施壓量推 worker 數量）
4. 何時用 Locust、何時走 k6 / JMeter / Gatling 的取捨

## 最短判讀路徑

判斷 Locust 壓測是否健康、最少看四件事：

- **User class 設計**：每個 `HttpUser` / `User` subclass 是不是一個明確的 *persona*（mobile user / API client / admin user）、`wait_time` 是否反映真實使用者間隔（用 `between(1, 5)` 模擬 think time，而不是設 0 拼最大 RPS）、user state 是否在 instance 內封閉
- **Task 比例**：`@task(weight)` 數字是否對應 production traffic mix（80% read / 15% write / 5% admin、不是每個 endpoint 等比例）、weight 是否走版控 review
- **on_start lifecycle**：login / token fetch / session bootstrap 是否寫在 `on_start`（每個 user 一次）、不是寫在 `@task` 裡（每個 request 都重做）— 寫錯位置會讓 auth endpoint 變成主要 traffic
- **Distributed master-worker**：worker 數量是否夠（worker 的 CPU 先到頂時，延遲上升的是施壓端，不是目標服務）、master 是否獨立機器（master 也跑 user 時 aggregation 跟 Web UI 會卡）、`--expect-workers` 是否設、worker sync drift 是否觀察

四件事任一缺失、就是壓測證據可信度的待補項目。

## 日常操作與決策形狀

**locustfile 結構**：locustfile.py 是 Python module、定義 `User` / `HttpUser` subclass、每個 user 有 `wait_time`、若干 `@task(weight)` method、`on_start` / `on_stop` lifecycle hook。執行用 `locust -f locustfile.py --host=https://target` 起 Web UI、或 `locust --headless -u 1000 -r 100 -t 10m` 在 CI 跑無 UI 模式。locustfile 應該走 Git review、不是 GUI 改完就跑。

**Task weight / wait_time 設計**：weight 是 *相對權重*、不是百分比 —`@task(8)` + `@task(2)` 等於 80% / 20%。`wait_time = between(1, 5)` 在每個 task 之間等 1-5 秒、模擬 think time；若要拚最大 RPS 用 `constant(0)`，這時模型就成了 *throughput probe*，而不是 user behavior 模型。

**on_start vs @task 的邊界**：`on_start(self)` 每個 user instance 啟動時跑一次、適合做 login、token fetch、cache warm、fixture lookup；`@task` 是 user 行為主迴圈、每次選一個 task 跑。把 login 寫在 `@task` 是常見錯誤、會讓 IdP 變成主壓力來源、不是目標 API。

**Gevent-based concurrency**：Locust 用 [gevent](https://www.gevent.org/) 的 green-thread 模擬大量 concurrent user、不是 OS thread。意義是一個 worker 程序裡的 user 共用一顆 CPU 與同一個 event loop，CPU bound 工作（JSON serialization、加密、本地計算）會 *blocking* 整個 worker 的 event loop。`import locust` 時 Locust 自己呼叫 `gevent.monkey.patch_all()`，標準庫的 socket、time、ssl 都會被 patch（設了環境變數 `LOCUST_SKIP_MONKEY_PATCH` 時不做）；卡住整個 worker 的是 patch 管不到的 I/O，也就是 C extension 自己做的網路呼叫（例如原生的資料庫 driver）。

**Distributed master-worker**：單機到極限時開 distributed — `locust --master` 起 master、`locust --worker --master-host=master.example.com` 起 worker。Master 負責 Web UI、spawn rate 控制、result aggregation、stat 收集；worker 負責跑 user。Master 不該跑 user（會跟 aggregation 搶 CPU、stat 失真）。worker 數量計算：先用一個 worker 逐級增加 user，記下 worker 的 CPU 開始到頂、或延遲在受測服務的指標沒有變化時就上升的那一級，那一級之前的 user 數是一個 worker 的上限；目標 user 數除以這個上限是最少的 worker 數，要留多少餘裕看量測時 CPU 離到頂還有多遠，以及正式跑時 task 的組合跟量測時差多少。

**Custom load shape**：除了固定 `-u 1000`、Locust 支援 `LoadTestShape` subclass 寫 *時間軸負載曲線* — spike test（瞬間 0 → 5000 user）、ramp test（線性爬升）、wave test（週期性高低交替）、step test（階梯式增加）。`tick()` method 每秒回傳 `(user_count, spawn_rate)`。用 custom shape 才能模擬 [9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 那種 ticket drop 瞬間衝擊。

**Prometheus exporter / 觀測**：Locust 內建 stat 只是 in-memory 的 p50 / p95 / p99 / RPS、結束就消失。長期觀測接 [locust-prometheus-exporter](https://github.com/ContainerSolutions/locust_exporter)（或 `--csv result.csv` 自己抓）、把 metric 推到 [Prometheus](/backend/04-observability/) + Grafana。**worker 自身的 CPU / memory / network** 一定要同時觀測、不然分不出是目標 saturation 還是 worker 已死。

**Locust Cloud（managed SaaS）**：Locust 的官方託管服務 [Locust Cloud](https://docs.locust.cloud/)、託管 master + worker + result storage、付費換 ops 成本。自管 master-worker 對 CI / staging 是合理的；production 等級的 scale test（10k+ concurrent user）跑一次要拉幾十台 worker、用 Cloud 省 infra ops 是合理 trade-off。

## 核心取捨表

| 取捨維度           | Locust                               | k6                                    | JMeter                               | Gatling                            |
| ------------------ | ------------------------------------ | ------------------------------------- | ------------------------------------ | ---------------------------------- |
| 腳本語言           | Python（generic）                    | JavaScript (k6 runtime)               | XML / GUI / Groovy                   | Scala DSL（也支援 Java / Kotlin）  |
| Runtime            | Python + Gevent green-thread         | Go-based、單 binary、低 overhead      | JVM、heavy                           | JVM、async actor model             |
| 單 worker capacity | 中低（Python overhead、千級 user）   | 高（Go runtime、萬級 VU 單機）        | 中（JVM tuning 後可用）              | 高（Akka actor、效能好）           |
| Distributed mode   | 內建 master-worker                   | 內建 k6 Cloud / k6 Operator           | 內建 client-server（remote testing） | Gatling Enterprise（前 FrontLine） |
| User behavior 彈性 | 高 — 一般 Python、任意 library       | 中 — JS 但 k6 runtime 受限            | 中 — GUI 拼裝 + plugin               | 中高 — Scala DSL 表達 simulation   |
| Custom protocol    | 強 — 接任何 Python library           | 強 — 有 gRPC / WS / Kafka extension   | 強但繁瑣 — plugin 生態廣             | 中 — 主要 HTTP / WS                |
| CI / headless      | `--headless` 支援                    | CI-first design                       | non-GUI mode 支援                    | 內建支援                           |
| Report / UI        | Web UI 即時 + CSV 匯出               | k6 Cloud / Grafana / 簡 stdout        | GUI listener / HTML report           | HTML report 內建、視覺豐富         |
| 學習曲線           | 緩（Python team）/ 陡（非 Python）   | 中 — JS-style scripting               | 緩（GUI）/ 陡（深度 tuning）         | 陡 — Scala 語法                    |
| 適合場景           | Python team + 自訂 behavior / client | DevOps + CI / 標準 HTTP / 高 RPS 單機 | 非工程角色協作 / legacy enterprise   | JVM team + 精細 injection profile  |
| 退場成本           | 低 — Python 腳本可移植               | 中 — k6 runtime 綁定                  | 中 — XML jmx 不易他移                | 中 — Scala DSL 綁定                |

選 Locust 的核心訴求：*Python team + custom user behavior + 既有 domain library 重用*、且能投入 worker scale-out 預算（單 worker capacity 低、要靠分散式補）+ scenario 走 Git review 不靠 GUI。標準 HTTP 高 RPS 單機壓測直接走 k6 更快、非工程角色協作壓測走 JMeter、JVM team 精細模擬走 Gatling。

## 進階主題

**Distributed Locust 的 master-worker swarm**：production scale test 通常需要 10-100 個 worker。實作要點：worker 之間 *不要* 共享 state、shared resource 由 master 統一發（用 [zeromq](https://zeromq.org/) message bus）；worker 加入 / 離開時 user 會 redistribute、避免 user index 當 unique key；worker 跨 region 跑時 *latency 來自 worker → target 不只是 target 內部*、要在 worker 本身的 region 對齊。

**Custom load shape（spike / wave / step）**：`LoadTestShape.tick(self)` return `(user_count, spawn_rate)` tuple 每秒被叫一次。Spike test：前 60 秒 0 user、第 61 秒瞬間衝 5000、模擬 [9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 admission storm。Wave test：sine wave 在 1000-3000 user 之間振盪、測 autoscaling 反應速度。Step test：每 5 分鐘加 1000 user、觀察哪一階開始降級。k6 用 `stages` 與 `ramping-vus`、`ramping-arrival-rate` executor 也寫得出這幾種曲線；`LoadTestShape` 的差別在 `tick()` 是一般 Python 程式，可以依執行中的狀態（目前的使用者數、統計值）決定下一秒的目標。

**跟 Prometheus exporter 整合**：locust-prometheus-exporter 把 Locust stat 推到 Prometheus / Grafana、做長期 baseline、跨 test 比較、p99 退化偵測。實務上要在 dashboard 同時放 *Locust 內部 stat* + *worker host metric* + *目標服務 APM*、三層 stack 起來才能判讀是 runner 還是目標 saturation。

**Locust Cloud（managed SaaS）**：官方的託管服務、託管 master + worker + result + dashboard。trade-off：自管適合 CI / staging / 內網壓測（target 跑在內網時 Cloud 連不到）；Cloud 適合大規模一次性 scale test（拉 50 worker 跑 2 小時、跑完即停、不想自己 infra ops）。

## 操作成本

Locust 的主要成本是 runner overhead 與分散式治理。Python runner 的效能上限要用 worker scale-out 解決；壓測結論要同時檢查目標服務 saturation 與 worker 本身 CPU、connection、network 是否已成瓶頸。

腳本工程成本來自自由度。Python 可以很快寫出複雜行為、也容易把測試資料、randomness、side effect、sleep 與 exception handling 寫散；團隊要維持 scenario structure、fixture、logging 與 artifact 標準。

自訂 client 成本來自校正。使用 SDK 或 custom protocol client 時、要確認 client retry、timeout、connection pool 與 serialization 行為是否接近 production、避免 runner 模擬出不存在的壓力形狀。

## 排錯與失敗快速判讀

- **Worker CPU 100% 但目標服務閒**：Python runner 先死、不是 target saturation — 加 worker 數量、或檢查 task 裡有沒有 CPU bound 的本地計算（大 JSON parse、加密、本地 fixture 生成）擠掉 event loop
- **Gevent monkey-patch gotcha**：`psycopg2` 這類 C extension 或自家 SDK 的原生程式碼自己做網路呼叫，gevent 的 patch 管不到，呼叫期間整個 worker 卡住 — `import locust` 已經做了 `patch_all()`，問題不在 patch 的時機；改用 socket 由 Python 層操作、patch 管得到的 client（例如 MySQL 的 `PyMySQL`），或把那段呼叫放到 gevent 的 threadpool
- **RPS 達不到目標 / 看起來像 target 慢**：實際是 worker connection pool 耗盡、或 worker 本身網卡飽和 — 觀測 worker 本身的 TCP socket 數、netstat ESTABLISHED、network throughput；不要直接 blame target
- **Distributed sync drift**：worker 之間 user count 不平均、aggregation 顯示 RPS 抖動 — `--expect-workers=N` 確認 master 等所有 worker join 才開測；worker 跨 region 時 message bus latency 也會影響 sync
- **on_start 在 @task 裡跑**：壓測啟動瞬間所有 user 同時登入、auth endpoint 的請求量突增、看到 IdP latency 飆高以為是 target — 把 login / token fetch 移到 `on_start`、每個 user 只做一次
- **wait_time = 0 拼最大 RPS 結果結論奇怪**：這已經不是 user behavior 是 throughput probe、p99 跟 production 對不上 — 改成 `between(1, 5)` 模擬 think time 或寫 custom shape
- **Web UI 卡 / master CPU 100%**：master 同時在跑 user + aggregation — `locust --master` 跟 worker 拆機器、master 不跑 user

## 何時改走其他服務

| 需求形狀                           | 改走                                                                                                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 標準 HTTP / 高 RPS 單機 / CI-first | [k6](/backend/09-performance-capacity/vendors/k6/)                                                                                                          |
| 非工程角色協作 / GUI 拼裝          | [JMeter](/backend/09-performance-capacity/vendors/jmeter/)                                                                                                  |
| JVM team / 精細 injection profile  | [Gatling](/backend/09-performance-capacity/vendors/gatling/)                                                                                                |
| 極簡 HTTP probe / 命令列 one-shot  | [Vegeta](/backend/09-performance-capacity/vendors/vegeta/)                                                                                                  |
| Production traffic replay / shadow | [GoReplay](/backend/09-performance-capacity/vendors/goreplay/) / [Service Mesh Mirroring](/backend/09-performance-capacity/vendors/service-mesh-mirroring/) |
| 壓測結果回寫到效能工程 lifecycle   | [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)、[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)      |

## 不在本頁內的主題

- locustfile 完整語法 reference、`User` 跟 `HttpUser` 的 attribute 細節
- Locust Cloud 計費跟 quota 細節（看官方 docs）
- gevent 跟 asyncio 的取捨（Locust 選了 gevent、不在本頁討論替代）
- 壓測證據怎麼歸檔（看 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 通則）

## Evidence Package

Locust 結果應回寫到 evidence package。最小欄位包括 locustfile version、user class、task weight、spawn rate、worker count、client library version、target environment、p95 / p99、error rate、throughput、target saturation metric、known gap 與 owner。

| 欄位         | Locust 證據來源                                 |
| ------------ | ----------------------------------------------- |
| Source       | locustfile、CSV / JSON result、dashboard link   |
| Time range   | test start / end                                |
| Query link   | APM / metrics / logs 查詢連結                   |
| Data quality | user behavior coverage、fixture freshness       |
| Confidence   | worker capacity、client realism                 |
| Known gap    | worker bottleneck、custom client 偏差、資料偏差 |

Evidence package 的核心用途是區分目標瓶頸與 runner 瓶頸。Locust 分散式測試要同時保存 worker 數量、worker 資源、spawn rate 與 client behavior、讓 reviewer 知道壓力是否真的打到目標服務。

## 案例回寫

Locust 適合回寫需要高度自訂 user behavior 的案例。它可接 [9.C28 FanDuel 雙峰 workload](/backend/09-performance-capacity/cases/fanduel-dual-peak-betting-streaming/) 的投注行為模型、[9.C16 SeatGeek waiting room](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/) 的 admission / token flow、[9.C26 PayPay mobile payment messaging](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) 的外部推送與下游 quota 模擬、[9.C8 Niantic Pokémon GO 50x surge](/backend/09-performance-capacity/cases/niantic-pokemon-go-fifty-x-surge-gcp/) 的玩家移動 + 互動混合行為、以及 [9.C18 Zoom COVID 30x surge](/backend/09-performance-capacity/cases/zoom-covid-surge-dynamodb/) 的會議建立 / 加入 / 離開行為混合。

這些案例的重點是 domain behavior。Locust 頁引用案例時、要把 case 轉成 user class、task weight、custom client、downstream mock 與 worker capacity、再把總 RPS 放回這些行為條件下判讀 — 例如 Pokémon GO 玩家行為跟一般 web user 完全不同（持續 GPS 上報 + 偶發互動）、不能直接用 HTTP RPS 衡量；SeatGeek waiting room 要寫 `LoadTestShape` 模擬 ticket drop 瞬間衝擊、不是穩態 RPS。

## 下一步路由

- 實作：[Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/)（locustfile、headless 執行與 CSV、exit code、quitting 事件裡的判定、一個 master 加兩個 worker 的啟動與 heartbeat 失聯的判讀）
- 上游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)
- 上游：[9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 上游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 平行：[k6](/backend/09-performance-capacity/vendors/k6/)、[JMeter](/backend/09-performance-capacity/vendors/jmeter/)、[Gatling](/backend/09-performance-capacity/vendors/gatling/)、[Vegeta](/backend/09-performance-capacity/vendors/vegeta/)
- 跨類：[GoReplay](/backend/09-performance-capacity/vendors/goreplay/)（production traffic replay 替代 synthetic load）
- 跨模組：[4 Observability](/backend/04-observability/)（worker 自身 + 目標 APM 雙觀測）
- 官方：[Locust documentation](https://docs.locust.io/)
