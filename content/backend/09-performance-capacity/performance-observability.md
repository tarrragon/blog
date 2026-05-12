---
title: "9.8 效能可觀測性"
date: 2026-05-12
description: "saturation metric、USE / RED method、cost dashboard"
weight: 8
tags: ["backend", "performance", "capacity", "observability"]
---

## 概念定位

效能可觀測性的責任是讓容量決策有訊號基礎。沒有適當訊號時、就算有壓測結果跟容量計畫、也看不到「現在實際距離 saturation 多遠」、無法做即時調整。

跟 [9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) 的關係：9.4 找到 saturation 點、9.8 定義持續監控這個點的訊號跟 dashboard。跟 [04 可觀測性模組](/backend/04-observability/) 是 sibling — 04 處理通用觀測、9.8 處理 *容量規劃用* 的觀測。

本章不重複 04 的訊號治理基礎、聚焦在 *容量 / 效能 / 成本三條觀測線怎麼整合*。讀完後讀者能設計一個「容量 dashboard」、回答「現在距離 saturation 還有多遠、什麼時候該擴」。

## USE method 在 production 持續監控

[USE method](/backend/knowledge-cards/use-method/) 不只是壓測時用、production 也要持續監控。

對每個資源（CPU / RAM / disk / network / DB connection / cache pool / file descriptor）量三個維度：

- **Utilization**（使用率 0-100%）：直觀但會誤判
- **Saturation**（queue depth）：早期警訊
- **Errors**（資源層錯誤）：已經出事的訊號

**為什麼不能只看 utilization**：

- CPU 100% 但 run queue 空 → 還能撐（單純 CPU bound）
- CPU 80% 但 run queue 不斷增長 → 已 saturate（saturation 比 utilization 領先）

**Saturation metric 是 capacity warning 的最早訊號**：

- queue depth（每個 queue / pool）
- connection pool 使用率（最常見隱性 bottleneck）
- thread pool / coroutine count
- event loop lag（Node.js、async runtime）
- GC pause time / frequency
- cache hit rate / eviction rate
- replication lag

**Dashboard 設計**：每個關鍵資源獨立 panel、同時顯示 utilization 跟 saturation。alert 在 *saturation 起飛* 時觸發、不是 utilization 滿。

