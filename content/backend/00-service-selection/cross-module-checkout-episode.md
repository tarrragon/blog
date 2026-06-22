---
title: "0.15 跨模組 Checkout Episode：從資料寫入到觀測證據"
date: 2026-06-22
description: "以 checkout 為切片，走完 DB write → cache invalidation → event publish → observability evidence 四層串聯，標示各模組的交接欄位與失敗判讀"
weight: 15
tags: ["backend", "service-selection", "cross-module", "checkout"]
---

跨模組 checkout episode 的核心責任是用同一條服務路徑，把資料庫、快取、訊息佇列與可觀測性四個模組的責任串在一起。讀者看完後能判斷一次 checkout 請求觸發的狀態寫入、快取失效、事件發布與訊號記錄分別由誰負責，以及任何一層失敗時該看哪組訊號。

本篇與 [0.13 操作控制 vertical slice](/backend/00-service-selection/operations-control-vertical-slice/) 互補：0.13 走的是 04/06/08 的操作控制閉環（觀測 → 驗證 → 事故 → 回寫），本篇走的是 01/02/03/04 的資料基礎設施鏈（狀態 → 副本 → 事件 → 訊號）。

## 服務路徑

一次 checkout 的最小路徑：

```text
client
  → checkout-api
    → order-db          (01: 寫入正式狀態)
    → cache invalidation (02: 失效商品快取)
    → event publish      (03: 發布 order.created 事件)
    → telemetry          (04: span / log / metric 記錄)
```

這條路徑刻意簡化。真實系統可能還有 payment adapter、inventory lock、notification service、search index sync 等環節，但四層串聯的責任分工用最小路徑就能說明。後續章節把各層展開。

## 第一層：資料庫寫入（01）

Checkout 的正式狀態是訂單紀錄。這筆寫入必須在 [transaction boundary](/backend/01-database/transaction-boundary/) 內完成，確保訂單、明細與付款紀錄一起成功或一起失敗。

**責任邊界**：

- 訂單狀態是 [source of truth](/backend/knowledge-cards/source-of-truth/)，快取和事件都是下游副本
- Transaction 範圍盡量小：寫入訂單 + 明細 + outbox record，不在同一個 transaction 裡做外部 API 呼叫
- Schema 需要支援狀態演進：訂單從 `pending` → `paid` → `shipped` 的欄位設計見 [1.7 schema migration rollout evidence](/backend/01-database/schema-migration-rollout-evidence/)

**失敗判讀**：

| 失敗訊號              | 判讀                              | 下一步                                                                                                   |
| --------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Transaction timeout   | 連線池飽和或長 transaction 鎖等待 | 回 [1.1 高併發讀寫邊界](/backend/01-database/high-concurrency-access/) 檢查連線池與 transaction 範圍     |
| Deadlock              | 多個 checkout 同時更新重疊資源    | 回 [1.3 transaction boundary](/backend/01-database/transaction-boundary/) 檢查 lock ordering             |
| Schema migration 中斷 | 欄位變更與正在執行的寫入衝突      | 回 [1.6 migration playbook](/backend/01-database/database-migration-playbook/) 確認 expand/contract 流程 |

**交接給下一層的資訊**：transaction commit 成功後，訂單 ID 與狀態就緒。Outbox record 已寫入同一個 transaction。

## 第二層：快取失效（02）

訂單成功後，商品庫存或價格的快取副本可能已經過期。快取失效的責任是讓後續讀取拿到正確狀態，同時保護資料庫不被回源壓力打穿。

**責任邊界**：

- 快取是 [可重建副本](/backend/02-cache-redis/cache-copy-freshness-boundary/)，資料來源是資料庫的正式狀態。失效後的 cache miss 會回源到資料庫
- 失效策略用 [cache aside](/backend/02-cache-redis/cache-aside/)：寫入後主動 invalidate，下次讀取時 lazy reload
- Invalidation 的順序：先 invalidate 應用層快取（Redis），再考慮是否需要 purge CDN 層（若商品頁有 edge cache）

**失敗判讀**：

| 失敗訊號                         | 判讀                                            | 下一步                                                                                                                         |
| -------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Invalidation 失敗但 DB 已 commit | 快取短暫提供舊資料，freshness window 內自動修正 | 確認 [TTL](/backend/02-cache-redis/ttl-eviction/) 是否足夠短，或補 retry                                                       |
| Cache stampede                   | 大量 invalidation 同時觸發 origin 回源          | 回 [2.9 cache migration stampede rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/) 補 singleflight 或 lock |
| Hot key 集中失效                 | 單一商品被大量並發 checkout 同時 invalidate     | 回 [2.1 高併發讀寫邊界](/backend/02-cache-redis/high-concurrency-access/) 檢查 hot key 分散策略                                |

