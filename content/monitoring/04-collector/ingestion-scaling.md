---
title: "Ingestion Scaling"
date: 2026-06-20
description: "四層防線應對 ingestion 端的流量擴展 — SDK 取樣、Collector 背壓、水平擴展、Queue 解耦"
weight: 11
tags: ["monitoring", "collector", "scaling", "ingestion", "backpressure", "rate-limit"]
---

Ingestion scaling 處理的是「大量事件同時湧入 collector 時怎麼辦」。這和 storage scaling（[SQLite → PostgreSQL 的可插拔 backend](/monitoring/04-collector/scaling-evolution/)）是兩個獨立的擴展軸 — storage scaling 解決「查得動嗎」，ingestion scaling 解決「收得下嗎」。一個 collector 可能 storage 用 PostgreSQL（查詢能力足夠）但 ingestion 撐不住（HTTP 請求太多），反之亦然。

## 四層防線

每一層在不同規模觸發，由近到遠依序啟用。前一層能擋住的流量不需要啟用後一層。本章的四層按防線位置劃分（SDK / Collector / 基礎設施兩層）。DevOps 的[規模分級應對表](/devops/07-burst-traffic/scale-tier-response/)按 events/sec 量級劃分（Tier 1-4），兩者視角不同但覆蓋相同的擴展路徑。

| 層  | 機制                            | 在哪裡做  | 觸發條件                                | 適用規模    |
| --- | ------------------------------- | --------- | --------------------------------------- | ----------- |
| 一  | SDK 端取樣 + 聚合前移           | SDK       | 高頻事件超過合理粒度                    | 所有規模    |
| 二  | Collector 單機背壓 + rate limit | Collector | 寫入 channel 接近滿載                   | 自用 ~ 小型 |
| 三  | 水平擴展（多 collector + LB）   | 基礎設施  | 單機 CPU / 連線數飽和                   | 中型 ~ 大型 |
| 四  | Queue 解耦（Kafka / NATS）      | 基礎設施  | 突發流量超過 collector 群的即時處理能力 | 商業網站級  |

## 第一層：SDK 端的流量控制

流量控制的最有效位置是事件產生的源頭。SDK 端減少的事件量，後面每一層都不需要處理。

### 動態取樣

SDK 在收到 collector 的 HTTP 429（Too Many Requests）回應時，自動降低取樣率。恢復正常後逐步回升。

```text
正常 → sampling 1.0
收到 429 → sampling 降到 0.5
持續 429 → sampling 降到 0.1
連續 10 次成功 → sampling 回升到 0.5
連續 30 次成功 → sampling 回到 1.0
```

動態取樣的控制邏輯在 SDK 端實作，不需要 collector 端額外支援 — 429 回應碼就是觸發訊號。和[感測器生命週期管理](/monitoring/03-sdk-design/sensor-lifecycle-management/)的靜態取樣率互補 — 靜態取樣在 config 中設定、動態取樣在執行期自動調整。

### 聚合前移

SDK 端累積一段時間的同名事件，送出摘要而非逐筆。適合 metric 類的高頻取樣。

例：原本每 100ms 送一筆 `render.frame_drop`，改成每 5 秒送一筆 `render.frame_drop_summary`（帶 count + min + max + avg）。事件數從 50 筆/5s 降到 1 筆/5s。

聚合前移犧牲事件粒度換取吞吐量。只適合「趨勢比每筆細節重要」的 metric 類事件。Error 和 lifecycle 事件不做聚合 — 每筆的 stack trace 和狀態轉換都有 debug 價值。

### 優先級丟棄

SDK 的離線 buffer 滿時，按優先級丟棄。Error 的 debug 價值最高，最後丟。

| 優先級 | 事件類型  | 理由                                         |
| ------ | --------- | -------------------------------------------- |
| 高     | error     | 每筆都可能是需要修的 bug                     |
| 高     | lifecycle | session 邊界和狀態轉換、影響 debug 和 cohort |
| 中     | metric    | 丟幾筆不影響趨勢（聚合摘要仍然有效）         |
| 低     | event     | 行為事件在取樣後丟幾筆對 funnel 影響有限     |

## 第二層：Collector 單機的防護

Collector 在自身能力範圍內保護自己不被壓垮。和 [architecture.md 的並發寫入策略](/monitoring/04-collector/architecture/)直接相關 — 寫入 channel 是背壓的實作基礎。背壓和流量管控的通用概念見 [DevOps 流量管控](/devops/03-traffic-management/)。

### 寫入 channel 容量 + 背壓

Single-writer goroutine pattern 的 Go channel 有固定容量（如 10,000）。Channel 滿時 HTTP handler 無法送入事件，此時回 429：

```go
select {
case writeCh <- event:
    w.WriteHeader(http.StatusAccepted) // 202
default:
    w.Header().Set("Retry-After", "5")
    w.WriteHeader(http.StatusTooManyRequests) // 429
}
```

Channel 容量的設定依據：容量 × 每筆事件的記憶體大小 = 背壓 buffer 的記憶體上限。10,000 筆 × 每筆 ~1KB = ~10MB，對多數機器微不足道。

### Per-SDK rate limiting

按 source.app（或 API key，啟用認證後）限制每個 SDK 實例的請求速率。防止單一 SDK 的 bug（無限迴圈送事件）打爆 collector。