對應案例：[Lemino connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — connection saturation 是 RDB 的真正 bottleneck、不是 CPU；[Zomato latency 降 90%](/backend/09-performance-capacity/cases/zomato-tidb-to-dynamodb-migration/) — 從 TiDB 換到 DynamoDB、saturation 行為完全不同、observability 也要跟著改。

## RED method：請求層的容量訊號

[RED method](/backend/knowledge-cards/red-method/) 跟 USE 互補、從請求層看容量。

- **Rate**：requests per second（每個 service / endpoint）
- **Errors**：error rate
- **Duration**：latency distribution（histogram、不是單一 percentile）

**Duration 比 Errors 早**：duration p99 飆通常先於 error rate 上升、是 saturation 的早期警訊。

**每個 endpoint 都要有 RED**：不能只看全站 average、要分 endpoint。登入 endpoint 跟結帳 endpoint 的 saturation 行為不同、混在一起看不到 issue。

**Histogram 是必須、不是 nice-to-have**：

- 只記 p99 → 看不到 p999、看不到 distribution shape
- 記 histogram → 可以隨時算任何 percentile、可以做 long-tail 分析
- Prometheus histogram、OpenMetrics histogram 是現代標準

對應案例：[GR8 Tech 25ms p95](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) — p95 是業務 KPI、不是技術指標、每個 endpoint 都有獨立 SLO。

## p50 / p95 / p99 / p999 的取捨

不同 percentile 反映不同問題、選錯 percentile 會錯失 issue。

- **p50（中位數）**：整體狀況、感覺正常的指標、對長尾不敏感
- **p95**：日常 user-perceived experience、大多數用戶感受到的延遲
- **p99**：minority but critical 用戶體驗、SLO 常訂在這
- **p999**：極端長尾、受 GC pause / leader election / retry storm 影響、internal critical 系統訂在這

**業務 SLO 通常訂 p99**：「99% 用戶 request < 500ms」是常見承諾、合約 SLA 也通常基於 p99。
**Internal critical 系統訂 p99.9**：金融交易、即時配對、客服 SaaS（5 個 9 可用性對應 5 個 9 latency 期待）。

**紀錄分布、不只紀錄 percentile**：

- gauge p99 → 看不到 distribution shape、看不到 multimodal 分布
- histogram → 可以重新計算任何 percentile、可以對比 distribution、可以找 anomaly

對應案例：[Tubi p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML inference 在 p99 才能控制用戶體驗、p50 沒意義；[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — 必須關注 p999、RAFT 系統長尾顯著。

詳見 [Tail Latency 卡片](/backend/knowledge-cards/tail-latency/)。

## Cost dashboard

成本訊號跟容量訊號要 *並列顯示*、不要分開看。

**Per-service / per-endpoint cost attribution**：

- 每個 service 自己的雲端成本
- 拆到每個 endpoint
- 跟 RPS / latency 並列、看「成本上升是因為流量還是低效」

**Cost per request 的時序變化**：

- 突然上升通常是 *退化* 訊號（新版本沒效率）
- 緩慢上升通常是 *規模* 訊號（用戶增加但 efficiency 沒變）

**成本異常告警（vs 容量異常告警）**：

- 容量告警：utilization > X% → 擴容
- 成本告警：cost spike > X% → review
- 兩者可能同時觸發（autoscaler 擴容也擴 cost）、要區分

**跟業務 metric 對齊**：cost per active user、cost per transaction、cost per ML inference。業務 metric 級別的 cost 才能 review unit economics。

對應案例：[Lyft 100+ 微服務各自 cost](/backend/09-performance-capacity/cases/lyft-microservice-eight-x-peak/) — 微服務粒度的 cost attribution、找出哪個 service 過貴；對應 [04.14 cost attribution](/backend/04-observability/cost-attribution/)。

## Continuous profiling

[Continuous profiling](/backend/knowledge-cards/continuous-profiling/) 是現代效能 observability 的關鍵環節 — production 持續取 profile（CPU / heap / lock）、隨時可以做 diff 跟 root cause。

**工具生態**：

- Datadog Continuous Profiler、Pyroscope（開源 + Grafana 整合）、Parca（CNCF）
- GCP Cloud Profiler、Azure Application Insights Profiler、AWS CodeGuru Profiler
- Overhead 通常 < 1% CPU、放心開在 production

**跟 distributed tracing 整合**：trace → span → profile。一個 slow request 點下去、能看到對應 span、再下去看 profile。

**Profile diff 是 release gate 的核心訊號**：每次 deploy 後自動對比 baseline、退化幅度過門檻 trigger alert。詳見 [9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 跟 [Profile Diff 卡片](/backend/knowledge-cards/profile-diff/)。

對應案例：[Netflix 多 DB 統一後 profile 變單純](/backend/09-performance-capacity/cases/netflix-aurora-consolidation/) — DB 統一 → application 層 profile 噪音降低 → 退化定位更快。

## Cardinality cost governance

效能 observability 的成本經常爆炸、源頭通常是 high cardinality metric。

**高 cardinality 來源**：

- per-user metric（user_id label）
- per-request metric（request_id label）
- per-trace metric（trace_id label）

**為什麼會爆**：Prometheus 等 metric system 為每個 label 組合存獨立 time series、cardinality = 所有 label value 的笛卡爾積。100 萬 user × 100 endpoint × 10 region = 10 億 time series、儲存爆炸。

**對策**：

- high cardinality 資訊放 log / trace、不放 metric
- metric label 限制在 low-cardinality 維度（service、endpoint、region、status）
- 真的需要 high-cardinality 分析、用 sampled trace + log query

對應 [04.10 cardinality cost governance](/backend/04-observability/cardinality-cost-governance/)、跟 [Metric Cardinality 卡片](/backend/knowledge-cards/metric-cardinality/)。

## 訊號跟 SLO 對接

最後一層整合：每個 saturation metric 都要對應一個 SLO threshold、訊號驅動行動。

**訊號 → 行動鏈**：

- saturation metric 超 threshold → trigger alert
- alert 觸發 → trigger autoscaler / runbook / oncall
- 持續超 threshold → trigger error budget burn alert
- error budget 用完 → trigger release freeze

**Alert 不要太敏感**：

- false positive 浪費 oncall、長期會 alert fatigue（[Alert Fatigue 卡片](/backend/knowledge-cards/alert-fatigue/)）
- 用 multi-window multi-burn-rate alert（Google SRE 推薦）
- 用 symptom-based alert（業務影響）而非 cause-based alert（單一資源）

跟 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/) 直接對接。

## 案例對照

| 案例                                                                                                         | 教學重點                             |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| [9.C5 Amazon Ads 99.999%](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)            | SLO 5 個 9 的訊號治理                |
| [9.C24 Genesys 12 個月 99.999%](/backend/09-performance-capacity/cases/genesys-dynamodb-99999-availability/) | 滾動 SLO 觀測                        |
| [9.C25 Tubi p99 分解](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)             | ML inference 多 stage latency budget |
| [9.C2 GR8 Tech p95 是業務 KPI](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/)   | latency 不只是技術指標               |

## 下一步路由

- 上游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/) / [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 下游：[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)
- 跨模組：[04 可觀測性模組](/backend/04-observability/)（基礎訊號）

## 既建知識卡片

- [USE Method](/backend/knowledge-cards/use-method/)
- [RED Method](/backend/knowledge-cards/red-method/)
- [Tail Latency](/backend/knowledge-cards/tail-latency/)
- [Continuous Profiling](/backend/knowledge-cards/continuous-profiling/)
- [Cost Per Request](/backend/knowledge-cards/cost-per-request/)