**交接給下一層的資訊**：快取失效完成（或 TTL 保底）。接下來的事件發布不依賴快取狀態 — 事件內容來自 DB 寫入結果。

## 第三層：事件發布（03）

訂單寫入後，`order.created` 事件需要傳遞到下游：通知服務寄信、庫存服務更新、搜尋索引同步、分析管道記錄。這些下游不在 checkout request 內完成，要用非同步傳遞。

**責任邊界**：

- 事件發布與 DB 寫入的一致性用 [outbox pattern](/backend/03-message-queue/outbox-pattern/)：outbox record 在 DB transaction 內寫入，poller 或 CDC 負責把 record 發到 broker
- Broker 保證 [at-least-once delivery](/backend/knowledge-cards/delivery-semantics/)，consumer 需要做 [idempotency](/backend/knowledge-cards/idempotency/) 處理
- Event contract（schema、idempotency key、replay window）見 [3.7 event contract replay boundary](/backend/03-message-queue/event-contract-replay-boundary/)

**失敗判讀**：

| 失敗訊號                   | 判讀                                    | 下一步                                                                                                               |
| -------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Outbox poller 延遲         | 事件延遲但不遺失，DB 已 commit          | 監控 outbox table 的 pending row count，回 [3.3 outbox pattern](/backend/03-message-queue/outbox-pattern/)           |
| Consumer lag 上升          | 下游處理速度跟不上，事件在 broker 堆積  | 回 [3.4 consumer design](/backend/03-message-queue/consumer-design/) 檢查 consumer 數量與 backpressure               |
| DLQ 堆積                   | 毒訊息或下游持續失敗，已超過 retry 預算 | 回 [3.8 retry replay handoff](/backend/03-message-queue/queue-consumer-retry-replay-handoff/) 啟動 DLQ drain runbook |
| 重複事件造成下游重複副作用 | Consumer idempotency 沒擋住             | 回 [3.6 processing recovery semantics](/backend/03-message-queue/processing-recovery-semantics/) 確認去重機制        |

**交接給下一層的資訊**：事件已發到 broker，每一步（publish、ack、consume、DLQ）都需要觀測訊號。

## 第四層：觀測訊號（04）

以上三層的每一步都需要被記錄成可查詢的訊號。Checkout 路徑的觀測責任是讓事故判讀者能用同一組 trace ID 串起完整鏈路。

**責任邊界**：

- [Trace context](/backend/04-observability/tracing-context/) 從 client 一路 propagate 到 consumer，跨 sync（HTTP）與 async（queue）邊界
- [Log schema](/backend/04-observability/log-schema/) 使用統一欄位：`order_id`、`trace_id`、`tenant_id`、`region`
- [Metrics](/backend/04-observability/metrics-basics/) 覆蓋三組 SLI：checkout latency（p50/p95/p99）、checkout error rate、event publish lag
- [Dashboard](/backend/04-observability/dashboard-alert/) 把上述三組 SLI 放在同一個 checkout 服務面板
- [Evidence package](/backend/04-observability/checkout-api-evidence-package/) 把查詢、時間窗、資料品質與 owner 打包成可交接證據

**失敗判讀**：

| 失敗訊號                       | 判讀                                                 | 下一步                                                                                             |
| ------------------------------ | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Trace 在 DB commit 後斷鏈      | Context propagation 沒跨到 async 邊界                | 回 [4.3 tracing context](/backend/04-observability/tracing-context/) 補 queue span link            |
| Checkout metric 正常但客訴增加 | 觀測盲區或 sampling 偏差                             | 回 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/) 標示 known gap |
| Alert 太吵但真正事件沒被抓到   | 告警粒度與閾值設計問題                               | 回 [4.4 dashboard alert](/backend/04-observability/dashboard-alert/) 調整 symptom-based alert      |
| 訊號延遲導致事故判讀困難       | Pipeline ingest delay 或 metric scrape interval 太長 | 回 [4.11 telemetry pipeline](/backend/04-observability/telemetry-pipeline/) 檢查 pipeline 健康     |

## 四層交接總覽

