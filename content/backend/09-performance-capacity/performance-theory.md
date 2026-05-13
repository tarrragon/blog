---
title: "9.1 壓測理論與系統行為"
date: 2026-05-12
description: "Little's Law、queueing theory、USL、saturation curve 在容量規劃中的角色"
weight: 1
tags: ["backend", "performance", "capacity", "theory"]
---

## 概念定位

壓測理論的角色是讓「加機器能不能解決」這個問題從直覺變成可推導。沒有理論基礎時、容量決策容易陷入「跑壓測 → 看數字 → 加機器」的盲試循環；有理論之後、可以從「現在的延遲 / 吞吐 / 並發量」反推「瓶頸在哪個資源、加什麼有效」。

本章是 9.2-9.12 的共同基礎。後續章節的 workload modeling、saturation discovery、capacity planning、SLO 都會回引本章的數學工具。讀者可以把這章當作「容量規劃的最小詞彙表」、其他章節是這些詞彙的應用情境。

本章不深入推導公式、聚焦在 *工程意義*。讀完之後讀者能回答：為什麼系統在 80% utilization 就該擴、為什麼加機器會邊際效益遞減、為什麼 sub-ms 延遲需求會反推架構選擇。

## Little's Law：穩態系統的最小數學工具

Little's Law 用一條等式 L = λW 把三個變數綁在一起：L 是系統內平均並發數、λ 是請求到達率、W 是請求平均逗留時間。這個關係在 *穩態*（流量已穩定、不在 warmup 階段）必然成立、不需要假設特定分布或服務模式。

工程上最有價值的用法是「反推」。給定預期 RPS λ = 1000 跟 SLO latency 上限 W = 200ms、能算出系統最大穩態並發 L = 1000 × 0.2 = 200。這個 200 直接對應「connection pool size」「thread pool size」「async worker count」這類容量參數 — 訂得比 200 小、系統撐不住預期流量；訂得比 200 大太多、資源浪費。

反向也成立。當 connection pool 卡死在某個 size L、latency budget W 已訂、能算出可支撐的 RPS。這個算法在 capacity planning 階段比 ramp-up 壓測更快、可以先用 Little's Law 篩掉明顯撐不住的配置、再用壓測驗證剩下的候選。

對應案例：[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) 把 W 訂在 sub-millisecond、所有架構選擇都從這個 W 反推；[Tubi ML p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) 從 W 反推 feature lookup 必須 cache hit 路徑、不能回到持久 store。

