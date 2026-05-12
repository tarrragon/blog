---
title: "9.4 Saturation Discovery"
date: 2026-05-12
description: "找出 throughput plateau 與 latency knee 的方法"
weight: 4
tags: ["backend", "performance", "capacity", "saturation"]
---

## 概念定位

Saturation discovery 的責任是把「系統能撐多少」這個問題變成可量化答案。沒有 saturation 量測時、容量規劃只能猜；有 saturation 量測之後、能說「在當前配置下、p99 < 100ms 的條件下、能撐 X RPS、headroom Y%」。

跟 [9.1 壓測理論](/backend/09-performance-capacity/performance-theory/) 的關係：9.1 預測 saturation curve 的形狀（linear → knee → cliff）、9.4 用實測找出 *本服務* 的曲線具體位置。理論告訴我們 knee 存在、實測告訴我們它在哪裡。

本章不深入工具操作（[9.3](/backend/09-performance-capacity/load-test-tooling/) 處理工具）、聚焦在 *方法論* — 怎麼設計 ramp-up、怎麼判斷 knee、怎麼把結果文件化讓後續決策可用。

## Saturation 的精確定義

容量規劃裡 saturation 不是「系統當機」、是「系統 *進入 latency 指數成長區*」。這個區分很重要 — 系統 *看起來* 還在跑、其實已經不可預測。

技術上 saturation 對應 [queueing theory 的 knee point](/backend/knowledge-cards/saturation-point/)：utilization 超過某個臨界（M/M/c 通常 70-80%）、平均 queue length 從線性轉成指數成長。latency 是 queue length 的線性函數、所以也跟著指數成長。

實務上把 saturation 分三段：

- **linear region**（utilization < 50%）：latency 平穩、加流量幾乎不影響
- **knee region**（utilization 50-80%）：latency 開始上升、但還可接受
- **cliff region**（utilization > 80%）：latency 不可預測、可能 timeout / cascade failure

健康系統運轉在 linear 後半段或 knee 前段（utilization 50-70%）、留出 headroom 應付 burst。autoscaler 的 target metric 通常訂在 60-70%、是這條曲線推導出的安全位置。

## Ramp-up 測試方法

要找出 saturation 點、必須跑 *ramp-up 測試* — 不能固定一個壓力值。

**單點壓測的問題**：跑「2000 RPS 連續 10 分鐘」、看 latency 100ms、結論「能撐 2000 RPS」 — 但不知道 1500 跟 2500 RPS 是什麼樣。可能 1500 也是 100ms（離 knee 還很遠）、可能 2500 直接崩（已經在 cliff）。

**Ramp-up 流程**：從基線開始、按倍數加壓（1x / 2x / 4x / 8x ...）。每個壓力 level 維持 5-10 分鐘、觀察 latency / throughput / resource utilization 的穩態（不是 transient）。紀錄每個 level 的 percentile 分布。

**Knee 出現的訊號**：

- throughput 從線性成長轉成 sub-linear（加壓但 throughput 不再等比成長）
- latency p50 還算穩、但 p99 / p999 開始飆
- resource saturation queue 開始堆積（不只 utilization 上升）
- error rate 仍接近 0（cliff 才會 error 飆）

**Cliff 出現的訊號**：throughput 開始下降（加壓反而越來越慢）、latency p99 變成 timeout、error rate 飆升、retry storm 出現。

