---
title: "功能分層與 Backend 選擇"
date: 2026-06-20
description: "SQLite 層和 PostgreSQL 層各自承載哪些功能 — 分界線是查詢模式而非資料量、觸發升級的是功能需求而非規模成長"
weight: 6
tags: ["monitoring", "collector", "architecture", "sqlite", "postgresql", "feature-tier"]
---

Collector 的可插拔 Storage Backend 分成兩個功能層級。分界線是查詢模式 — SQLite 能高效處理的查詢定義了簡單版的功能邊界，超出的查詢需求觸發 PostgreSQL 的引入。所有事件都經過同一個 Ingestion domain，差異在 Query 和 Dashboard domain 能提供什麼能力。

## SQLite 層：開發者工具

SQLite 層提供的功能聚焦在「開發者自己 debug 和監控」。所有查詢都是單一維度的 — 按時間、按類型、按名稱過濾，不需要跨事件 JOIN 或跨使用者聚合。

### 承載的功能

| 功能                       | 查詢模式           | SQL 範例                                                             |
| -------------------------- | ------------------ | -------------------------------------------------------------------- |
| 最近 error 列表            | 按 type + 時間過濾 | `WHERE type='error' ORDER BY ts DESC LIMIT 20`                       |
| Error 計數（按 name 分群） | 單表 GROUP BY      | `SELECT name, COUNT(*) FROM events WHERE type='error' GROUP BY name` |
| 單次 session 回放          | 按 session_id 過濾 | `WHERE session_id='xxx' ORDER BY ts`                                 |
| 事件時間軸                 | 按時間排序         | `WHERE ts BETWEEN ? AND ? ORDER BY ts`                               |
| 基本 rule engine           | 逐筆事件評估       | 收到事件時逐條比對 rule（不需要查歷史）                              |
| CLI 查詢                   | 任意過濾           | `WHERE type=? AND name LIKE ? AND ts > ?`                            |

這些功能覆蓋開發者日常 debug 和監控的核心操作 — 查錯誤、看時間軸、回放 session、設規則告警。

### 對應的 Dashboard 視圖

| 視圖         | 顯示                                                 |
| ------------ | ---------------------------------------------------- |
| 總覽頁       | 最近 1 小時的事件計數（按 type 分）+ 最近 error 列表 |
| 事件詳情     | 單筆事件的完整 JSON                                  |
| Session 回放 | 單次 session 內的事件序列                            |

### 對應的事件消費

SQLite 層消費所有四類事件，但消費方式是「單筆或單 session 級查詢」：

| 事件類型  | 消費方式                               | 保留需求                         |
| --------- | -------------------------------------- | -------------------------------- |
| event     | 按名稱計數、按 session 排列            | 原始 7 天（debug）               |
| error     | 按名稱分群、按時間排列、看 stack trace | 原始 30 天（error 追蹤價值較長） |
| metric    | 按名稱查最近 N 筆的值                  | 原始 7 天 + 每小時聚合 90 天     |
| lifecycle | 按 session 排列、看狀態轉換            | 原始 7 天                        |

## PostgreSQL 層：行為分析

PostgreSQL 層在 SQLite 層的基礎上加入「跨 session、跨使用者的聚合分析」。這些查詢需要 JOIN 多張表、計算時間窗口、處理大量資料的 GROUP BY — SQLite 的單寫者模型和有限的查詢最佳化器在這些場景下效能不足。

### 觸發引入 PostgreSQL 的功能需求

| 功能需求               | 為什麼 SQLite 不夠                                | PostgreSQL 提供什麼              |
| ---------------------- | ------------------------------------------------- | -------------------------------- |
| **Funnel 分析**        | 跨大量 session 的 multi-step JOIN 和聚合效能不足  | Window functions + 高效 JOIN     |
| **Cohort 留存**        | 需要按「註冊週」分群、計算每週的回訪率            | Date functions + 大規模 GROUP BY |
| **RFM 分群**           | 需要跨所有使用者計算 recency/frequency/monetary   | 全表聚合 + 分位數計算            |
| **時間趨勢 dashboard** | 需要「過去 30 天每小時的 error P95」              | 時間分桶 + percentile 函數       |
| **高併發寫入**         | 多個 SDK 同時 flush 且持續出現 database is locked | 連線池 + 並行寫入                |
| **長期保留 + 聚合**    | 降採樣的 materialized view                        | REFRESH MATERIALIZED VIEW        |