詳見 [Little's Law 卡片](/backend/knowledge-cards/little-law/)。

## Queueing Theory：為什麼 80% 利用率就是 knee

排隊論（M/M/c 模型）解釋了一個常見直覺：「系統在 50% utilization 看似還很閒、80% 就該擴、90% 已經太晚」。這個直覺不是經驗法則、是 *數學必然*。

M/M/c 系統的平均 queue length 跟 utilization 之間是非線性關係。當 utilization 從 50% 漲到 70%、queue length 約增加 2-3 倍；從 70% 漲到 90%、queue length 增加 10 倍以上。latency 跟 queue length 成正比（Little's Law 又出現）、所以 latency 也呈現同樣的指數成長。

工程意義：健康系統運轉在 50-70% utilization、超過 80% 就接近 knee、超過 90% 進入不可預測區。「為什麼明明還沒滿就 saturate」的答案就在這條曲線。autoscaler 的 target metric 通常訂在 60-70%、是 queueing theory 推導出的安全邊界、不是工程師憑感覺。

多 server 模型（M/M/c）比單 server（M/M/1）有顯著容量優勢：c 個 server 的有效容量遠超 1 個 server 容量 × c。這也解釋了為什麼水平擴容（多開幾個 instance）通常比垂直擴容（單機加 CPU）划算 — 不只是規模、是 queue 行為的本質差異。

對應案例：[GR8 Tech 25ms p95](/backend/09-performance-capacity/cases/gr8-tech-ai-predicted-betting-peak/) 把 p95 維持在 25ms 同時撐 54K TPS、靠的是 *永遠不讓系統進入 knee*、AI 預測讓擴容窗口縮短到 reaction time 內。

## Universal Scalability Law：擴容會邊際失效

USL（Neil Gunther 提出）的公式 throughput(N) = N / (1 + α(N-1) + βN(N-1)) 解釋了「為什麼加機器到某個點之後 throughput 反而下降」。兩個常數 α 跟 β 描述系統的擴展限制：

- α 是必須序列化的部分（Amdahl's Law 的對應）。distributed lock、coordinator、單一 leader DB 都是 α 來源。α 越大、線性擴容越早 plateau。
- β 是節點間互相通訊的成本（crosstalk）。cache invalidation broadcast、consensus [quorum](/backend/knowledge-cards/quorum/)、cross-region replication 都是 β。β 比 α 更危險、會讓 throughput 在 N 大到某點後 *反向下降*。

工程上 α 比較好處理 — 把序列化部分拆細、用 partition 切分、用 sharded coordinator。β 比較難 — 通訊本質就需要協調、降低 β 通常要重新設計分散式協議（例如 Spanner 用 TrueTime 把跨節點交易的協調成本降低）。

對應案例：[Spanner 線性擴展到 10 億 req/sec](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/) — TrueTime API 讓跨地區交易的 β 降到可接受、達成傳統 OLTP 做不到的線性；[Coinbase RAFT consensus](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — RAFT 的 quorum 通訊讓 β 不可降、所以 *選擇不橫向擴*、改用 z1d + Cluster Placement Group 榨單機。

詳見 [USL 卡片](/backend/knowledge-cards/universal-scalability-law/)。

## Saturation Curve：linear → knee → cliff

實際系統的 latency vs throughput 曲線分三段。第一段是 linear region — utilization 低、latency 平穩、加流量幾乎不影響 latency。第二段是 knee — utilization 接近 80%、latency 開始指數成長、再加流量會明顯變慢。第三段是 cliff — 系統進入不穩定區、latency 不可預測、可能 timeout、可能 cascade failure。

容量規劃的關鍵概念是 *knee point = 設計容量上限*。健康系統運轉在 knee 以下 50-70%、留出 headroom 應付 burst 跟 forecast 誤差。沒有量過 knee 的系統等於「不知道距離崩潰多遠」 — 平日看起來穩、實際隨時可能因為一個小 spike 進入 cliff。

不同 system 的 knee 位置差異很大。stateless service 通常 knee 在 80% CPU；DB 因為 lock contention、knee 可能在 60% utilization；broker / queue 因為 disk I/O bottleneck、knee 可能在 50%。容量規劃時不能一概而論、必須個別量測。

每次重大改動後必須 re-test knee。新增功能、改 ORM、升級 library、調 GC tuning、改 cache 策略 — 任何一個都可能讓 knee 往不好的方向移。

對應案例：[Tixcraft DynamoDB IOPS 20 → 135K](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — partition 設計均勻時 saturation point 可以推到極遠（6750x 擴展）；[Amazon Ads 9000 萬 RPS](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — 線性擴展靠 partition key 均勻、不靠 vendor 神話。

詳見 [Saturation Point 卡片](/backend/knowledge-cards/saturation-point/)。

## 反推：從業務 KPI 到系統參數

理論工具的真正價值在「反推」 — 不是先設計系統再量測 saturate 多少、是 *先訂業務目標再反推系統參數*。這層思維把容量規劃從 reactive（撐到撐不住才擴）變成 proactive（按業務需求預先配置）。

反推流程通常從 latency budget 開始（詳見 [9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)）：

1. 從 user-perceived end-to-end latency（例如 p99 500ms）開始
2. 拆到每個 stage（網路、CDN、application、cache、DB、第三方）的 latency 配額
3. 配額決定每個 stage 的設計選擇 — DB 配 50ms → 不能跨 region、application 配 100ms → 不能多層 microservice hop
4. 配額 + 預期 RPS → Little's Law 算每個 stage 的並發
5. 並發 → 每個 stage 的容量需求 → 實例數 / connection pool size / cache size

反推失敗的常見徵兆：算出來的某個 stage 容量超過 vendor 提供的上限（例如「需要 50 萬 DynamoDB RCU」可能超過單一 table partition 上限）、或某個 stage latency 配額過短（例如 cross-AZ 網路至少 1-2ms、配 0.5ms 不可能達成）。這時要回頭調整 SLO 或重新設計架構。

詳見 [Latency Budget 卡片](/backend/knowledge-cards/latency-budget/)。

## 案例對照

| 案例                                                                                              | 教學重點                            |
| ------------------------------------------------------------------------------------------------- | ----------------------------------- |
| [9.C3 Coinbase](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) | sub-ms latency 反推所有架構選擇     |
| [9.C10 Spanner](/backend/09-performance-capacity/cases/spanner-planetary-scale-database-gcp/)     | TrueTime 降低 β 達成線性擴展        |
| [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)           | ML p99 < 10ms 的 stage latency 配額 |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)         | 線性擴展靠 partition 均勻、不靠魔法 |

## 下一步路由

- 下游：[9.2 Workload Modeling](/backend/09-performance-capacity/workload-modeling/)（把模型量化成 production traffic）
- 下游：[9.4 Saturation Discovery](/backend/09-performance-capacity/saturation-discovery/)（實測 knee point）
- 跨章節：[9.12 SLO 與 Performance Budget](/backend/09-performance-capacity/slo-performance-budget/)（latency budget 拆解）

## 既建知識卡片

- [Little's Law](/backend/knowledge-cards/little-law/)
- [Universal Scalability Law](/backend/knowledge-cards/universal-scalability-law/)
- [Saturation Point](/backend/knowledge-cards/saturation-point/)
- [Latency Budget](/backend/knowledge-cards/latency-budget/)
- [Tail Latency](/backend/knowledge-cards/tail-latency/)