對應案例：[Tixcraft 用 10K t2.micro 壓測](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 找 DynamoDB 從 20 IOPS 到 135K 的擴展曲線、知道 knee 在哪。

## Resource saturation 的六個維度

每次 ramp-up 都要同時觀察六個維度的 resource saturation、找出哪個 *先 saturate*。

**CPU**：utilization 100% *不一定* 等於 saturation。要看 load average 跟 run queue。utilization 80% 但 run queue 不斷增長 → 已 saturate；utilization 100% 但 run queue 空 → 還能撐（單純 CPU bound）。

**Memory**：not OOM 即可？不夠。GC pause（Java、Go）、swap（Linux）、cache eviction 都是隱性 saturation。記憶體不直接 OOM 但 GC 飆 → 已影響 [tail latency](/backend/knowledge-cards/tail-latency/)。

**Disk I/O**：要看三個維度：throughput（MB/s）、IOPS（operations/sec）、queue depth。雲端 SSD 通常先 IOPS bound、不是 throughput；本機 NVMe 可能先 throughput bound。

**Network**：bandwidth（Gbps）、packets per second、connection count。雲端 instance 通常有 PPS limit、超過會 silent drop、不是顯式錯誤。

**Connection pool**：DB / cache / external API 的連線數。這是 *最常見的隱性 bottleneck*。pool size 訂 100、實際在用 95 → utilization 看似還好、其實已經 saturate（剩下的 request 在等 connection）。

**External API quota**：第三方 rate limit（Stripe、Twilio、Slack API）。這個維度的 saturation 看不到 *本系統* 的訊號、要看 *對方 API 的 429 error rate*。

對應案例：[Lemino RDB connection limit](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/) — connection 是 RDB 的 saturation 點、CPU 跟 RAM 都還沒到。

詳見 [USE Method 卡片](/backend/knowledge-cards/use-method/)。

## Hot partition 的隱性 saturation

對分散式 KV / OLTP（DynamoDB、Cosmos DB、Bigtable、Cassandra）、saturation 還有另一個維度：[hot partition](/backend/knowledge-cards/hot-partition/)。

名義容量 = 每 partition 上限 × partition 數量。partition key 分布不均 → 名義容量達不到。整體 utilization 看起來 20% → 系統還能撐？不一定。最熱 partition 已經 100%、其他 partition 0%、整體平均才 20%、但加流量會打在最熱 partition、立即 throttle。

**識別 hot partition 的訊號**：

- throughput 上不去、但 average resource utilization 低
- 某些 key 的 request latency 飆、其他 key 正常
- DynamoDB throttling event 出現（即使 capacity 還沒滿）

**處理方法**：

- composite key（event_id + user_id_hash）
- write sharding（event_id + random_suffix）
- time-bucket（event_id + minute）
- 用 cache 吸收 hot key（DAX、ElastiCache）

對應案例：[Amazon Ads 9000 萬 RPS](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/) — partition 設計均勻時可以撐 sustained 高吞吐；[Tixcraft 售票](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) — 同一場演唱會（event_id）天然容易 hot、必須用 composite key 分散。

## Long-tail latency 的 saturation

p50 / p95 / p99 / p999 在 saturate 時表現可能完全不同。

p50（中位數）對 GC pause、retry storm、tail latency 不敏感 — 大部分 request 沒事、p50 看不到。
p99（百分之 1）對 connection contention 開始敏感、能早期看到 saturation。
p999（千分之 1）對 GC stop-the-world、leader election、retry storm 敏感、是長尾的最強訊號。

純看 average / p50 會誤判 saturation 還沒到。SLO 通常訂 p99（讓 99% 用戶體驗良好）、internal critical 系統可訂 p99.9（5 個 9 的可用性對應 5 個 9 的 latency 期待）。

對應案例：[Tubi p99 < 10ms](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/) — ML 系統的 user-perceived latency 是 *最後完成的 inference*、p50 快沒用；[Coinbase sub-ms](/backend/09-performance-capacity/cases/coinbase-ultra-low-latency-exchange-2023/) — RAFT 系統的 p999 通常比 p99 高一個量級。

詳見 [Tail Latency 卡片](/backend/knowledge-cards/tail-latency/)。

## Saturation 文件化：容量地圖

Saturation discovery 跑完之後、產出 *容量地圖* — 不是一個數字、是一張表。

容量地圖至少要回答：

- 在 X 配置下（instance count、type、network）
- SLO 條件 Y 下（p99 < N ms、error rate < M%）
- 能撐 Z RPS（含分解到不同 endpoint）
- knee 在哪（什麼條件下進入 cliff）
- 第一個 saturate 的 resource 是什麼

紀錄 *測試時間* 跟 *軟硬體版本*：硬體 / 軟體版本變動後、saturation 點可能位移、舊地圖不能套用。

加入 release gate：每次重大改動後 re-test、確認 knee 沒往不好的方向移。這層自動化跟 [9.9 Improvement Loop](/backend/09-performance-capacity/improvement-loop/) 對接。

## 案例對照

| 案例                                                                                          | 教學重點                                 |
| --------------------------------------------------------------------------------------------- | ---------------------------------------- |
| [9.C15 Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) | DynamoDB IOPS 20 → 135K 的擴展曲線量測   |
| [9.C5 Amazon Ads](/backend/09-performance-capacity/cases/amazon-ads-dynamodb-extreme-kv/)     | partition 均勻時的線性擴展               |
| [9.C29 Lemino](/backend/09-performance-capacity/cases/ntt-docomo-lemino-japanese-streaming/)  | connection limit 是 RDB 的 saturation 點 |
| [9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)       | p99 < 10ms saturation 條件比平均嚴格     |

## 下一步路由

- 上游：[9.1 壓測理論](/backend/09-performance-capacity/performance-theory/) / [9.3 壓測工具選型](/backend/09-performance-capacity/load-test-tooling/)
- 下游：[9.5 瓶頸定位流程](/backend/09-performance-capacity/bottleneck-localization/)（找到 knee 之後、定位是哪個 resource）
- 下游：[9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/)（用 knee 算 headroom）
- 跨模組：[04 可觀測性模組](/backend/04-observability/)（量測訊號）

## 既建知識卡片

- [Saturation Point](/backend/knowledge-cards/saturation-point/)
- [USE Method](/backend/knowledge-cards/use-method/)
- [Tail Latency](/backend/knowledge-cards/tail-latency/)
- [Hot Partition](/backend/knowledge-cards/hot-partition/)
