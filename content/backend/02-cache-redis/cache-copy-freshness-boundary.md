---
title: "2.7 Cache Copy Boundary 與 Freshness"
date: 2026-05-11
description: "說明快取何時只是可重建副本，何時會影響交易、權限或配額正確性。"
weight: 7
tags: ["backend", "cache", "freshness", "source-of-truth"]
---

Cache copy boundary 與 freshness 的核心責任是定義快取副本能承擔什麼判斷，以及它可以不新鮮多久。進入 Redis、Valkey、Memcached 或其他快取服務前，讀者需要先理解快取同時是加速層，也是 source of truth 與讀取壓力之間的風險邊界。

## Cache Copy Boundary

Cache copy boundary 的責任是把可重建副本和正式狀態分開。[source of truth](/backend/knowledge-cards/source-of-truth/) 承擔最終判斷，cache 承擔低延遲讀取與來源保護。

商品描述、公開設定、推薦摘要通常是可重建副本。價格、庫存、權限、配額與付款狀態雖然可以被快取，但它們的錯誤會直接影響交易或安全判斷，因此 freshness 與 invalidation 要更嚴格。

## Freshness

Freshness 的責任是定義資料可接受的 stale window。不同欄位需要不同 window，TTL 策略要跟欄位風險分層對齊。

| 資料類型 | 可接受 stale   | 判斷重點             |
| -------- | -------------- | -------------------- |
| 商品描述 | 秒到分鐘級     | 主要影響體驗         |
| 推薦清單 | 秒到分鐘級     | 主要影響排序與轉換率 |
| 價格     | 秒級或事件失效 | 影響交易正確性       |
| 庫存     | 秒級或即時查詢 | 影響超賣與履約       |
| 權限     | 極短或強制失效 | 影響資料外洩與越權   |
| 配額     | 極短或原子更新 | 影響濫用與計費       |

[stale data](/backend/knowledge-cards/stale-data/) 本身是快取常態成本，定義 stale 代價能讓團隊選擇對應保護。可接受 stale 的資料可用 [TTL](/backend/knowledge-cards/ttl/) 管理，高代價 stale 的資料需要事件失效、版本化 key 或回源確認。

商品描述與推薦清單偏向體驗資料，短暫 stale 的主要代價是使用者看到較舊內容。價格與庫存偏向交易資料，stale 會改變付款、履約或客服判斷。權限與配額偏向控制資料，stale 會放大越權、濫用或計費風險。這些差異決定快取策略要分欄位設計，並以服務層邊界統一交接。

## Invalidation

Invalidation 的責任是讓快取副本在正式狀態變更後收斂。常見模型包含刪除 key、更新 key、版本化 key、事件驅動失效與 TTL 保底。

[cache invalidation](/backend/knowledge-cards/cache-invalidation/) 要和資料責任對齊。價格類資料適合事件驅動失效加短 TTL；商品描述可以長 TTL 加背景刷新；權限類資料要能在撤權後快速失效。

### Cache 不一致的主要來源點

對應 [2.C1 Meta Cache Consistency Upgrade](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/) — 大規模 cache 的不一致通常不來自「TTL 設錯」、而是來自三類事件：

- **Promotion / failover**：primary 切到 replica 過程中、寫入順序可能跨節點不一致、replica 變 primary 後讀到舊資料
- **Shard move / rebalance**：cluster topology 變更時、部分 key 在搬遷窗口內可能讀到舊 shard 的副本
- **故障恢復**：節點重啟後、cache 從 backing store 重建、跟 application 寫入的新值可能交錯

傳統 invalidation（DEL key、SET key）在這些事件下不夠用、因為 *事件本身* 改變了 cache 的拓樸跟讀寫順序。Meta 的解法是把 *mutation tracing* 制度化、不只看命中率、追蹤每次資料變動是否在所有 cache 副本都收斂。

### Mutation tracing 跟一致性指標

跟一般 cache hit rate 不同、mutation tracing 是 *資料變動到所有 cache 副本收斂的時間軸*。要追蹤的指標：

