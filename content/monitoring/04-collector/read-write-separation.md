---
title: "讀寫分離與查詢擴展"
date: 2026-06-22
description: "Monitor 在 PostgreSQL 層之後的讀寫競爭問題、Read Replica 分離策略、CQRS 判讀訊號"
weight: 13
tags: ["monitoring", "collector", "scaling", "read-write", "replica", "cqrs"]
---

Monitor 的寫入路徑（SDK flush → HTTP endpoint → Storage）和讀取路徑（Dashboard 刷新、Debug 即席查詢、聚合趨勢、Rule engine 評估）在 SQLite 階段不太會互相干擾 — 事件量小、查詢簡單、WAL mode 讓讀寫各自進行。進入 PostgreSQL 層之後，兩條路徑的負載都會成長，而且成長方向不同。本章處理的是讀寫開始互相干擾時的辨識訊號和應對策略。

## 讀寫競爭的具體場景

Monitor 的 PostgreSQL 層同時承擔三種負載，各自的資源消耗特性不同。

### 寫入負載

SDK flush 是 Monitor 的主要寫入來源。多個 SDK 同時 flush 時，collector 透過連線池並行寫入 PostgreSQL。每筆 INSERT 涉及主表寫入 + 索引更新（`idx_type_ts`、`idx_session`、`idx_name`）。寫入量隨 SDK 數量和 flush 頻率線性成長。

Downsample job 是另一種寫入：定期把原始事件聚合到 `hourly_summary` / `daily_summary`。Downsample 執行時同時做大量 SELECT（讀原始事件）和 INSERT（寫摘要），佔用連線和 I/O。

### Dashboard 讀取負載

Dashboard 是穩定的高頻背景負載。總覽頁每 30 秒刷新、Error 列表每分鐘刷新、趨勢圖每分鐘重算。每次刷新執行一到多個聚合查詢（`GROUP BY name`、`COUNT(*)`、時間分桶）。

Dashboard 查詢的掃描量隨資料累積成長。「過去 7 天每小時的 error 數量」在第一週掃描幾千筆，三個月後掃描幾十萬筆。如果沒有用 `hourly_summary` 摘要表、而是直接查原始 events 表，查詢時間會隨資料量線性增加。

### Debug 即席讀取負載

Debug 查詢是偶發的突增負載。開發者在排查問題時，可能用 session_id 拉出整條事件鏈、用 error name 掃描最近 N 筆 stack trace、或用 `data->>'duration_ms'` 做 ad-hoc 效能分析。這些查詢的特徵是不可預測、偶發但延遲敏感 — 開發者在等結果。

### 競爭發生在哪

三種負載打同一個 PostgreSQL 時，競爭集中在兩個資源：

**連線池**：collector 的 `SetMaxOpenConns` 是固定值（例如 20）。如果 ingestion 佔用 15 條連線做批次 INSERT、dashboard 需要 3 條做聚合查詢、debug 需要 2 條做 ad-hoc 查詢 — 剛好佔滿。這時 downsample job 啟動需要連線，會排隊等待。

**I/O 頻寬**：聚合查詢需要掃描大量資料（sequential scan 或 index scan + heap access），跟 INSERT 的隨機寫入搶磁碟 I/O。在 HDD 或低階 SSD 上，一個 heavy 聚合查詢可以讓同時進行的 INSERT latency 從毫秒跳到十毫秒。

**鎖競爭**：PostgreSQL 的 MVCC 讓 SELECT 跟 INSERT 不互相阻塞（reader 不等 writer），但 Downsample 的 INSERT OR REPLACE 跟 ingestion 的 INSERT 可能在同一張表上競爭 row-level lock。長時間的 aggregation query 也可能觸發 `idle in transaction` 問題，佔住連線不釋放。

## 辨識訊號

讀寫競爭的辨識訊號是「寫入跟讀取的效能同時退化，而且退化是交互的」：

- Ingestion 的 INSERT latency 在 dashboard 刷新時段（每 30 秒）出現週期性尖峰
- Dashboard 的聚合查詢在 SDK 高峰 flush 時段（例：每整點、app 啟動潮）變慢
- Debug 即席查詢在 downsample job 執行期間 timeout
- PostgreSQL 的 `pg_stat_activity` 顯示多個 `idle in transaction` 或 `waiting` 狀態
- 連線池使用率持續高於 80%，偶發 `too many connections` 或連線等待

單純的寫入慢（沒有讀取影響）或單純的查詢慢（沒有寫入影響）不是讀寫競爭，可能是索引缺失或查詢效率問題。讀寫競爭的特徵是「兩邊同時退化、一邊忙的時候另一邊也變慢」。

## Read Replica 分離

