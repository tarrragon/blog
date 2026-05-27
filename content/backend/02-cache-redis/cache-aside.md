---
title: "2.2 cache aside 與失效策略"
date: 2026-04-23
description: "整理 read-through 思路、cache miss 與 invalidation"
weight: 2
tags: ["backend", "cache", "redis"]
---

旁路快取（cache aside）的核心責任是把讀取加速與正式狀態分離。資料庫維持 [source of truth](/backend/knowledge-cards/source-of-truth/)，快取維持可重建副本；兩者透過失效策略與新鮮度窗口對齊。

## 基本流程

[cache aside](/backend/knowledge-cards/cache-aside/) 的讀路徑是「先讀 cache，miss 後回源，再回填 cache」；寫路徑是「先寫 source of truth，再做 cache invalidation 或版本更新」。這個流程讓正式狀態維持單一責任，同時讓熱門讀取獲得低延遲。

實務上要先定義 freshness window。每個資料類型可容忍的不新鮮時間不同：商品介紹可接受秒級延遲，價格、庫存、權限與配額則需要更短窗口或即時失效。

## 失效策略

失效策略的責任是控制 cache 和 source of truth 之間的偏差。常見做法有三類：

1. 事件驅動失效：寫入成功後推事件刪 key 或更新版本，適合正確性要求高的資料。
2. TTL 失效：以時間上限控制資料壽命，適合可短暫不新鮮的資料。
3. 混合策略：事件失效為主、TTL 為保底，適合多來源寫入或跨區快取。

[stale data](/backend/knowledge-cards/stale-data/) 不是例外事件，而是快取系統的常態成本。設計時要先定義可接受的 stale 形式，再設計對應補償與回退路徑。

### 應用層 + 邊緣層 Invalidation Pipeline

當系統同時用應用層快取（Redis、本機 cache）跟邊緣層快取（[CDN](/backend/05-deployment-platform/edge-cdn-static-distribution/)）時、失效策略要把兩層當「一條 pipeline」設計、不能各自獨立 purge。兩層失效的物理特性差異：

| 層級         | Purge 控制                        | Purge 延遲                                               | 失敗代價                             |
| ------------ | --------------------------------- | -------------------------------------------------------- | ------------------------------------ |
| 應用層 cache | 自家 cluster 內、application 控制 | 毫秒 - 秒級（cache cluster 內傳播）                      | Cluster 內 stale、用戶感受立即修正   |
| CDN edge     | Vendor API 控制、全球節點同步     | 秒 - 分鐘級（傳統 origin pull）或 150ms 級（push-based） | 全球節點 stale、回填到應用層污染快取 |

正確順序是「先應用層、再 CDN」：

1. 業務寫入完成、source of truth 更新
2. Purge 應用層 cache（毫秒級完成）
3. Purge CDN（秒級到分鐘級）
4. 等 CDN purge 完成的 ack（或設等待窗口）

順序顛倒會出事 — 若先 purge CDN、CDN 全球節點 miss 後到 origin 拉資料、若 origin 應用層還是舊 cache、CDN 會把舊資料回填到全球節點、stale 被「重新永久化」一個 TTL 週期。

實務上的權衡是「CDN purge ack 是否要等」。等了會讓 write API latency 升高到秒級、不等則必須接受短暫雙層不一致。價格 / 庫存類資料適合「短 TTL + 等 purge ack」、blog 文章類適合「長 TTL + 不等 ack」。詳見 [5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/) 的 purge 操作模型。

## Cache aside vs write-through 的選擇

選 cache 模式由 *miss 成本* 跟 *寫入頻率* 的取捨決定。Cache aside、write-through、write-behind 三種主流模式各自適合不同業務壓力。

**Cache aside**（read-through）：寫入只動 source-of-truth、讀取 miss 時才填 cache。適合寫入頻率低於讀取、cache 可以重建、寫入失敗時 cache 保持不污染的場景。常見於商品詳情、推薦列表、設定值這類 read-heavy 資料、業務代價是 cache miss 時用戶等待回源、可接受。

**Write-through**：寫入同時動 source-of-truth + cache、保證 cache 永遠最新。對應 [2.C5 Shopify Write-through Cache](/backend/02-cache-redis/cases/shopify-write-through-cache-at-scale/) — Shopify 在 Shop App 後端的 read-heavy 路徑用 write-through 降低 cache miss 風險、改善熱門資料讀取穩定性。適合場景：cache miss 成本很高（回源慢或會壓垮 origin）、寫入流量可控、資料更新時間可預測。典型應用包括熱門商品的庫存 / 價格、用戶 session、需要避免讀路徑抖動的場景。

**Write-behind**（async）：寫入只動 cache、async 同步到 source-of-truth。適合寫入頻率極高、source-of-truth 跟不上、可接受 cache crash 丟失少量資料的場景。常見於 counter、rate limit、metrics aggregation 這類 *吞吐優先、可接受短暫不持久* 的資料。代價是 cache crash 會丟最近 N 秒寫入、要確認業務代價可承受。

判讀順序：先看 read/write 比例（read-heavy 偏 cache aside / write-through、write-extreme 偏 write-behind）、再看 miss 成本（miss 貴選 write-through、miss 便宜選 cache aside）、最後看持久性需求（不可丟選 write-through、可丟選 write-behind）。

## Cache 模式選擇的判讀順序

當「重算成本」「資料一致性」「持久性」三個維度互相衝突、選擇優先序：