- **Inconsistency window**：從 source-of-truth 寫入到所有 cache 副本反映、平均 / p99 多久
- **Inconsistency rate**：query 取到 stale 副本的比例
- **Inconsistency duration distribution**：stale 持續時間的分布（不是只看平均、長尾才是事故風險）

這些指標要接到 *告警跟回退條件*、不只放在 dashboard。當 inconsistency window 突然拉長、可能是 invalidation pipeline 卡住或 cache topology 變更中、要觸發保護動作（停止寫入、降級到回源、或回退近期變更）。

對應 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/) — cache 一致性指標屬於 *資料品質指標*、不只 *效能指標*、要進 evidence chain。

## Origin Protection

Origin protection 的責任是避免 cache miss 把壓力集中打回資料庫或下游服務。快取越接近高流量路徑，越要把 miss 視為需要治理的事件。

保護策略包含：

1. [cache warmup](/backend/knowledge-cards/cache-warmup/) 先建立熱門資料覆蓋。
2. [singleflight](/backend/knowledge-cards/singleflight/) 或 request coalescing 合併同 key 回源。
3. 對回源設 rate limit、timeout 與 fallback。
4. 對短暫找不到的結果使用短 TTL negative cache。

這些策略的共同目標是優先保護正式狀態來源，再提升命中率與延遲表現。

## 跨區一致性窗口

當 cache 跨多 region 部署、一致性問題從「副本 vs source-of-truth」變成「副本 vs 副本」。同一個用戶在不同 region 看到 cache 內容差異、可能影響業務邏輯（庫存超賣、配額超用、權限延遲）。

對應 [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/) 跟 [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/) — 規模化的 cache 把跨區一致性窗口跟區域容錯設計納入同一模型、不是分開治理。

**跨區 cache 一致性的設計選項**：

- **Strong sync**：每次寫入同步到所有 region、延遲高、可靠性高。適合付款 / 庫存 / 權限類資料。
- **Async with bounded staleness**：寫入主 region、其他 region 在 N 秒內收斂。多數場景夠用、要明確 stale window。
- **Per-region cache**：每 region 各自獨立、不跨區同步、靠 backing store 收斂。適合本地用戶為主的資料。

判讀重點：選哪種跨區一致性、跟「同一用戶會不會跨 region 操作」直接相關。全球漫遊用戶（旅遊、跨國商務）要更強的同步；本地用戶為主的服務（B2B SaaS、區域電商）可以 per-region。對應 [9.C35 Snap KeyDB](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) — Snap 把 cache 放在 application 同一 cloud（GCP）、避免跨 cloud 同步延遲、是「data 在哪、cache 跟著去」的資料引力原則。

## 選型前判準

快取服務選型前要先回答四個問題：

1. 快取值是可重建副本，還是被拿來做正式判斷。
2. 每種值的 freshness window 是多久。
3. miss 時來源系統能承受多少回源 QPS。
4. 錯誤資料要如何失效、降級與回寫事故證據。

這些問題先回答後，才進入 Redis data structure、Memcached 設計、Valkey 相容性或 managed cache 的討論。

## 實體服務討論承接點

實體快取服務文章要承接本篇的 copy boundary 與 freshness。Redis、Valkey、Memcached、DragonflyDB 或 managed cache 的比較，應先問它們如何支援 key 失效、TTL、eviction、warmup、回源保護與觀測訊號，再進入 command 或部署細節。

若服務需要嚴格 freshness，後續文章要比較事件失效、版本化 key、原子更新與 fallback 能力。若服務主要面對高讀取壓力，後續文章要比較連線模型、hot key 保護、memory policy 與 cluster/sharding 行為。若服務需要事故回退，後續文章要比較 key migration、dual read、metrics 與 rollback window。

## 下一步路由

要進一步處理讀寫流程，接著讀 [2.2 cache aside 與失效策略](/backend/02-cache-redis/cache-aside/)。要把 freshness 放進 rollout 與停損，接著讀 [2.9 Cache Migration 與 Stampede Rollback](/backend/02-cache-redis/cache-migration-stampede-rollback/)。