Read replica 是 Monitor 在 PostgreSQL 層後的第一步讀寫分離。概念簡單：寫入走 primary、讀取走 replica，兩者物理隔離。

### 架構

```text
SDK ──→ Collector
             │
        ┌────┴──────────┐
        ▼                ▼
   Primary (write)   Replica (read)
        │                │
        │  replication →  │
        │                │
        ▼                ▼
   Ingestion        Dashboard + Debug
   Downsample       聚合查詢
```

Collector 持有兩個連線池 — 一個連 primary（用於 `Store()`、`Downsample()`、`Purge()`），一個連 replica（用於 `Query()`、`Aggregate()`、Dashboard 的所有讀取）。

### Storage interface 的調整

現有的 `BasicStorage` interface 不需要改動。實作層在初始化時接收兩個 DSN（primary + replica），內部根據操作類型選擇連線池：

```go
type PostgresStorage struct {
    primary *sql.DB  // write operations
    replica *sql.DB  // read operations (nil = use primary)
}
```

當 replica DSN 未設定時，所有操作走 primary — 行為跟目前一樣，不破壞 single-instance 部署。

### Replica lag 對各查詢場景的影響

PostgreSQL streaming replication 的 lag 在同 AZ 通常 < 100ms，跨 AZ 可能到秒級。各查詢場景對 lag 的容忍度不同：

| 查詢場景           | Lag 容忍度     | 走哪裡  | 理由                                    |
| ------------------ | -------------- | ------- | --------------------------------------- |
| Dashboard 總覽     | 秒級可接受     | Replica | 30 秒刷新一次，lag < 1 秒不影響判讀     |
| Error 列表         | 秒級可接受     | Replica | 新 error 晚一秒出現在列表上不影響 debug |
| 聚合趨勢圖         | 分鐘級可接受   | Replica | 趨勢圖本身就是歷史資料的聚合            |
| Funnel / Cohort    | 分鐘級可接受   | Replica | 分析查詢看的是天級或週級的資料          |
| Debug 即席查詢     | 數秒可能不接受 | Primary | 開發者剛送一筆 test event 想立刻查到    |
| Rule engine 查歷史 | 秒級可接受     | Replica | Rule 的閾值判斷容忍短暫延遲             |

Debug 即席查詢的 lag 問題是 read-after-write 一致性 — 開發者從 SDK 送出 test event 後立刻查詢，如果查 replica 可能還沒同步到。解法是讓 debug query API 提供 `consistency=strong` 參數，強制走 primary。預設走 replica（大部分 debug 查的是歷史資料），只有需要 read-after-write 時切 primary。

### 引入時機

Read replica 的引入時機是「辨識訊號」段列出的讀寫競爭訊號持續出現，而且已經做過基本最佳化（索引補齊、dashboard 改讀 summary 表、downsample job 調整執行時段避開高峰）仍然不夠。

引入 read replica 的成本是多一台 PostgreSQL 實例（或 managed service 的 read replica 選項）和 replication 設定。Monitor 的 PostgreSQL 層已經承擔外部 DB 的運維成本，加 replica 是增量而非從零開始。

## 預聚合作為讀取面的第一道防線

在引入 read replica 之前，預聚合是降低讀取負載最有效的方式 — 不改架構、不加機器、只改查詢的資料來源。

Monitor 已經有 `hourly_summary` 跟 `daily_summary` 兩張摘要表（見 [規模演進](/monitoring/04-collector/scaling-evolution/)）。Dashboard 的趨勢圖跟 Error 計數應該讀摘要表而非原始 events 表。

預聚合沒處理到的讀取負載是「需要原始事件的查詢」— Debug 即席查詢（看 stack trace）、Session 回放（看事件序列）、Funnel 分析（跨 session JOIN）。這些查詢必須掃描原始資料，預聚合無法取代。當這類查詢的負載開始擠壓寫入時，才是引入 read replica 的時機。

概念上，預聚合就是 [recording rule](/backend/knowledge-cards/recording-rule/) 在關聯式資料庫的實作。Downsample job 定期執行 aggregation query、把結果寫入 summary 表，dashboard 讀 summary 表而非重算 raw data。Monitor 的 `hourly_summary` 等同於 Prometheus 的 recording rule output、PostgreSQL 的 [materialized view](/backend/knowledge-cards/materialized-view/) 等同於 TSDB 的 continuous aggregate。

## CQRS 的判讀訊號

Read replica 解決的是「讀寫搶同一台機器的 I/O 跟連線」。當問題不只是資源競爭、而是讀寫的資料形狀根本不同時，read replica 不夠 — 需要獨立的 [read model](/backend/knowledge-cards/read-model/)。

