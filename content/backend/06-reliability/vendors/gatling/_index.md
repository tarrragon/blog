---
title: "Gatling"
date: 2026-05-01
description: "JVM-based load test、Scala / Java / Kotlin DSL、強型別 scenario、HAR-driven recording"
weight: 4
tags: ["backend", "reliability", "vendor"]
---

Gatling 是 JVM 生態的 load test 工具、承擔三個責任：code-first 強型別 scenario DSL（Scala / Java / Kotlin、編譯期就抓 script bug）、async / non-blocking 引擎（單機高 VU 不靠 thread-per-VU）、Gatling Enterprise 分散式負載與企業 dashboard。設計取捨偏向「強型別 + 高單機 throughput + JVM 既有資產」、跟 k6（JS DX）跟 JMeter（GUI + plugins）的取捨在 dev workflow 跟團隊既有技能。

## 本章目標

讀完本章後、你應該能：

1. 用 Scala / Java / Kotlin DSL 寫 simulation（scenario + injection profile）
2. 設計 assertion + threshold 接 CI
3. 用 HAR-driven recording 從瀏覽器抓真實 user flow 起 script
4. 評估 Gatling Enterprise 分散式 vs OSS 單機高 VU 的取捨
5. 評估 Gatling vs k6 / JMeter / Locust 的選用條件

## 最短路徑：5 分鐘把 Gatling 跑起來

```bash
# 1. 安裝
# TODO: brew install gatling / 下載 bundle / Maven / sbt plugin

# 2. 寫 simulation
# TODO: class MySim extends Simulation {
#         val httpProtocol = http.baseUrl("...")
#         val scn = scenario("...").exec(http("get").get("/"))
#         setUp(scn.inject(rampUsersPerSec(1).to(50).during(60))).protocols(httpProtocol)
#       }

# 3. 跑
# TODO: gatling.sh -s MySim / mvn gatling:test / sbt Gatling/test
```

## 日常操作與決策形狀

### Simulation 結構

子議題：

- `Simulation` class（一個檔一個 simulation、整個 test 的根）
- `scenario(...).exec(...)`（一條 user journey 的步驟序列）
- `httpProtocol`（baseUrl / header / acceptedContent / proxy 共用配置）
- `feeder`（CSV / JSON / JDBC 餵 data、配合 `randomFeeder` / `circular`）

### Injection profile（VU 注入節奏）

子議題：

- `atOnceUsers(n)`、`rampUsers(n).during(t)`、`constantUsersPerSec(rate).during(t)`、`rampUsersPerSec(a).to(b).during(t)`、`heavisideUsers(n).during(t)`
- 跟 k6 stages 對照：Gatling 用 injection step composition、k6 用 stages array — 概念近、語法不同
- Closed model（固定 VU）vs Open model（固定 rate）— Gatling 兩者都支援、production 流量多半 open model 更貼近

### Assertion + threshold + CI

子議題：

- `setUp(...).assertions(global.responseTime.percentile3.lt(500), global.successfulRequests.percent.gt(95))`
- Assertion 失敗時 process exit code 非 0、直接接 CI pass/fail gate
- 對應 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)

## 進階主題（按需閱讀）

### HAR-driven recording

子議題：

- Chrome DevTools 匯出 HAR、`gatling-recorder` 從 HAR 產 simulation skeleton
- 適合：複雜 user flow（multi-step checkout / form / login redirect）懶得手寫 script
- 邊界：recording 出來是 baseline、需手動補 dynamic correlation（CSRF token / session id / form state）

### Gatling Enterprise（前 FrontLine）

子議題：

- 分散式 load（多 injector node 模擬 100k+ VU）、跨 region traffic source
- Web UI 跑 test、看 dashboard、開 trend analysis
- 接 Git repo 自動 build simulation、跟 CI / Jenkins / GitLab 整合
- 對應 [Kubernetes vendor 頁](/backend/05-deployment-platform/vendors/kubernetes/) 的 on-K8s 部署

### Async engine 跟單機高 VU

子議題：

- 引擎基於 Akka / Netty、non-blocking IO、單 thread 可驅動上千 VU
- 對比 JMeter thread-per-VU 模型、Gatling 單機 VU 上限可高 10x 起跳
- 邊界：target service 才是瓶頸時、單機更高 VU 也壓不出更多訊號、要走分散式

### JVM tuning

子議題：

- Heap size（`-Xms / -Xmx`）跟 GC 策略（G1 / ZGC）影響高 VU 穩定性
- Connection pool / file descriptor ulimit 是常見卡關點
- Container 跑 Gatling 要注意 CPU / memory request 給足

### 從 JMeter 遷移

子議題：

- JMeter `.jmx` 沒官方 converter、要人工 port
- 適合切點：新 simulation 寫 Gatling、舊 `.jmx` 維護收斂後再評估
- 對應 [JMeter](/backend/06-reliability/vendors/jmeter/) 「既有 .jmx 資產治理」段

## 排錯快速判讀

### 單機 VU 上不去

操作原則：JVM heap / ulimit / connection pool 三層先排、再看是不是 target service 已是瓶頸（latency 漲、VU 卻沒滿）。

### Response time p99 不穩

操作原則：GC pause（看 GC log）/ network jitter / target service warmup 沒做完。Steady-state 量測前要先 ramp-up + soak 5-10 分鐘。

### Assertion 偶發 fail

操作原則：threshold 設在 noise level 附近、把 baseline 重跑 3 次抓 p95 區間、再設 threshold 留 buffer。

### Recording 出來的 script 跑不通

操作原則：HAR 沒抓到 dynamic value（CSRF / session）、要手動加 `check(regex(...).saveAs(...))` 把 response 抓出來餵後續 request。

## 何時改走其他服務

| 需求形狀                    | 改走                                                         |
| --------------------------- | ------------------------------------------------------------ |
| 非 JVM 團隊 / JS DX         | [k6](/backend/06-reliability/vendors/k6/)                    |
| Python + 動態 user behavior | [Locust](/backend/06-reliability/vendors/locust/)            |
| GUI 設計 / 既有資產         | [JMeter](/backend/06-reliability/vendors/jmeter/)            |
| Browser flow load           | k6 browser / Playwright + 自製 load harness                  |
| Cloud managed               | Gatling Enterprise / BlazeMeter / k6 Cloud                   |
| Capacity planning（非 CI）  | [09 performance capacity](/backend/09-performance-capacity/) |

## 不在本頁內的主題

- Scala / Kotlin 語言基礎
- Gatling DSL 完整 API reference
- Gatling Enterprise pricing 跟 deployment model 細節

## 案例回寫

| 案例方向                                                                                                           | 對應主題                                            |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| [LinkedIn：Capacity 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/) | JVM 服務的 capacity headroom 與 automated load test |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)             | 峰值準備期 scenario-driven load test 的對照組       |

**待補 Gatling customer case**：金融 / e-commerce 重度 JVM 生態採用 Gatling Enterprise、HAR-driven scenario recording 在 multi-step checkout flow 的實踐。

## 下一步路由

- 上游概念：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 平行 vendor：[k6](/backend/06-reliability/vendors/k6/)、[Locust](/backend/06-reliability/vendors/locust/)、[JMeter](/backend/06-reliability/vendors/jmeter/)
- 下游能力：[09 performance capacity](/backend/09-performance-capacity/) load test 模組
