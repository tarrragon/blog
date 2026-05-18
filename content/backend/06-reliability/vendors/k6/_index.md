---
title: "k6"
date: 2026-05-01
description: "現代 load test、JS scripting、Grafana Labs"
weight: 3
tags: ["backend", "reliability", "vendor"]
---

k6 是 Grafana Labs 出品的 load test 工具、承擔三個責任：CLI-first load test（Go 寫成、JS 寫測試 script）、threshold-based CI gate（pass/fail 直接接 CI）、Grafana Cloud k6 / k6 Operator on K8s 分散式。設計取捨偏向「CI-first + JS DX + 整合 Grafana 生態」、是現代 load test 主流選擇。

## 本章目標

讀完本章後、你應該能：

1. 寫 k6 test script（VU / iteration / stages）
2. 設計 threshold + CI gate（pass/fail）
3. 用 xk6 extension 擴展（gRPC / Kafka / SQL）
4. 部署 k6 Operator 做 distributed load
5. 評估 k6 vs Gatling / Locust / JMeter 的選用

## 最短路徑：5 分鐘把 k6 跑起來

```bash
# 1. 安裝
# TODO: brew install k6 / docker run grafana/k6

# 2. 寫 test.js
# TODO: import http from 'k6/http'; export default function(){ http.get(...) }

# 3. 跑
# TODO: k6 run --vus 10 --duration 30s test.js
```

## 日常操作與決策形狀

### Test script 結構

子議題：

- export default function（per-VU iteration）
- export const options（VU / duration / stages / thresholds）
- Setup / teardown
- 對應指令範例：`k6 run --vus 100 --duration 10m`

### Threshold + CI gate

子議題：

- thresholds: `http_req_duration: ['p(95)<500']`
- Exit code 非 0 → CI fail
- Custom metric thresholds
- 對應 [6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)

### Test pattern

子議題：

- Smoke / Load / Stress / Spike / Soak / Breakpoint
- Stages（ramp-up / steady / ramp-down）
- VU vs iteration vs RPS-based

## 進階主題（按需閱讀）

### xk6 extensions

子議題：

- 自訂 binary：xk6 build + import extension
- 內建：HTTP / WebSocket / gRPC
- 社群：Kafka / SQL / Redis / browser
- 對應 cross-protocol load test

### k6 Operator on K8s

子議題：

- TestRun CRD
- Distributed load（多 pod 模擬高 VU）
- Result aggregation
- 對應 [Kubernetes vendor 頁](/backend/05-deployment-platform/vendors/kubernetes/)

### Grafana Cloud k6

子議題：

- Managed runner（多 region load source）
- 跟 Grafana dashboard 整合
- 跟 Loki / Tempo trace 關聯（test → APM trace）

### Browser testing

子議題：

- k6 browser：Chromium-based browser testing
- 跟 Playwright 重疊但更聚焦 load
- 適合 frontend regression load test

### CI integration

子議題：

- GitHub Actions / GitLab CI / Jenkins 整合
- Artifact + report upload
- 對應 [6.8 Release Gate](/backend/06-reliability/release-gate/)

### k6 vs xk6 vs Cloud

子議題：

- k6 OSS：CLI + local script
- xk6：build custom binary with extensions
- k6 Cloud / Grafana Cloud k6：managed + UI

## 排錯快速判讀

### Test 結果差異大

操作原則：local network / VU saturation / target 處理能力。

### Threshold 太鬆 / 太嚴

操作原則：baseline 不準 / production traffic pattern 沒模擬。

### Distributed load 不均勻

操作原則：k6 Operator 分配 VU 不均 / pod 規格差異。

### Browser testing 慢 / 不穩

操作原則：Chromium 啟動成本 / network condition / target 反應時間。

## 何時改走其他服務

| 需求形狀                   | 改走                                                              |
| -------------------------- | ----------------------------------------------------------------- |
| JVM 生態                   | [Gatling](/backend/06-reliability/vendors/gatling/)               |
| GUI / 老牌                 | [JMeter](/backend/06-reliability/vendors/jmeter/)                 |
| Python                     | [Locust](/backend/06-reliability/vendors/locust/)                 |
| 純 browser flow            | Playwright / Cypress                                              |
| Cloud managed              | Grafana Cloud k6 / BlazeMeter / k6 Cloud                          |
| Capacity planning（非 CI） | [09 performance capacity 模組](/backend/09-performance-capacity/) |

## 不在本頁內的主題

- JS 語言基礎
- k6 完整 API
- Grafana Cloud k6 pricing

## 案例回寫

| 案例方向                                                                                                           | 對應主題                                        |
| ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)             | 峰值前 load test 對齊 capacity model + CI gate  |
| [LinkedIn：Capacity 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/) | automated load testing 變成日常流程的工程化做法 |

**待補 k6 customer case**：Grafana Labs / k6 customer engineering blog、企業遷移 JMeter → k6 案例。

## 下一步路由

- 上游概念：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 平行 vendor：[Gatling](/backend/06-reliability/vendors/gatling/)、[Locust](/backend/06-reliability/vendors/locust/)、[JMeter](/backend/06-reliability/vendors/jmeter/)
- 下游能力：[09 performance capacity](/backend/09-performance-capacity/) load test 模組
