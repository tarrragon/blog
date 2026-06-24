---
title: "規模演進"
date: 2026-06-19
description: "可插拔 Storage Backend 架構 — SQLite 預設、PostgreSQL 觸發切換、時間序列 DB 長期演進"
weight: 5
tags: ["monitoring", "collector", "scaling", "sqlite", "postgresql", "timeseries", "evolution"]
---

Collector 的儲存方案是可插拔 storage backend — 同一個 binary 透過啟動參數選擇不同的 storage implementation。Go 的 interface composition 讓 storage 分成 BasicStorage（所有 backend 共用）和 AnalyticsStorage（PostgreSQL 層新增），內部實作（SQLite / PostgreSQL / 時間序列 DB）分離，切換是 config change 而非重寫程式碼。

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

選擇哪個 backend 取決於部署場景和查詢需求：

| 場景                 | Backend     | 啟動參數                        |
| -------------------- | ----------- | ------------------------------- |
| 自架簡單版（零依賴） | SQLite      | `--storage=sqlite`              |
| 需要聚合分析的自用版 | PostgreSQL  | `--storage=postgres --dsn=...`  |
| 高併發 + 長期保留    | 時間序列 DB | `--storage=timescale --dsn=...` |

## SQLite Backend（day-one 預設）

SQLite 是嵌入式資料庫，編譯進 collector binary 中，不需要額外 server。Go 用 `modernc.org/sqlite`（pure Go、無 CGO 依賴、效能約為 CGO driver mattn/go-sqlite3 的 60-80%，自用規模下足夠），開源使用者 `go build && ./collector` 就能跑，部署步驟為零。WAL mode 允許讀寫並行 — dashboard 的 SELECT 查詢不會被 ingestion 的 INSERT 阻塞，反之亦然。寫入之間的競爭由 busy_timeout 處理。

### 能力範圍

- **索引查詢**：按 type、name、timestamp 建索引，查詢從全表掃描變成索引查找
- **SQL 聚合**：`SELECT name, COUNT(*) FROM events WHERE type='error' GROUP BY name` — 一行 SQL 完成分群計數
- **跨欄位過濾**：`WHERE type='error' AND name LIKE 'terminal.%' AND ts > '2026-06-18'`
- **寫入**：WAL mode 下每秒數千筆 append 寫入

### Events 主表 DDL

Events 表的欄位從 [event.schema.json](/monitoring/02-log-schema/event-schema-fields/) 的 JSON 結構推導。Source 的 nested object 攤平成獨立 column — 方便 SQL 查詢和索引，不需要每次從 JSON 裡 extract。

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    v INTEGER NOT NULL DEFAULT 1,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    ts TEXT NOT NULL,
    source_sdk TEXT,
    source_app TEXT,
    source_version TEXT,
    source_platform TEXT,
    source_os TEXT,
    session_id TEXT,
    session_started TEXT,
    level TEXT,
    data TEXT,
    error_message TEXT,
    error_stack TEXT,
    error_type TEXT,
    receive_ts TEXT
);
```

`source_sdk` 獨立成 column 讓「按 SDK 來源篩選」（`WHERE source_sdk = 'python'`）不需要從 JSON extract。`data` 用 TEXT 存 JSON。SQLite 沒有原生 JSON 型別，但 3.38+ 支援 `json_extract()` 函式做查詢（`WHERE json_extract(data, '$.duration_ms') > 1000`）。`session_id` 獨立成 column 讓 session 回放的 JOIN 不需要 JSON extract。`error_stack` 獨立成 column 讓 error 調查時全文搜尋 stack trace 不需要 JSON extract。`receive_ts` 是 collector 收到事件的時間，和 SDK 端的 `ts` 對照可估算 clock drift。

PostgreSQL 版本的差異：`data` 改成 `JSONB` 型別（原生索引和查詢）、`source_*` 可保持為 nested JSON（PostgreSQL 的 JSONB 查詢效能足夠）或維持攤平（和 SQLite 版本保持一致）。

### 建議索引

建表時一起建索引，覆蓋 dashboard 的核心查詢模式：

```sql
CREATE INDEX idx_type_ts ON events(type, ts);    -- 按 type + 時間過濾（error 列表、趨勢圖）
CREATE INDEX idx_session ON events(session_id);   -- 按 session 回放
CREATE INDEX idx_name ON events(name);            -- 按 name 分群計數（功能使用排行）
```

Day-one 建表時就建，不是效能出問題後才加。

### 適用規模

單日事件量在十萬筆以下、SQLite 資料庫在 1GB 以下。索引查詢在毫秒級完成。自用工具和小型團隊的日常使用通常在這個範圍。

### 分層保留與降採樣

保留策略從查詢需求反推，每一種查詢需要的資料粒度和回溯深度不同。回溯越深的查詢需要的粒度越粗 — debug 需要最近幾天的逐筆事件，cohort 留存需要一整年的資料但每週一筆聚合數字就夠。

| 查詢用途   | 需要的粒度 | 回溯深度 | 對應表          |
| ---------- | ---------- | -------- | --------------- |
| Debug 定位 | 逐筆原始   | 天       | events          |
| Funnel     | 逐筆 event | 週～月   | events          |
| Error 趨勢 | 每小時計數 | 月～季   | hourly_summary  |
| Cohort     | 每天計數   | 季～年   | daily_summary   |
| RFM 分群   | 每月聚合   | 年       | monthly_summary |

SQLite 中的實作是三張摘要表加定期 job：

```sql
-- 摘要表
CREATE TABLE hourly_summary (
    hour TEXT, type TEXT, name TEXT,
    count INTEGER, error_count INTEGER,
    UNIQUE(hour, type, name)
);
CREATE TABLE daily_summary (
    date TEXT, type TEXT, name TEXT,
    count INTEGER, unique_sessions INTEGER,
    UNIQUE(date, type, name)
);

