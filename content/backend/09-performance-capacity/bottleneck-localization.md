---
title: "9.5 瓶頸定位流程"
date: 2026-05-12
description: "從 app 到 DB / cache / broker / 第三方 quota 的逐層瓶頸定位"
weight: 5
tags: ["backend", "performance", "capacity", "bottleneck"]
---

## 概念定位

瓶頸定位的責任是回答「為什麼擴 app 沒用」這類問題。當 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 找到 knee point 之後、下一步是知道 *哪個 resource* 先 saturate。沒有定位、容量規劃只能 *全部翻倍*；有定位、可以 *精準加在瓶頸層*。

跟其他章節的關係：跟 9.4 是姊妹章（9.4 找出 knee、9.5 定位 knee 的成因）、跟 [9.8 效能可觀測性](/backend/09-performance-capacity/performance-observability/) 互補（9.8 訊號治理、9.5 用訊號做定位）。

本章不深入工具操作、聚焦在 *方法論* — 怎麼按層次定位、怎麼避免常見誤判、怎麼區分可分散 vs 不可分散瓶頸。

## USE method：resource-oriented 觀察

Brendan Gregg 的 USE method 提供逐層定位的最小框架：對每個資源、量三個維度。

**Utilization**：資源使用率 0-100%。CPU 70%、memory 60%、disk 40% 這類數字。
**Saturation**：資源排隊量（queue depth）。CPU run queue length、memory swap rate、disk I/O wait queue、connection pool wait count。
**Errors**：資源層錯誤。CPU page fault、memory OOM、disk I/O error、network packet drop、connection refused。

對每個資源（CPU / RAM / disk / network / DB connection / cache connection / file descriptor）逐一檢查。*第一個出現 saturation 上升的資源是 bottleneck*、不是 utilization 最高的那個。

USE 跟 [RED method](/backend/knowledge-cards/red-method/)（rate / errors / duration）互補：USE 看「哪個資源頂不住」、RED 看「哪個 endpoint 表現變差」。容量規劃通常先用 USE 找瓶頸、再用 RED 看影響面。

詳見 [USE Method 卡片](/backend/knowledge-cards/use-method/)。

## 逐層定位流程

從 application 層往下查、按依賴鏈逐層檢查。多數 bottleneck 在 application 跟 DB 兩層、但不能跳過其他層 — 偶爾真的在意外位置。

**1. 應用層（application）**：

- thread / coroutine pool 使用率：是否已飽和
- event loop lag（Node.js、async runtime）：> 50ms 是警訊
- GC pause 頻率與時長：影響 p99 / p999
- request queue（accept queue、application internal queue）

**2. DB 層**：

- connection pool 使用率（最常見隱性 bottleneck）
- slow query frequency
- replication lag
- lock contention（row lock、table lock）
- transaction queue depth

**3. Cache 層**：

- hit rate（突然下降是訊號）
- eviction rate
- connection 飽和（cache pool 也會耗盡）
- memory utilization

**4. Broker / queue 層**：

- consumer lag（最重要的單一指標）
- queue depth
- dead-letter rate
- broker connection count

**5. 外部 API / 第三方 quota**：

- rate limit 觸發頻率
- retry storm（自家 retry 把對方 quota 打爆）
- circuit breaker trip
- timeout rate

**6. 網路層**：

- bandwidth utilization
- packets per second（PPS limit）
- socket count（file descriptor limit）
- 跨 region / 跨 AZ latency

**7. DNS / load balancer**：

- DNS resolution latency
- LB connection establishment time
- TLS handshake duration
- backend health check failure