```text
┌─────────────┐    commit     ┌──────────────┐
│  01 DB      │──────────────→│  02 Cache    │
│  order-db   │    ok         │  invalidate  │
│  write      │               │  product key │
└──────┬──────┘               └──────────────┘
       │ outbox
       │ record
       ▼
┌─────────────┐
│  03 Event   │
│  publish    │
│  order.     │
│  created    │
└─────────────┘
       │
       │ all layers emit
       ▼
┌──────────────────────────┐
│  04 Observability        │
│  span + log + metric     │
│  per layer               │
└──────────────────────────┘
```

每一層都有明確的失敗判讀與交接資訊。四層合在一起的判讀順序是：先看 04 的 trace 確認斷點在哪一層，再進那一層的失敗訊號表。

## 跨層失敗場景

單層失敗表只處理各自的責任。跨層失敗需要同時看多組訊號：

### DB commit 成功，但快取沒失效且事件沒發出

原因通常是 outbox poller 和 cache invalidation 在同一個 request 內串行、前者失敗後沒做到後者。判讀順序：

1. 04 的 trace 看 checkout span 是否有 error tag
2. 01 的 outbox table 看 pending row 是否堆積
3. 02 的 cache key 是否仍是舊值（TTL 保底正常時可接受）

修正方向：invalidation 和 outbox 解耦 — invalidation 在 DB commit 後同步執行（失敗可 retry），outbox 非同步由 poller 負責。兩者不應互相阻塞。

### Event consumer 重複處理造成庫存扣兩次

原因是 consumer 的 idempotency 沒做好，broker redelivery 導致重複副作用。判讀順序：

1. 04 的 consumer span 看 redelivery count
2. 03 的 DLQ 看是否有 poison message
3. 01 的 inventory table 看同一 order_id 是否有多筆扣減

修正方向：回 [3.4 consumer design](/backend/03-message-queue/consumer-design/) 補 idempotency key 驗證，用 order_id 當去重鍵。

### Checkout latency 上升但 DB 和 cache 都正常

原因可能是 outbox poller 或 event publish 在 request path 內同步等待（設計錯誤）。判讀順序：

1. 04 的 checkout span 看 child span 時間分布
2. 確認 event publish 是否在 request 返回前完成（不該）
3. 如果是，回到 03 確認 outbox pattern 是否正確實作（寫 outbox record 應在 DB transaction 內、publish 應由 poller 異步執行）

## 各模組回讀路由

| 層               | 主要回讀章節                                                                                                                                                                                                                           | 回讀時機                             |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 01 DB            | [1.1](/backend/01-database/high-concurrency-access/)、[1.3](/backend/01-database/transaction-boundary/)、[1.6](/backend/01-database/database-migration-playbook/)、[1.7](/backend/01-database/schema-migration-rollout-evidence/)      | transaction 或 schema 問題           |
| 02 Cache         | [2.1](/backend/02-cache-redis/high-concurrency-access/)、[2.2](/backend/02-cache-redis/cache-aside/)、[2.7](/backend/02-cache-redis/cache-copy-freshness-boundary/)、[2.9](/backend/02-cache-redis/cache-migration-stampede-rollback/) | invalidation 或 stampede 問題        |
| 03 Event         | [3.3](/backend/03-message-queue/outbox-pattern/)、[3.4](/backend/03-message-queue/consumer-design/)、[3.6](/backend/03-message-queue/processing-recovery-semantics/)、[3.7](/backend/03-message-queue/event-contract-replay-boundary/) | delivery、idempotency 或 replay 問題 |
| 04 Observability | [4.3](/backend/04-observability/tracing-context/)、[4.4](/backend/04-observability/dashboard-alert/)、[4.17](/backend/04-observability/telemetry-data-quality/)、[4.22](/backend/04-observability/checkout-api-evidence-package/)      | 訊號斷鏈、盲區或 evidence 問題       |
| 操作閉環         | [0.13](/backend/00-service-selection/operations-control-vertical-slice/)                                                                                                                                                               | 從訊號進入驗證、事故與回寫流程       |

## 使用方式

本篇是索引型讀物。讀者第一次讀時順著四層走一遍，建立跨模組的交接心智模型。之後遇到具體問題時，用失敗訊號表定位到對應模組的章節。

已經有某一層經驗的讀者可以從那一層開始讀，看該層與相鄰層的交接欄位是否對齊。資料庫工程師從第一層開始看事件發布的交接；觀測工程師從第四層反推前三層需要哪些欄位。

本篇不處理 payment adapter、inventory lock、notification 等更複雜的分支。這些分支的模式相同 — 確認責任邊界、交接欄位與失敗判讀 — 讀者可以自行延伸。
