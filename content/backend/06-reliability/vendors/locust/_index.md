---
title: "Locust 在可靠性驗證的工具總覽：user class、headless 執行、分散施壓與 regression gate"
date: 2026-05-01
description: "Python 團隊要用 Locust 寫驗證用的負載測試、把它接進 release 前的效能 regression gate，或在 Locust 與 k6、Gatling、JMeter 之間選擇驗證流程的工具時讀"
weight: 6
tags: ["backend", "reliability", "vendor"]
---

Locust 是 Python-based load test 工具、承擔三個責任：Python class-based test 設計（user behavior 表達力強）、distributed mode（master / worker 內建）、Web UI 即時觀察。設計取捨偏向「Python DX + 高度自訂邏輯 + 任何 Python lib 都可用」、適合 Python 團隊與需要極高自訂邏輯的場景。

## 本章目標

讀完本章後、你應該能：

1. 寫 Locust user class + task
2. 跑 standalone + distributed mode
3. 自訂 client（非 HTTP、如 gRPC / WebSocket）
4. 設計 task weight + on_start / on_stop hook
5. 評估 Locust vs k6 / Gatling 的選用

## 實作紀錄：在本機用 Docker 跑 Locust

實際跑過的完整流程在 `hands-on/`：[Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/)，用 Docker 跑受測服務與 Locust、locustfile、headless 執行與 CSV、內建的 exit code、quitting 事件裡的門檻判定、--reset-stats 與 on_start、master 與 worker 的分散執行。Web UI 的操作不在那次的實測裡。

## 日常操作與決策形狀

### User class + task

子議題：

- HttpUser / FastHttpUser（FastHttpUser 用 geventhttpclient、效能高）
- @task decorator + weight
- on_start / on_stop（per-VU setup / teardown）
- 對應 Python class inheritance

### Distributed mode

子議題：

- master：協調 + 收集 metric
- worker：實際發送 request
- `locust --master` / `locust --worker --master-host=...`
- 多 worker 突破 Python GIL 限制

### Web UI vs headless

子議題：

- Web UI（dev / interactive）
- Headless（`--headless --users N --spawn-rate N --run-time T`）
- 對應 CI 整合：CSV report

## 進階主題（按需閱讀）

### 自訂 client（非 HTTP）

子議題：

- 任何 Python lib 都可包成 user
- gRPC / WebSocket / database / queue 都行
- request event 手動 fire

### Custom request

子議題：

- self.client.get/post（HTTP）
- 自訂 event emission
- Custom statistics

### locust-plugins 生態

子議題：

- locust-plugins：第三方 plugin（CSV report enhanced / Postgres / Kafka / etc）
- Custom shape（dynamic load profile）
- TaskSet / SequentialTaskSet

### CI integration

子議題：

- Headless mode + exit code：內建只在有失敗的請求或未處理的例外時回 1，延遲與吞吐量的門檻要在 `quitting` 事件裡自己判定、寫進 `process_exit_code`
- CSV / JSON report
- 門檻判定、預熱的請求與 gate 失敗的排查：[Locust 在效能 regression gate 的用法](/backend/06-reliability/vendors/locust/locust-performance-regression-gate/)；gate 在 release 流程裡的位置：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)

### Distributed scaling

子議題：

- Kubernetes 部署
- 多 region load source
- Result aggregation

## 排錯快速判讀

### High VU 跑不上去

操作原則：Python GIL + 單 worker 限制、用 distributed mode。判讀：CPU / network bottleneck？

### Worker disconnect

操作原則：master / worker network 不通、heartbeat timeout。判讀：log + master UI。heartbeat 的間隔與判定失聯的次數、一次實際遇到的失聯與查法，見 [Locust 在本機跑負載測試的實測紀錄](/backend/06-reliability/vendors/locust/hands-on/locust-local-lab/) 的〈master 與兩個 worker〉。

### Custom protocol 報告不正確

操作原則：手動 event fire 缺 / metric name 不對。

### Memory leak

操作原則：long run test、user state accumulate。判讀：on_stop cleanup。

## 何時改走其他服務

| 需求形狀                | 改走                                                              |
| ----------------------- | ----------------------------------------------------------------- |
| 編譯後分發 / 高 VU 單機 | [k6](/backend/06-reliability/vendors/k6/)                         |
| JVM 生態                | [Gatling](/backend/06-reliability/vendors/gatling/)               |
| GUI / 老牌              | [JMeter](/backend/06-reliability/vendors/jmeter/)                 |
| Cloud managed           | k6 Cloud / BlazeMeter / Locust 自管 K8s                           |
| Capacity planning       | [09 performance capacity 模組](/backend/09-performance-capacity/) |

## 不在本頁內的主題

- Python 語言基礎
- gevent / asyncio 內部
- locust-plugins 完整列表

## 案例回寫

| 案例方向                                                                                                           | 對應主題                                                 |
| ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- |
| [LinkedIn：Capacity 與 On-call 分層](/backend/06-reliability/cases/linkedin/capacity-headroom-and-oncall-tiering/) | automated load testing 對齊 headroom 預測（Python 場景） |

**Case 庫稀薄**：本 cases/ 目錄目前沒有以 Locust 為主軸的案例。可參考候選方向：

- **待補 Locust customer case**：Python-heavy 團隊 load test 採用案例、distributed Locust 大規模部署案例
- **候選 case**：Pinterest（ML serving / 推薦系統壓測場景）、Spotify（squad-based 各團隊自管壓測）— 若未來收錄需先在 cases/ 補正文，本欄再寫實際 link

## 下一步路由

- 上游概念：[6.13 Performance Regression Gate](/backend/06-reliability/performance-regression-gate/)
- 平行 vendor：[k6](/backend/06-reliability/vendors/k6/)、[Gatling](/backend/06-reliability/vendors/gatling/)
- 下游能力：[09 performance capacity](/backend/09-performance-capacity/)

## Backlog

格式見 [Backlog 段格式規範](/posts/backlog-format-spec/)。

| 項目                                                                                                                                                                                                                                            | 類型   | 前置條件     | 規模 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------ | ---- |
| locust-local-lab〈master 與兩個 worker〉的 heartbeat 失聯：2026-10-28 前兩次分散執行 worker 停住約 4 秒、之後五次沒有重現，成因沒有查出；重現時同時收集施壓機的 CPU 與 worker 的 log，查出成因後把排查經過寫成 work-log、實作文章那一段改連過去 | vendor | 能重現的環境 | 小   |