-- 降採樣（Downsample，每小時跑一次，幂等 — 重跑只更新不重複）
INSERT OR REPLACE INTO hourly_summary (hour, type, name, count, error_count)
SELECT strftime('%Y-%m-%dT%H:00:00', ts), type, name,
       COUNT(*), SUM(CASE WHEN type='error' THEN 1 ELSE 0 END)
FROM events
WHERE ts >= datetime('now', '-1 hour')
GROUP BY 1, 2, 3;

-- 清理（Purge，每天跑一次，分批刪除避免長時間鎖定）
DELETE FROM events WHERE rowid IN (
  SELECT rowid FROM events WHERE ts < datetime('now', '-7 days') LIMIT 10000
);
-- 重複執行直到影響行數為 0
DELETE FROM hourly_summary WHERE hour < datetime('now', '-90 days');
DELETE FROM daily_summary WHERE date < datetime('now', '-365 days');
```

保留期限由 collector config 設定，數字的來源是「哪些查詢需要回溯多遠」：

```yaml
retention:
  raw_events: 7d
  hourly_summary: 90d
  daily_summary: 365d
  monthly_summary: forever
```

Storage interface 的 `Downsample()` 和 `Purge()` 由 collector 的定時排程觸發（Go 的 `time.Ticker`）。每個 storage backend 各自實作 — SQLite 用上述 SQL、PostgreSQL 用相同邏輯但可以加 partial index 加速、時間序列 DB 的 continuous aggregate 和 retention policy 原生支援。

### 為什麼是聚合而非抽樣

降採樣有兩種思路。**抽樣保留**是同 name 同小時保留一筆原始事件、刪除其餘，保留了逐筆查詢能力但喪失準確計數。**聚合摘要**是把一小時內的事件壓成一筆計數記錄，喪失逐筆細節但保留準確統計。

Collector 選擇聚合摘要。降採樣後的資料用途是趨勢圖和長期統計——這些查詢需要「過去 30 天每小時的 error 總數」而非「某一筆原始 error 的 stack trace」。準確計數比保留個別事件更有價值。

這意味著原始事件 purge 後，超過保留期的逐筆查詢會回傳空結果。Dashboard 在回溯超過原始事件保留期的時間範圍時，應切換到摘要表查詢——顯示趨勢圖而非事件列表。查詢 API 的 `from` 參數超過 `retention.raw_events` 時，collector 可以自動降級到摘要表，或回傳提示告知 client 該時間範圍只有聚合資料。

### 觸發切換到 PostgreSQL 的訊號

**寫入爭搶**：SQLite 是單寫者模型。高併發寫入（多個 SDK 同時 flush、每秒數百筆以上持續發生）會出現 `database is locked` 錯誤。WAL mode 能緩解但不能根治。

**聚合查詢效能不足**：Dashboard 需要的聚合查詢（「過去 30 天每小時的 error 數量趨勢」「funnel 的每步轉換率」）在資料量成長後變慢。SQLite 沒有 parallel query 和 partial index 等進階 OLAP 能力。

**跨實例需求**：需要多個 collector 實例共用同一個資料庫時，SQLite 的單檔案模型無法跨主機存取。

## PostgreSQL Backend（分析觸發）

PostgreSQL 是獨立的資料庫 server，提供多連線並行寫入、進階索引（GIN for JSONB、partial index）和完整的 SQL 分析能力。切換到 PostgreSQL 意味著 collector 從「零依賴單一 binary」變成「binary + 外部 DB」，運維複雜度上升。

### 觸發條件

SQLite 的寫入爭搶或聚合效能成為瓶頸時切換。具體訊號：`database is locked` 錯誤頻率超過每分鐘一次、或 dashboard 的聚合查詢超過 3 秒。

### 切換方式

切換是 config change：把 `--storage=sqlite` 改成 `--storage=postgres --dsn=postgres://...`。資料遷移用匯出 + 匯入完成：

