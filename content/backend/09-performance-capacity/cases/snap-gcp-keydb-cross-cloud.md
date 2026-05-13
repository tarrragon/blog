---
title: "9.C35 Snap：GCP + KeyDB 在 multi-cloud 架構下的低延遲快取"
date: 2026-05-13
description: "Snap 用 GCP 上的 KeyDB cluster 減少跨 cloud cache 延遲、用 TPU 訓練廣告推薦模型"
weight: 35
tags: ["backend", "performance", "capacity", "case-study", "cache", "gcp", "low-latency-sustained"]
---

這個案例的核心責任是補強 GCP cache 維度、並揭示 multi-cloud 架構的隱性 latency 議題。Snap（Snapchat 母公司、日活 4 億 +）2011 年從零起就在 GCP 上、是雲原生最早期客戶之一、但近年走 multi-cloud（GCP + AWS）。這個架構引出「跨 cloud cache latency 怎麼處理」的工程議題。

## 觀察

Snap 在 GCP 的關鍵敘述（引自 [Snap deploys KeyDB on Google Cloud](https://cloud.google.com/blog/products/application-modernization/snap-deploys-keydb-on-google-cloud-to-reduce-cross-cloud-latency)、[Snap TPU recommendation](https://cloud.google.com/blog/products/ai-machine-learning/snap-inc-uses-google-cloud-tpu-for-deep-learning-recommendation-models)）：

| 指標                   | 內容                                              |
| ---------------------- | ------------------------------------------------- |
| 用戶基礎               | 4 億 + DAU、年增 18% YoY                          |
| 開始在 GCP 時間        | 2011 年（產品早期）                               |
| Multi-cloud cache 方案 | GCP 上部署 KeyDB cluster 減少 cross-cloud latency |
| ML training            | TPU（vs GPU 吞吐高 67%、成本低 52%）              |
| 安全框架               | BeyondCorp Enterprise（Zero Trust）               |

關鍵架構決策：在 *GCP* 上部署 KeyDB（Redis fork、multi-threaded）作為 cache layer、減少 cross-cloud latency。

## 判讀

Snap 案例揭露三個 multi-cloud 容量設計的工程重點。

1. **跨 cloud latency 是隱性容量瓶頸**：當 application 在 AWS、cache 在 GCP（或反之）、每個 cache lookup 都吃跨 cloud 網路 latency（通常 5-30ms、視 region pair 而定）。對 [Snap 這類「每次互動查多個 cache」](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 的服務、5ms × 10 cache lookup = 50ms 額外 latency、用戶感受明顯。對應 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/) 的 latency budget 反推。
2. **KeyDB 是 Redis 的 multi-threaded 替代**：Redis 7+ 之前是 single-threaded、單實例吞吐受限。KeyDB（Snap 等大型用戶採用）改成 multi-threaded、單實例 throughput 提升 5-10x、適合超高吞吐 cache 需求。對應 [9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) 的 cache layer 設計、但 Snap 規模更大要走專業 fork。
3. **TPU vs GPU 是 ML training 的容量成本決策**：Snap 算過 GPU 的「throughput -67% + cost +52%」就是 TPU 的反向 — TPU 的 throughput 高 67%、cost 低 52% — 對 ML-heavy 公司是巨大決策。對應 [9.7 成本邊界與 efficiency](/backend/09-performance-capacity/cost-engineering/) 的雲端硬體選型、跟 [9.C31 Mercado Libre Vertex AI](/backend/09-performance-capacity/cases/mercado-libre-latam-bigquery-vertex/) 的 ML 容量規劃同類。

需要警惕：

- KeyDB 是 *fork-based* 軟體、有 vendor lock-in 風險（Snap 大規模採用後、KeyDB 公司被收購、未來 fork 走向不確定）
- TPU 是 *Google 專屬硬體*、不能在其他 cloud 用、是 vendor lock-in 來源
- 「年增 18%」是用戶數、不是流量。流量成長通常超過用戶成長（per-user engagement 上升）

## 策略

可重用的工程做法：

1. **Multi-cloud 架構優先把 cache 跟 application 放同一 cloud**：跨 cloud 的不該是 cache lookup（高頻、低 latency 容忍）、應該是 batch sync（低頻、高 latency 容忍）。對應 [02 快取模組](/backend/02-cache-redis/) 的部署策略。
2. **Redis 規模化遇到 single-threaded 限制時的選項**：
   - 拆 cluster（多個 Redis instance）— 應用層分散 key
   - 換 KeyDB / Dragonfly（multi-threaded fork）
   - 換 Redis 7+ I/O thread（保留 protocol）
   - 換 Memcached（multi-threaded、但功能少）
3. **ML training infrastructure 選型按 throughput / cost 而非品牌**：GPU vs TPU vs Trainium 不是「哪家好」、是「在 *本 workload* 上哪個划算」。要實測 benchmark、不是看 vendor marketing。
4. **跨 cloud 部署的「資料引力」**：data 在哪、application 通常會被 data 吸過去。Snap 把 cache 放 GCP 是因為 production data 在 GCP — 想搬 cache 到 AWS 同時要搬 data、成本高。

跨平台等效：AWS ElastiCache + Cassandra / DynamoDB Global Tables、Azure Cache for Redis + Cosmos DB 都可實作 multi-region cache 但 single-cloud 內。multi-cloud cache 通常要自管（自管 KeyDB / Dragonfly / Redis Cluster）。

## 下一步路由

- 對照其他 cache 案例 → [9.C6 Tinder ElastiCache](/backend/09-performance-capacity/cases/tinder-elasticache-valkey-matching/) / [9.C25 Tubi ML feature store](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)
- 想設計 multi-cloud cache → [02 快取模組](/backend/02-cache-redis/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)
- 想做 ML training 容量規劃 → [9.7 成本邊界](/backend/09-performance-capacity/cost-engineering/) + [9.C31 Mercado Libre](/backend/09-performance-capacity/cases/mercado-libre-latam-bigquery-vertex/)
- 想理解 cross-cloud latency → [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)

## 引用源

- [Snap deploys KeyDB on Google Cloud to reduce cross-cloud latency](https://cloud.google.com/blog/products/application-modernization/snap-deploys-keydb-on-google-cloud-to-reduce-cross-cloud-latency)
- [Snap Inc. uses Google Cloud TPU for deep learning recommendation models](https://cloud.google.com/blog/products/ai-machine-learning/snap-inc-uses-google-cloud-tpu-for-deep-learning-recommendation-models)
- [Snap maintains uptime with MCS from Google Cloud](https://cloud.google.com/blog/products/gcp/snap-maintains-uptime-with-mcs-from-google-cloud/)
- [Why Snap chose BeyondCorp Enterprise](https://cloud.google.com/blog/products/identity-security/why-snap-chose-beyondcorp-enterprise-to-build-a-durable-zero-trust-framework)
