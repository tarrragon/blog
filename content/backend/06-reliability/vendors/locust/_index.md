---
title: "Locust"
date: 2026-05-01
description: "Python-based load test、distributed、易擴展"
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

## 最短路徑：5 分鐘把 Locust 跑起來

```bash
# 1. 安裝
# TODO: pip install locust

# 2. 寫 locustfile.py
# TODO: class User(HttpUser): wait_time = ..., @task def hello(self): ...

# 3. 跑
# TODO: locust -f locustfile.py --host=http://target
# TODO: 瀏覽器 http://localhost:8089 操作
```

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

- Headless mode + exit code
- CSV / JSON report
- 對應 [6.8 Release Gate](/backend/06-reliability/release-gate/)

### Distributed scaling

子議題：

- Kubernetes 部署
- 多 region load source
- Result aggregation

## 排錯快速判讀

### High VU 跑不上去

操作原則：Python GIL + 單 worker 限制、用 distributed mode。判讀：CPU / network bottleneck？

### Worker disconnect

操作原則：master / worker network 不通、heartbeat timeout。判讀：log + master UI。

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