對應案例：[Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) RDB connection limit 是隱性 bottleneck、CPU / RAM 都還行；[Tixcraft 付款層獨立](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 把高頻搶票流量跟低頻付款流量分離、避免一層拖累另一層。

## Profile 工具鏈

USE 找出哪一層 saturate 之後、profile 工具找出 *該層的哪段 code* 拖累。

**Continuous profiling**：Datadog Continuous Profiler、Pyroscope（開源 + Grafana 整合）、Parca（CNCF）、GCP Cloud Profiler、Azure Application Insights Profiler、AWS CodeGuru Profiler。production 持續取樣 CPU / heap / lock、overhead 通常 < 1%。

**Distributed tracing**：OpenTelemetry、Jaeger、Tempo、AWS X-Ray、GCP Cloud Trace、Azure Application Insights。記錄 request 在每個 service / 每個 stage 花了多少時間、找跨服務的 latency 累積。

**Flame graph**：profile 結果視覺化的標準。從寬度可以看到「哪段 code 佔 CPU 最多」。學會看 flame graph 是 SRE 的基本功。

**Profile diff**：壓測 baseline 跟 release candidate 比 stack 差異。看 *相對變化* 而非絕對值。詳見 [Profile Diff 卡片](/backend/knowledge-cards/profile-diff/)。

對應案例：[Netflix Aurora storage / compute 分離](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 統一後 application profile 變單純、退化來源更容易識別。

詳見 [Continuous Profiling 卡片](/backend/knowledge-cards/continuous-profiling/)。

## 跨層依賴鏈

瓶頸不一定在 *本服務*、可能在 *下游服務*。這層判斷常被忽略。

**第三方 API quota** 是常見隱性瓶頸。Twilio SMS、Stripe API、Slack webhook、Sendgrid email、Google Maps API 都有 rate limit。自家服務看起來健康、實際是 *對方 throttle*、自家 retry 再讓對方更慢。

**跨 region / 跨 zone 網路延遲** 是累積的。一個 user request 經過 5 個 service、每個 service 跨 AZ 一次、累積 10-20ms cross-AZ latency。看起來每個 service 都很快、但 end-to-end 慢。

**Downstream cache** 也是依賴。app 看起來健康、但其實是 cache 在擋；cache 突然 cold start（restart、eviction storm）、application 直接被打爆。

對應案例：[PayPay 行動支付](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/) — DynamoDB 寫入可以撐 3K msg/sec、但 APNs / FCM 一天的 quota 有限、推送下游才是瓶頸。

## 可分散 vs 不可分散瓶頸

定位完瓶頸後、要判斷它 *可不可以橫向擴*。這個判斷決定能不能用「加機器」解決。

**可分散瓶頸**：

- stateless app server → 加機器有用
- partitioned KV / OLTP（partition key 均勻時）→ 加 partition 有用
- read replica（read-heavy workload）→ 加 replica 有用
- worker pool → 加 worker 有用

**不可分散瓶頸**：

- consensus DB（RAFT / Paxos）→ 加節點不一定快（[quorum](/backend/knowledge-cards/quorum/) overhead）
- single leader DB（master 寫）→ 必須垂直擴
- 中央 coordinator → 必須拆解或垂直擴
- 共享 cache（hot key）→ 必須改 partition key 或加 local cache

判斷不可分散的關鍵是「協調成本」。一個操作必須 *跟所有 / 多數節點協調* 才能完成、就不可水平擴。

對應案例：[Coinbase RAFT consensus](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — consensus 不可水平擴、所以 *選擇不擴*、改用單機極致；[Spanner TrueTime](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — TrueTime 把協調成本 amortize 到 hardware（GPS + 原子鐘）、讓 OLTP 可水平擴。

## 常見定位陷阱

**看單一指標就下結論**：CPU 100% 不一定是 bottleneck（可能 saturation queue 空）；CPU 50% 不一定健康（可能 saturation queue 已滿）。always 看 USE 三個維度。

**平均看 OK、p99 看不出來**：average latency 50ms 看起來健康、p99 500ms 已經出事。用 percentile、不用 average。

**Observer effect**：profile / tracing 本身有 overhead、量測會輕微影響系統。critical path 上的 instrumentation 要 sampled 不要 100%。

**跨 release 比較 baseline 沒對齊**：上週的 baseline 對應 v1.2、這週的 candidate 對應 v1.3、但 v1.2 跟 v1.3 之間還有 schema migration / hardware 變化、baseline 已經漂移。重新建 baseline 再 diff。

## 案例對照

| 案例                                                                                                             | 教學重點                                |
| ---------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)                     | connection limit 是 RDB 隱性 bottleneck |
| [9.C15 Tixcraft 付款層獨立](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)         | 關鍵路徑切分避免 cross contamination    |
| [9.C3 Coinbase RAFT consensus](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) | 不可分散 bottleneck                     |
| [9.C26 PayPay](/backend/09-performance-capacity/cases/paypay-mobile-payment-messaging/)                          | 下游 APNs / FCM quota 瓶頸              |

## 下一步路由

- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)
- 下游：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)（針對 bottleneck 規劃）
- 下游：[9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/)（用 profile diff 改進）
- 跨模組：[04 可觀測性模組](/backend/04-observability/) / [05 部署平台模組](/backend/05-deployment-platform/)

## 既建知識卡片

- [USE Method](/backend/knowledge-cards/use-method/)
- [RED Method](/backend/knowledge-cards/red-method/)
- [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)
- [Profile Diff](/backend/knowledge-cards/profile-diff/)
- [Universal Scalability Law](/backend/knowledge-cards/universal-scalability-law/)
