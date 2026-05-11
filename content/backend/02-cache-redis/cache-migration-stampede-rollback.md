---
title: "2.9 Cache Migration 與 Stampede Rollback（實作示範）"
date: 2026-05-11
description: "以商品詳情與價格快取示範 cache migration 如何交付 evidence package、release gate 與 incident decision log。"
weight: 9
tags: ["backend", "cache", "redis", "implementation", "evidence-package"]
---

Cache migration 與 stampede rollback 的核心責任是讓快取副本在格式、鍵名與覆蓋範圍演進時，仍能保護 [source of truth](/backend/knowledge-cards/source-of-truth/) 不被回源流量打穿。這篇以商品詳情與價格快取為例，示範如何把 key schema 演進、freshness 控制、warmup、放行與停損交給可交接 artifact。

## 服務路徑與失敗代價

這條路徑是 `product-page -> cache -> product-db/pricing-service`。商品頁會同時讀取描述、價格、庫存與促銷標籤，快取需要在低延遲與正確性間平衡。

這篇示範的變更是把舊 key `product:{id}` 演進到版本化 key `product:v2:{region}:{id}`。演進動機是支援區域價格與促銷欄位拆分，避免舊序列化格式在多區域路徑下持續膨脹。

失敗代價分三層：描述欄位 stale 主要影響體驗，價格 stale 直接影響交易正確性，回源尖峰會擠壓正式狀態查詢容量。這三層要分別設 freshness、gate 與 rollback 條件。

## Key Schema 與相容窗口

Key schema 的責任是讓新舊值可共存，不讓切換變成一次性替換。這條路徑採 `dual-read` 再 `dual-write` 再 `single-read-v2`：

1. 讀取先查 `v2`，miss 再查舊 key，最後才回源。
2. 回填期間新舊 key 同時寫入，保留可回退窗口。
3. `v2` 命中穩定後，關閉舊 key 寫入，保留舊 key 讀 fallback 一段時間。

相容窗口的重點是讀語意一致。舊 key 與新 key 的值結構不同時，要先有轉換層，避免同一商品在不同 API path 回傳不同語意。

## Freshness Window 與資料分級

Freshness window 的責任是把 stale 代價寫成可執行規則，而不是只寫全域 TTL。

| 資料欄位       | freshness window | 原因                                               |
| -------------- | ---------------- | -------------------------------------------------- |
| 商品描述       | 5-15 分鐘        | 體驗導向，短時間 stale 可接受                      |
| 促銷標籤       | 1-3 分鐘         | 促銷切換頻繁，錯誤會影響轉換率                     |
| 庫存可售狀態   | 10-30 秒         | 超賣風險高，需接近即時                             |
| 價格與幣別     | 5-15 秒          | 交易正確性高風險，需短 TTL 並搭配事件失效          |
| 失敗回源保護值 | 3-10 秒          | 下游暫時異常時保護來源，避免反覆 miss 放大回源壓力 |

[TTL](/backend/knowledge-cards/ttl/) 與事件失效要同時存在。TTL 控上限，事件失效控即時性；只用其一都會造成隱性風險。

## Warmup 與回源保護

Warmup 的責任是先建立新 key 的可服務覆蓋率，再擴大流量。這條路徑採分批 warmup：`region -> category -> hot key list -> 全量`。

Warmup completion 的判讀訊號：

1. `v2` 命中率在目標區間連續穩定。
2. origin QPS 未突破上限。
3. 熱門 key 的 miss 尖峰已被抹平。

回源保護策略：

1. 以 [singleflight](/backend/knowledge-cards/singleflight/) 合併同 key 同時 miss。
2. 對回源查詢設 [rate limit](/backend/knowledge-cards/rate-limit/) 與超時。
3. 回源失敗時寫入短 TTL 降級值，避免瞬時重試風暴。
4. 針對熱門 key 在切換前做預熱與分散過期。

## Rollout / Cutover / Rollback

Rollout 的責任是把快取切換拆成可停損批次，不把風險一次放大。