1. **持久性必須**（不可丟、無法重建）→ 必須選 write-through 或 persistent store + cache、不能選 write-behind 或純 cache aside
2. **持久性可接受失損** + **一致性嚴格**（餘額、權限類）→ write-through 同步更新、確保 cache 不 stale
3. **持久性可接受失損** + **一致性可放寬** + **重算貴** → cache aside + 較長 TTL、減少回源
4. **持久性可接受失損** + **一致性可放寬** + **重算便宜** → cache aside + 短 TTL 或 write-behind

例如 ML feature store 場景（[9.C25 Tubi](/backend/09-performance-capacity/cases/tubi-elasticache-ml-feature-store/)）— 持久性可接受失損（feature 可重算）、一致性可放寬（推薦演算法）、重算便宜（feature engineering pipeline 跑得到）— 落在第 4 類、Tubi 把 feature store 從 ScyllaDB 遷到 ElastiCache 是合理取捨。p99 落在 ElastiCache 的 < 10ms 範圍（先前 ScyllaDB-based 架構為 ML inference 路徑的延遲瓶頸、案例未公開 ScyllaDB 端具體延遲數字）。

判讀重點：cache 的本質是用 miss 風險換取 latency；資料若無法重建、需採 persistent store 並接受 latency 成本；資料若可重建但一致性嚴格、可用 cache 但要 write-through 確保即時收斂。詳見 [2.7 cache copy boundary](/backend/02-cache-redis/cache-copy-freshness-boundary/) 的「Cache vs Persistent Store 取捨」段。

## 判讀訊號與回源保護

cache 命中下降時，來源系統會承受瞬間回源壓力。回源保護需要和失效策略一起設計：

| 風險訊號                             | 判讀重點                        | 對應動作                                                                        |
| ------------------------------------ | ------------------------------- | ------------------------------------------------------------------------------- |
| hit ratio 下降且 origin QPS 快速上升 | 大量 key 同時過期或失效策略失準 | 分散 TTL、分批失效、啟用 [cache warmup](/backend/knowledge-cards/cache-warmup/) |
| 熱門 key miss 後延遲與錯誤率同步上升 | 單 key 造成 stampede            | 啟用 request coalescing、局部預熱、限流回源                                     |
| cache 層延遲穩定但業務錯誤增加       | 值語意過期或序列化版本漂移      | 補 key version 與 schema migration                                              |
| eviction rate 升高且 value size 變大 | 容量策略與資料形狀不匹配        | 重配記憶體策略、調整 value 拆分                                                 |

[cache stampede](/backend/knowledge-cards/cache-stampede/) 與 [thundering herd](/backend/knowledge-cards/thundering-herd/) 都是回源保護議題；重點是把來源系統視為有限資源，讓 miss 風險可控。

## 服務情境

商品詳情頁是典型 cache aside 場景。頁面讀取需要組合商品主檔、價格、庫存與行銷標籤。主檔可用較長 TTL 與背景更新，價格與庫存則用事件失效與較短 TTL，讓讀取延遲與正確性維持平衡。

當促銷開始時，大量熱門商品同時被讀取。這時 cache 策略的重點從命中率轉到來源保護與新鮮度控制：是否能限制回源尖峰、是否能快速修正錯誤資料、是否能在事故時降級。

## 常見誤區

把命中率當作唯一目標，會忽略資料語意與失敗代價。命中率高不代表結果正確，尤其在價格、權限、配額類資料。

把 cache 當成正式資料來源，會讓資料修復與稽核變複雜。快取系統適合承擔讀取加速，不適合承擔正式狀態的最終判定。

## 案例回寫

cache aside 的失效風險可用 [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/) 做回寫。先看事件中的失效節奏：是大批 key 同時過期、失效順序錯置，還是熱點 key 回源放大，再對照本章的 freshness window、回源保護與容量策略。
這個案例主要支撐的是「失效節奏與回源壓力」判讀，不直接支撐分散式鎖租約或 queue replay；若是互斥控制或重播問題，應轉到 2.4 或 3.x。

命中率看似正常但業務錯誤上升時，先回到本章檢查值語意與 key 版本化，再把量測缺口接到 [4.17 Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。

## 跨模組路由

cache aside 的設計會直接影響觀測、驗證與事故處理。

1. 與 01 的交接：source of truth 與查詢壓力回到 [1.1 高併發讀寫邊界](/backend/01-database/high-concurrency-access/)。
2. 與 04 的交接：hit ratio、origin QPS、[stale read](/backend/knowledge-cards/stale-read/) 與 eviction 進入 [Telemetry Data Quality](/backend/04-observability/telemetry-data-quality/)。
3. 與 06 的交接：回源保護與壓測邊界進入 [Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)。
4. 與 08 的交接：失效策略誤配與 stampede 事故回寫 [Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/)。

## 下一步路由

**規模成長路線下一站 → [5.9 邊緣分發與靜態資源](/backend/05-deployment-platform/edge-cdn-static-distribution/)**：應用層快取上面還有 CDN 邊緣層、兩層失效時序要對齊（先 purge 應用層、再 purge 邊緣層、避免邊緣回填到應用層舊資料）。

其他延伸方向：

- 進一步處理 TTL、容量與淘汰策略 → [2.3 TTL 與 eviction](/backend/02-cache-redis/ttl-eviction/)
- 快取策略在真實事件中的失敗與修復 → [2.C9 反例](/backend/02-cache-redis/cases/failure-cache-stampede-rollout-regression/)