1. 從 SQLite 匯出事件為 JSONL（`monitor export --format=jsonl`）
2. 在 PostgreSQL 建立 events 表（schema 和 SQLite 相同，data 欄位改用 JSONB）
3. 匯入 JSONL 到 PostgreSQL（`monitor import --storage=postgres --file=events.jsonl`）
4. 切換啟動參數、確認查詢正常後停用 SQLite 檔案

Storage interface 保證 collector 的 ingestion、query、rule engine 邏輯不需要改動 — 只有 storage implementation 層切換。

### 能力增量

- **並行寫入**：多個 SDK 同時 flush 不會 lock
- **JSONB 索引**：對 data 欄位的特定 key 建索引（`CREATE INDEX ON events ((data->>'name'))`）
- **Window function**：funnel 和 cohort 分析的 SQL 基礎
- **Read replica**：寫入和查詢分離，dashboard 的查詢不影響 ingestion 效能

## 時間序列 DB Backend（長期演進）

時間序列資料庫（TimescaleDB、InfluxDB、VictoriaMetrics）專門為高頻 append 寫入和時間分桶聚合設計。TimescaleDB 基於 PostgreSQL 擴展，Storage interface 的 PostgreSQL implementation 可以直接複用、加上 hypertable 和 continuous aggregate。

### 觸發條件

每秒數萬筆以上的持續寫入、或需要自動 downsampling（每分鐘的原始資料保留 7 天、每小時的聚合保留 90 天、每天的聚合永久保留）。多數自用工具和小型團隊不會到達這個規模。

### 能力增量

- **時間分桶原生操作**：`time_bucket('1 hour', ts)` 替代手動 DATE_TRUNC
- **Continuous aggregate**：預計算的聚合結果自動更新
- **壓縮**：歷史資料自動壓縮，TB 級資料可查詢
- **Retention policy**：按時間自動清理舊資料

## JSONL 匯出（debug 用途）

JSONL 不作為主要 storage backend，而是作為匯出格式保留人類可讀性和 grep 友好性。`monitor export --format=jsonl` 把 storage 中的事件匯出為每行一個 JSON 物件的檔案，讓開發者可以用 grep / jq 做臨時查詢或把資料搬到其他工具。

JSONL 匯出也是備份和遷移的中介格式 — SQLite 損壞時從 JSONL 重建、切換到 PostgreSQL 時從 JSONL 匯入。

匯出使用 streaming — 從 storage 逐筆讀取、逐行寫出檔案，記憶體使用和事件總量無關。300 萬筆事件（約 900MB JSONL）的匯出不需要載入全部資料到記憶體。匯出的 JSONL 檔案包含事件明文（已 redaction 的欄位除外），匯出後不受 collector 的存取控制保護，應注意存放位置和存取權限。

## 演進原則

**按觀察到的瓶頸切換**。`database is locked` 錯誤頻率、聚合查詢延遲、磁碟使用量 — 這些是可觀察的訊號。「未來可能有百萬筆事件」是預測。按訊號行動，不按預測行動。

**切換是 config change**。Storage interface 確保切換 backend 時 collector 的其他邏輯（ingestion、query API、rule engine、dashboard）不需要改動。切換的成本是資料遷移，不是程式碼重寫。

**SQLite 是安全的起點**。多數開源使用者會停留在 SQLite backend — 單日萬筆以下、索引查詢毫秒級、零依賴部署。只有明確的效能瓶頸才值得引入外部 DB 的運維成本。

## 下一步路由

- Collector 的整體架構 → [Collector 架構](/monitoring/04-collector/architecture/)
- 查詢 API 的設計（跨 backend 統一） → [查詢 API 設計](/monitoring/04-collector/query-api/)
- 資料庫選型的通用指南 → [backend 01 資料庫](/backend/01-database/)
- 效能瓶頸的判讀方法 → [backend 09 效能容量](/backend/09-performance-capacity/)
- 水平擴展的基礎概念 → [DevOps 水平擴展](/devops/02-horizontal-scaling/)