| 階段                | 判讀重點                                   | 停損動作                            |
| ------------------- | ------------------------------------------ | ----------------------------------- |
| Dual read           | `v2` miss 是否快速收斂                     | 維持舊 key 讀 fallback，暫停擴批    |
| Dual write          | 新舊值語意是否一致                         | 停新格式寫入，保留舊格式            |
| Single read on `v2` | origin QPS 是否受控、價格 stale 是否達門檻 | 回退到 dual read，恢復舊 key 讀路徑 |
| Contract old key    | 舊 key 是否仍被依賴                        | 停 contract，延長相容窗口           |

Rollback 不是只「切回舊 key」。若新格式已經被下游依賴，回退時要同時保留新舊讀寫相容，避免第二次不一致。

## Evidence Package

快取 migration evidence 的責任是證明「效能提升」沒有交換成「來源壓力失控」或「交易資料錯誤」。

| 欄位                                                   | 內容                                                       |
| ------------------------------------------------------ | ---------------------------------------------------------- |
| Source                                                 | cache metrics、origin metrics、query logs、warmup job logs |
| [Time range](/backend/knowledge-cards/time-range/)     | 每個 rollout batch 的觀察窗口                              |
| [Query link](/backend/knowledge-cards/query-link/)     | hit/miss、origin QPS、stale read、eviction、latency 分布   |
| Owner                                                  | cache owner、product owner、pricing owner                  |
| [Data quality](/backend/knowledge-cards/data-quality/) | 指標延遲、抽樣覆蓋率、分區漏報                             |
| [Confidence](/backend/knowledge-cards/confidence/)     | confirmed / suspected / needs follow-up                    |
| [Known gap](/backend/knowledge-cards/known-gap/)       | 未涵蓋低流量區域、尚未演練的促銷尖峰窗口                   |

這份 evidence 要對齊 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/)。

## Release Gate

Release gate 的責任是決定是否放行下一批切換，而不是只報告觀測結果。

| Gate 欄位                                                | 最小內容                                           |
| -------------------------------------------------------- | -------------------------------------------------- |
| [Gate decision](/backend/knowledge-cards/gate-decision/) | 放行下一批、維持當前批、回退到 dual read           |
| Checks                                                   | `v2` 命中率、origin QPS ceiling、stale price ratio |
| Stop condition                                           | 回源尖峰、價格 stale 超門檻、熱門 key miss 反彈    |
| Rollback window                                          | 舊 key fallback 可維持時間、舊格式寫入可恢復時間   |
| Owner                                                    | cache on-call、pricing on-call                     |

這組欄位要對齊 [6.8 Release Gate](/backend/06-reliability/release-gate/) 與 [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。

## Incident Decision Log

切換過程中的停用新 key、延長 TTL、凍結 invalidation、回退讀路徑都屬於事故決策。每筆決策都要留在 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/)。

```yaml
incident_decision:
  timestamp: 2026-05-11T11:42:00Z
  decision: "rollback to dual-read and freeze v2-only rollout"
  context: "origin QPS exceeded ceiling and stale price ratio increased in TW region"
  evidence:
    - query: cache_v2_origin_qps_region_tw
    - query: stale_price_ratio_by_region
  owner: cache-incident-commander
  expected_effect: "reduce origin pressure and restore price freshness baseline"
  rollback_condition: "origin qps or stale ratio does not recover within 15 minutes"
```

## Case Write-back 與邊界

這篇回寫重點對齊 [2.C3 Shopify：Cache Serialization Migration](/backend/02-cache-redis/cases/shopify-cache-serialization-migration/) 與 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)：前者看格式演進與相容窗口，後者看回源尖峰與停損節奏。

這篇不處理分散式鎖正確性、queue replay 或資料庫正式狀態切換。若核心風險在互斥語意、事件重播或資料 schema，路由到 [2.4 distributed lock](/backend/02-cache-redis/distributed-lock/)、[3.4 consumer 設計與去重](/backend/03-message-queue/consumer-design/) 或 [1.7 Schema Migration Rollout 證據](/backend/01-database/schema-migration-rollout-evidence/)。
