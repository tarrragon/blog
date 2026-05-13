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

規模化 cache 的不一致主要由 *topology 變動事件* 觸發、不是 TTL 設定。對應 [2.C1 Meta Cache Consistency Upgrade](/backend/02-cache-redis/cases/meta-cache-consistency-upgrade/) — 案例指出 promotion、shard move、故障恢復是三類主要事件來源、傳統 invalidation 在大規模系統難以維持穩定。

**三類事件的典型機制**（具體實作依 cluster 設計而異）：

- **Promotion / failover**：primary 切到 replica 過程中、寫入順序可能跨節點不一致、replica 變 primary 後可能讀到舊資料
- **Shard move / rebalance**：cluster topology 變更時、部分 key 在搬遷窗口內可能讀到舊 shard 的副本
- **故障恢復**：節點重啟後、cache 從 backing store 重建、跟 application 寫入的新值可能交錯

在這些事件中、cache 拓樸隨著事件改變、需要追蹤 mutation 收斂、不只清 key。Meta 的解法是把 *mutation tracing* 制度化、追蹤每次資料變動是否在所有 cache 副本都收斂。

### Mutation tracing 跟一致性指標

Mutation tracing 是 *資料變動到所有 cache 副本收斂的時間軸* 追蹤、跟一般 cache hit rate 屬不同維度。常見的工程實踐指標（屬 case-derived 推論、非 Meta case 直接揭露具體 SLO）：

- **Inconsistency window**：從 source-of-truth 寫入到所有 cache 副本反映的耗時（平均 / p99）
- **Inconsistency rate**：query 取到 stale 副本的比例
- **Inconsistency duration distribution**：stale 持續時間的分布（看長尾才能識別事故風險、平均值會掩蓋）

這些指標要接到告警跟回退條件、用法接近一般 SLO（例：inconsistency window p99 超過 *服務可接受 stale window* 觸發保護動作）。具體門檻依業務型態定 — 付款 / 庫存 / 權限類資料的容忍可能在秒級、商品描述可能在分鐘級。

當 inconsistency window 突然拉長、可能是 invalidation pipeline 卡住或 cache topology 變更中、應觸發保護動作（停止寫入、降級到回源、或回退近期變更）。

對應 [4.17 telemetry data quality](/backend/04-observability/telemetry-data-quality/) — cache 一致性指標屬於 *資料品質指標*、要進 evidence chain、跟效能指標分開追蹤。

## Origin Protection

Origin protection 的責任是避免 cache miss 把壓力集中打回資料庫或下游服務。快取越接近高流量路徑，越要把 miss 視為需要治理的事件。

保護策略包含：

1. [cache warmup](/backend/knowledge-cards/cache-warmup/) 先建立熱門資料覆蓋。
2. [singleflight](/backend/knowledge-cards/singleflight/) 或 request coalescing 合併同 key 回源。
3. 對回源設 rate limit、timeout 與 fallback。
4. 對短暫找不到的結果使用短 TTL negative cache。

這些策略的共同目標是優先保護正式狀態來源，再提升命中率與延遲表現。

## 跨區一致性窗口

當 cache 跨多 region 部署、一致性問題從「副本 vs source-of-truth」變成「副本 vs 副本」。同一個用戶在不同 region 看到 cache 內容差異、可能影響業務邏輯（庫存超賣、配額超用、權限延遲）。規模化的 cache 把跨區一致性窗口跟區域容錯設計納入同一模型、不是分開治理（對應 [2.C6 Netflix EVCache](/backend/02-cache-redis/cases/netflix-evcache-global-cache-layer/) 跟 [2.C2 Meta mcrouter](/backend/02-cache-redis/cases/meta-mcrouter-global-cache-routing/)）。

**Strong sync** 採每次寫入同步到所有 region、延遲高、可靠性高。適合付款 / 庫存 / 權限類資料 — 庫存超賣的代價是業務直接損失（賣出實際沒有的商品）、權限不一致的代價是越權或拒服務、付款延遲一致的代價是重複扣款。這些代價高到值得付跨 region quorum 的 latency 成本。失敗代價路徑：跨 region quorum 不可達時 → 寫入失敗 → 用戶看到操作失敗、業務不繼續寫錯資料。

**Async with bounded staleness** 寫入主 region、其他 region 在 N 秒內收斂、多數場景夠用、要明確 stale window。適合 B2B SaaS、社群動態、推薦資料 — 用戶可以接受短暫看到舊版內容、但長時間 stale 會影響體驗。失敗代價路徑：跨 region 同步 lag 增長 → 用戶看到不同版本內容 → 累積到 stale window 上限時觸發 alert 跟保護。

**Per-region cache** 每 region 各自獨立、不跨區同步、靠 backing store 收斂。適合本地用戶為主的資料（區域電商、本地內容平台） — 同一用戶極少跨 region、跨區一致性需求低、為了少數情境付跨區同步成本不划算。失敗代價路徑：跨 region 操作的用戶看到 region 之間不一致 → 業務側手動補償或要求用戶重試。

判讀重點：選哪種跨區一致性跟「同一用戶會不會跨 region 操作」直接相關。全球漫遊用戶（旅遊、跨國商務）要更強的同步；本地用戶為主的服務可以 per-region。

### 跨 cloud 部署的資料引力

當 application 跟 cache 不在同一 cloud / region、每次 cache lookup 吃跨網路 latency（視 region pair 而定、9.C35 觀察值為 5-30ms）。對「每次互動查多個 cache」的服務、5ms × 10 lookup = 50ms 額外延遲、用戶感受明顯。

對應 [9.C35 Snap KeyDB cross-cloud](/backend/09-performance-capacity/cases/snap-gcp-keydb-cross-cloud/) — Snap 把 KeyDB cache 放在 GCP 上、減少跨 cloud cache lookup latency。資料引力原則：data 在哪、cache 跟著去、跨 cloud 走 batch sync 降頻、應用與 cache 共置主資料 cloud。

**Multi-cloud cache 部署原則**：

- **同 cloud 內**：cache + application + DB 都在同一 cloud、cache lookup 在 ms 級內
- **跨 cloud 採 batch sync 降頻**：低頻、高延遲容忍的資料同步（每小時 / 每天）、應用本地讀 cache
- **應用與 cache 共置主資料 cloud**：高頻、低延遲容忍的路徑跟主資料同 cloud、避免跨 cloud RTT

判讀重點：multi-cloud 架構的 cache 設計要先確定 data 主要在哪個 cloud、其他 cloud 的 application 要靠 batch sync 拿資料。Snap 從 zero-day 就在 GCP、近年走 multi-cloud 時、把 KeyDB 留在 GCP（data 一直在的地方）、避免反向部署引發的隱性 latency。違反這原則會踩到用戶層難以 debug 的延遲瓶頸。

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
