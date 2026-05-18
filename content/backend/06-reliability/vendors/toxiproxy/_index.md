---
title: "Toxiproxy"
date: 2026-05-01
description: "TCP-level fault injection proxy（Shopify 開源）"
weight: 10
tags: ["backend", "reliability", "vendor"]
---

Toxiproxy 是 Shopify 開源的 TCP-level fault injection proxy、承擔三個責任：TCP 層 fault inject（latency / bandwidth / partition / slow_close）、integration test 中可程式化故障注入（reproducible）、client SDK 多語言（Go / Ruby / Python / JS）。設計取捨偏向「CI-friendly + reproducible + 細粒度 TCP control」、不適合 production chaos、適合 integration test 跟 dependency failure 模擬。

## 本章目標

讀完本章後、你應該能：

1. 跑起 Toxiproxy server + 設 listener / upstream proxy
2. 用 client SDK 注入 latency / partition / bandwidth toxic
3. 整合 Toxiproxy 到 integration test（before/after test hook）
4. 用 Docker Compose 整合
5. 評估 Toxiproxy vs Chaos Mesh NetworkChaos 的選用

## 最短路徑：5 分鐘把 Toxiproxy 跑起來

```bash
# 1. 啟動 server
# TODO: docker run -d -p 8474:8474 -p 26379:26379 ghcr.io/shopify/toxiproxy

# 2. 建 proxy（Redis 為例）
# TODO: curl -X POST localhost:8474/proxies -d '{"name":"redis","listen":"0.0.0.0:26379","upstream":"redis:6379"}'

# 3. 注入 toxic
# TODO: curl -X POST localhost:8474/proxies/redis/toxics -d '{"type":"latency","attributes":{"latency":1000}}'
```

## 日常操作與決策形狀

### Toxic types

子議題：

- latency：增加延遲
- bandwidth：限制頻寬
- slow_close：connection close 慢
- timeout：connection timeout
- slicer：把 TCP packet 切片
- limit_data：limit 傳輸量

### API + Client SDK

子議題：

- HTTP API（8474 default）
- Client SDK：Go / Ruby / Python / JS
- Programmatic toxic enable/disable

### Integration test pattern

子議題：

- before each test 設 toxic
- after each test cleanup
- Test isolation：每 test reset proxy state

## 進階主題（按需閱讀）

### Docker Compose 整合

子議題：

- service depends_on toxiproxy
- 應用透過 toxiproxy connect 真正 DB / cache
- environment variable 切換 toxiproxy vs direct

### Reproducible chaos

子議題：

- Toxic seed（reproducible random）
- Toxic stream（upstream / downstream）
- 對應 test reproducibility

### 跟 Chaos Mesh NetworkChaos 對比

子議題：

- Toxiproxy：CI / integration test、TCP 層
- Chaos Mesh：production、K8s pod 層
- 選擇判讀：testing CI → Toxiproxy；K8s staging chaos → Chaos Mesh

### 跟 client retry / circuit breaker 配合

子議題：

- 驗證 client 對 dependency failure 的應對
- Retry budget / backoff 測試
- Circuit breaker trigger 測試
- 對應 [knowledge cards retry-budget](/backend/knowledge-cards/retry-budget/)

## 排錯快速判讀

### Proxy 連不上

操作原則：先 `curl :8474/proxies` 看 proxy state、再看 network。

### Toxic 沒生效

操作原則：toxic enabled 但 attribute 設錯。判讀：API GET toxics 看當前狀態。

### Test state pollute

操作原則：test 間沒 reset proxy、state 殘留。修法：每 test 開頭 reset。

### Performance overhead

操作原則：Toxiproxy 本身有 latency overhead（μs 級）、不適合 production sensitivity。

## 何時改走其他服務

| 需求形狀                | 改走                                                                   |
| ----------------------- | ---------------------------------------------------------------------- |
| K8s production chaos    | [Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/) NetworkChaos |
| 商業跨平台              | [Gremlin](/backend/06-reliability/vendors/gremlin/)                    |
| Application-level error | Mock / stub library                                                    |
| AWS-native              | AWS Fault Injection Service                                            |

## 不在本頁內的主題

- Toxic 內部實作
- 各語言 SDK 完整 API
- TCP protocol 細節

## 案例回寫

**Shopify 自家**：Toxiproxy 是 Shopify 開源、Shopify reliability cases 多有引用。

| 案例方向                                                                                                          | 對應主題                                                         |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Shopify：BFCM 容量治理與 Game Day](/backend/06-reliability/cases/shopify/bfcm-capacity-and-game-day/)            | resiliency matrix + TCP-level fault injection 的原生使用脈絡     |
| [Stripe：Idempotency 與零停機遷移](/backend/06-reliability/cases/stripe/idempotency-and-zero-downtime-migration/) | integration test 模擬 dependency 失敗、驗證 retry 與 idempotency |

**Case 庫稀薄**：Toxiproxy 主要 case 集中在 Shopify 自家、其他 adopter 案例待補。

- **待補 Toxiproxy adopter case**：其他公司用 Toxiproxy 做 dependency failure 測試
- **候選 case**：Pinterest（cache failure mode integration test）、Spotify（squad 自管 integration chaos）— 若未來收錄需先在 cases/ 補正文

## 下一步路由

- 上游概念：[6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)
- 平行 vendor：[Chaos Mesh](/backend/06-reliability/vendors/chaos-mesh/)、[Gremlin](/backend/06-reliability/vendors/gremlin/)
- 下游能力：[knowledge cards retry-budget](/backend/knowledge-cards/retry-budget/)