```go
// 每個 source.app 一個 rate limiter
limiter := rateLimiters.GetOrCreate(sourceApp, rate.Limit(100)) // 100 events/sec
if !limiter.Allow() {
    w.WriteHeader(http.StatusTooManyRequests)
    return
}
```

### Error 快通道

Error 事件不經 rate limit — 它們的 debug 價值最高，且在正常情況下數量遠少於其他類型。Error storm（app 出 bug 導致大量 error）時，error 的量可能暴增，但這正是最需要記錄的時刻。

Error 快通道用獨立的 channel 或跳過 rate limiter 的 check。如果 error 量也超出承載，用第一層的 SDK 端優先級丟棄處理。

## 第三層：水平擴展

單機的 CPU、記憶體或網路頻寬飽和時，水平擴展 — 多個 collector 實例分攤流量。水平擴展的通用模式見 [DevOps 水平擴展](/devops/02-horizontal-scaling/)。

### 前提：已切換到 PostgreSQL

SQLite backend 不支援水平擴展。每個 collector 實例有各自的 SQLite 檔案，無法合併查詢。水平擴展的前提是所有 collector 寫入同一個 PostgreSQL。

### 架構

```text
SDK ──→ Load Balancer (nginx / HAProxy)
             │
        ┌────┴────┐
        ▼         ▼
   Collector A  Collector B
        │         │
        └────┬────┘
             ▼
        PostgreSQL
             │
             ▼
         Dashboard
```

Collector 實例是 stateless 的 — 不在記憶體保存查詢狀態，所有持久化資料在 PostgreSQL。任何 collector 接收的事件都能被任何 dashboard 查到。

Load balancer 用 round-robin 或 least-connections 分配。不需要 sticky session — collector 不保存 session 狀態。

### 多機的 Downsample 和 Purge

Downsample 和 Purge job 只能由一個 collector 實例執行（避免重複處理）。用 PostgreSQL 的 advisory lock 或外部的 distributed lock 確保單一執行者。

## 第四層：Queue 解耦

突發流量超過 collector 群的即時處理能力時，在 collector 和 storage 之間插入 message queue 做緩衝。Queue 緩衝的通用概念見 [DevOps 突發流量應對](/devops/07-burst-traffic/)，message queue 的選型見 [Backend 模組三 非同步與訊息佇列](/backend/03-message-queue/)。

### 架構

```text
SDK ──→ Collector (ingestion only)
             │
             ▼
        Queue (Kafka / NATS / Redis Streams)
             │
        ┌────┴────┐
        ▼         ▼
    Worker A   Worker B
        │         │
        └────┬────┘
             ▼
        PostgreSQL
```

Collector 的職責簡化為「接收 → 驗證 → 寫入 queue → 回 202」。寫入 queue 比寫入 DB 快得多（append-only、不需要索引更新），collector 的吞吐上限大幅提升。

Worker 從 queue 消費、寫入 PostgreSQL。Worker 按自己的速度處理 — 高峰時 queue 積壓，高峰過後 worker 消化積壓。Queue 的持久化保證事件不遺失。

### Queue 的選擇

| Queue          | 適合場景                               | 代價                               |
| -------------- | -------------------------------------- | ---------------------------------- |
| Kafka          | 高吞吐（百萬 events/sec）、需要 replay | 運維重（ZooKeeper / KRaft）        |
| NATS JetStream | 輕量、Go 原生、足夠的持久化            | 生態較小                           |
| Redis Streams  | 簡單、如果已有 Redis                   | 不是專門的 queue、持久化設定需注意 |

自架監控工具的 queue 層級推薦 NATS JetStream — Go 原生 client、單 binary 部署、JetStream 提供持久化和 replay。

### 觸發條件

Queue 解耦的引入時機是「collector 群已水平擴展但仍無法處理突發流量」。如果日常流量 collector 群能處理，只有行銷活動 / 新聞曝光的短暫高峰需要 queue 緩衝，queue 的維護成本可能高於收益 — 考慮用第一層的動態取樣在源頭降量。

## 功能分層整合

擴展 [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/) 的分層表，加入 ingestion 維度：

| 功能層級      | Storage         | Ingestion                  | 適用規模        |
| ------------- | --------------- | -------------------------- | --------------- |
| SQLite 層     | SQLite embedded | 單 collector + 背壓        | 自用 ~ 小型團隊 |
| PostgreSQL 層 | PostgreSQL      | 多 collector + LB          | 中型 ~ 大型     |
| Queue 層      | PostgreSQL      | Collector + Queue + Worker | 商業網站級      |

每一層是前一層的超集 — Queue 層包含 PostgreSQL 層的所有查詢能力，加上 ingestion 的 queue 緩衝。

## 下一步路由

- Collector 的並發寫入策略 → [Collector 架構](/monitoring/04-collector/architecture/)
- Storage 端的擴展設計 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- 功能分層的定義 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- 背壓和流量管控的通用概念 → [DevOps 流量管控](/devops/03-traffic-management/)
- 水平擴展的通用模式 → [DevOps 水平擴展](/devops/02-horizontal-scaling/)
- 突發流量應對 → [DevOps 突發流量](/devops/07-burst-traffic/)
- Message queue 選型 → [Backend 模組三 非同步與訊息佇列](/backend/03-message-queue/)