[CQRS](/backend/knowledge-cards/cqrs/) 的完整概念見知識卡。以下是 Monitor 情境下，什麼訊號出現時該考慮從 read replica 往 CQRS 方向演進。

### 訊號一：讀取需要的資料形狀跟 events 表差異太大

Monitor 的 events 表是 append-only 的正規化結構（一筆事件一個 row）。如果讀取面需要的是：

- 每個 user 的行為摘要（最近登入、最常用功能、累計 error 數）— 需要跨所有事件聚合成 per-user profile
- 即時的 error fingerprint 索引（相同 stack trace 的 error 自動分群、計數、追蹤首次出現時間）— 需要維護一張反正規化的 error group 表
- 跨 session 的 funnel conversion 快照 — 需要維護一張 pre-computed funnel 表

這些讀取形狀無法用 `SELECT FROM events` + 索引高效產生，需要獨立的 read model 持續從 events 推算。

### 訊號二：預聚合的種類和刷新頻率失控

Summary 表從 2 張（hourly + daily）增長到 5 張、10 張，每張的刷新頻率從每小時變成每分鐘。Downsample job 的執行時間從秒級增長到分鐘級，開始擠壓 ingestion。

這時候 summary 表已經不只是「摘要」，而是事實上的 read model — 專門為讀取需求設計的獨立資料結構。承認這個事實、把 summary 表的維護從 Downsample job 拆出來成為獨立的 projection consumer，就是進入 [CQRS](/backend/knowledge-cards/cqrs/) 的起點。

### 訊號三：讀取跟寫入需要獨立擴展

寫入量穩定（SDK 數量不變），但讀取面因為新增 dashboard、新增分析維度、新增使用者而持續成長。Read replica 可以加多台分攤讀取，但每台 replica 仍然存的是跟 primary 一樣的 events 表結構 — 讀取查詢的複雜度不變，只是分攤到更多機器。

獨立的 read model 可以用完全不同的 schema（反正規化、pre-joined、pre-aggregated），讓讀取查詢從 O(N) 的聚合變成 O(1) 的 lookup。這是 CQRS 的核心價值 — 讀取面的效能不再受限於寫入面的資料結構。

### Monitor 目前的位置

Monitor 目前在「SQLite → PostgreSQL → Read Replica」這條路徑的前半段。MVP 用 SQLite、功能需求觸發 PostgreSQL、讀寫競爭觸發 Read Replica。CQRS 是更遠的演進方向，只有上述三個訊號明確出現時才值得引入。

```text
SQLite（零依賴）
  → PostgreSQL（聚合分析觸發）
    → 預聚合 summary 表（讀取負載觸發）
      → Read Replica（讀寫競爭觸發）
        → 獨立 read model / CQRS（資料形狀不對稱觸發）
```

每一步都是被具體的效能訊號或功能需求推動的，跟 Monitor 整體的「按觀察到的瓶頸切換」原則一致。教學的價值在於讓讀者在每一步都知道「下一步是什麼、什麼訊號出現時該走」— 而不是在 SQLite 階段就預先設計 CQRS。

## 跟 Backend 的概念對照

Monitor 的讀寫分離路徑跟 backend 教材的概念有直接對應：

| Monitor 演進階段             | Backend 對應概念                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| SQLite WAL（讀寫各自進行）   | [WAL mode](/backend/knowledge-cards/write-ahead-log/) 的 reader-writer 並行                  |
| PostgreSQL summary 表        | [Materialized view](/backend/knowledge-cards/materialized-view/) 的最簡實作                  |
| Read replica                 | [1.8 Query Boundary](/backend/01-database/state-ownership-query-boundary/) 的讀寫分流        |
| 獨立 read model              | [CQRS](/backend/knowledge-cards/cqrs/) + [Projection](/backend/knowledge-cards/projection/)  |
| Downsample job → 獨立 worker | [Event sourcing](/backend/knowledge-cards/event-sourcing/) 架構中 projection consumer 的起點 |

Monitor 的規模演進路徑是 backend 概念的具體實例 — 從自用工具到小型服務、從單機到讀寫分離、從 summary 表到可能的 CQRS，每一步都能回到 backend 教材找到概念基礎。

## 下一步路由

- Storage backend 的可插拔架構 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- 功能分層的定義 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- Ingestion 端的流量防線 → [Ingestion Scaling](/monitoring/04-collector/ingestion-scaling/)
- 讀寫分離的通用概念 → [CQRS 知識卡](/backend/knowledge-cards/cqrs/)
- 資料庫層的讀寫分離設計 → [1.8 State Ownership 與 Query Boundary](/backend/01-database/state-ownership-query-boundary/)
- 觀測領域的讀取路徑設計 → [4.23 觀測查詢設計](/backend/04-observability/observability-query-design/)