### 判斷公式

```text
需要 funnel / cohort / RFM 任一 → PostgreSQL
需要跨使用者聚合（不只看自己的資料） → PostgreSQL
需要高併發寫入（多個 SDK 同時 flush 且持續出現 database is locked 錯誤） → PostgreSQL
以上都不需要 → SQLite 足夠
```

### 對應的 Dashboard 視圖（SQLite 層不提供）

| 視圖                 | 查詢模式                        |
| -------------------- | ------------------------------- |
| Funnel 漏斗          | 多步驟轉換率（session 級 JOIN） |
| Cohort 留存表        | 時間窗口 × 群組矩陣             |
| RFM 分群散佈         | 三維度分位數計算                |
| Error 趨勢圖（長期） | 30 天 × 每小時的時間序列        |
| 效能 P95 趨勢        | percentile_cont 視窗函數        |

### 對應的事件消費

PostgreSQL 層消費的事件和 SQLite 相同（Ingestion 不變），但消費方式從「單筆/單 session」擴展到「跨 session/跨使用者」：

| 事件類型  | SQLite 層消費   | PostgreSQL 層新增消費                 |
| --------- | --------------- | ------------------------------------- |
| event     | 按名稱計數      | funnel 步驟轉換、cohort 行為分群      |
| error     | 按名稱分群      | 跨版本 error 率比較、P95 回應時間趨勢 |
| metric    | 最近 N 筆值     | 長期趨勢（materialized view 預聚合）  |
| lifecycle | 單 session 排列 | session 長度分佈、留存率計算          |

## Domain 的分層影響

| Domain        | SQLite 層                      | PostgreSQL 層新增                   |
| ------------- | ------------------------------ | ----------------------------------- |
| **Ingestion** | HTTP POST → 驗證 → 寫入        | 不變（寫入目標換 backend）          |
| **Storage**   | SQLite embedded                | PostgreSQL + 連線池                 |
| **Query**     | 單表過濾 + 單表 GROUP BY       | JOIN + window function + percentile |
| **Rule**      | 逐筆事件即時評估               | 不變（rule 不依賴聚合查詢）         |
| **Dashboard** | 總覽 + 事件詳情 + session 回放 | 新增 funnel / cohort / RFM / 趨勢圖 |

Ingestion 和 Rule 兩個 domain 和 storage backend 無關 — 事件進來的方式和規則評估的邏輯不因 backend 改變。Query 和 Dashboard 是分層影響最大的兩個 domain — PostgreSQL 層的查詢能力決定了 Dashboard 能提供什麼視圖。

## 實作邊界

Storage interface 用 Go 的 interface composition 分成兩層：

```go
type BasicStorage interface {
    Store(event Event) error
    Query(filter QueryFilter) ([]Event, error)
    Close() error
    Downsample() error
    Purge() error
}

type AnalyticsStorage interface {
    BasicStorage
    Aggregate(spec AggregateSpec) (AggregateResult, error)
    Funnel(steps []string, timeWindow Duration) (FunnelResult, error)
    Cohort(groupBy string, metric string) (CohortResult, error)
}
```

SQLite implementation 只實作 `BasicStorage`。PostgreSQL implementation 實作 `AnalyticsStorage`。Dashboard 用 Go 的 type assertion（`if as, ok := storage.(AnalyticsStorage); ok { ... }`）判斷能力 — funnel/cohort 視圖在 SQLite 模式下不顯示入口，而非顯示後報錯。

## 下一步路由

- 可插拔 Storage Backend 的架構 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- 事件枚舉方法（哪些事件要收） → [事件枚舉與補齊檢查](/monitoring/01-mental-model/event-enumeration-method/)
- 分層保留策略 → [規模演進的分層保留段](/monitoring/04-collector/scaling-evolution/)
- Funnel 分析的完整方法論 → [Funnel analysis](/monitoring/08-business-analytics/funnel-analysis/)
- 查詢消費模式（各場景需要什麼事件）→ [查詢消費模式](/monitoring/04-collector/query-consumption-patterns/)
