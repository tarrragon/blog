---
title: "查詢 API 設計"
date: 2026-06-19
description: "CLI grep 友好的 JSONL 結構 + HTTP 查詢 endpoint — 兩種查詢介面各自的適用場景和設計要點"
weight: 3
tags: ["monitoring", "collector", "query", "cli", "grep", "api"]
---

查詢是監控資料的消費介面。Collector 提供兩種查詢方式：CLI 直接操作 JSONL 檔案（grep + jq），和 HTTP 查詢 endpoint。兩種方式服務不同的消費者 — CLI 給開發者即時探索，HTTP endpoint 給自動化工具和非 CLI 使用者。

## CLI 查詢：grep + jq

JSONL 格式的最大優勢是原生支援 Unix 文字處理工具。不需要額外的查詢語言、不需要客戶端工具、不需要連線到 database。

### 常見查詢模式

按事件類型過濾：

```bash
grep '"type":"error"' events-2026-06-19.jsonl | jq .
```

按 namespace 過濾：

```bash
grep '"name":"terminal.connect' events-2026-06-19.jsonl | jq .
```

按時間範圍過濾（跨檔案）：

```bash
cat events-2026-06-1{8,9}.jsonl | jq 'select(.ts >= "2026-06-18T18:00:00")'
```

統計每種事件的數量：

```bash
jq -r '.name' events-2026-06-19.jsonl | sort | uniq -c | sort -rn
```

### grep 友好的 JSONL 設計

JSONL 的每行 JSON 結構影響 grep 的查詢效率和準確性。

**把常用過濾欄位放在 JSON 的前面**。grep 是字串匹配，把 `type` 和 `name` 放在行首讓 grep pattern 更簡單、誤匹配更少。

**避免 JSON 值中包含雙引號**。事件名稱和型別用簡單字串（不含特殊字元），讓 grep 的 pattern 不需要處理 escape。

**每行 JSON 不換行**。JSONL 的定義就是每行一個 JSON，但格式化工具可能自動加換行。寫入時用 `json.Marshal`（Go）或 `JSON.stringify`（JS）確保單行輸出。

## HTTP 查詢 endpoint

HTTP 查詢 endpoint 讓非 CLI 使用者（dashboard、自動化腳本、其他服務）能查詢事件資料。

### Endpoint 設計

```text
GET /v1/events?type=error&name=terminal.connect.*&from=2026-06-18T00:00:00Z&to=2026-06-19T00:00:00Z&limit=100
```

查詢參數：

| 參數   | 說明                                     | 預設值    |
| ------ | ---------------------------------------- | --------- |
| type   | 事件類型（event/error/metric/lifecycle） | 全部      |
| name   | 事件名稱（支援 `*` 萬用字元）            | 全部      |
| from   | 起始時間（ISO 8601）                     | 24 小時前 |
| to     | 結束時間（ISO 8601）                     | 現在      |
| limit  | 回傳筆數上限                             | 100       |
| offset | 分頁偏移                                 | 0         |

### 回應格式

```json
{
  "events": [
    {
      "v": 1,
      "type": "error",
      "timestamp": "2026-06-19T08:42:00Z",
      "source": { "sdk": "python", "platform": "macos", "app": "claude-hooks" },
      "name": "hook.failure",
      "level": "error",
      "data": { "hook": "branch-status-reminder", "step": "validation" },
      "error": { "message": "KeyError: 'status'", "stack": "Traceback...", "type": "KeyError" },
      "context": { "session_id": "sess-abc-123" }
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

`events` 陣列按 `timestamp` 降序排列。`total` 是符合篩選條件的全量筆數（不受 limit 截斷），讓呼叫端計算分頁（`total_pages = ceil(total / limit)`）。分頁用 offset-based（`offset=100` 取第二頁），適合資料量在十萬筆以下的場景。資料量大到 offset 效能不足時，改用 cursor-based（`after=<last_event_id>`），但 cursor-based 是 PostgreSQL 層的演進，SQLite 層用 offset 足夠。

### 實作策略

HTTP 查詢 endpoint 的底層實作可以直接讀取 JSONL 檔案 — 根據 from/to 確定要讀哪些日期的檔案，逐行 parse 並過濾。這個實作在資料量小（單日萬筆以下）時足夠快。

當查詢效能成為問題時，在 JSONL 之上加一層索引（按 type/name 建立反向索引），或演進到 SQLite 儲存（見 [規模演進](/monitoring/04-collector/scaling-evolution/)）。

## 聚合查詢

逐筆查詢回答「發生了什麼」，聚合查詢回答「發生了多少」。Error 調查的第一步是定位最頻繁的 error — 「哪些 error 最多」需要按 name 分群計數的聚合結果，逐筆列表在這個階段資訊量太大。

### Endpoint 設計

```text
GET /v1/events/summary?type=error&from=2026-06-18T00:00:00Z&to=2026-06-19T00:00:00Z&group_by=name
```

回傳按 name 分群的統計：

```json
{
  "groups": [
    { "name": "hook.failure", "count": 15, "last_seen": "2026-06-19T08:42:00Z" },
    { "name": "terminal.connect.failed", "count": 3, "last_seen": "2026-06-19T07:10:00Z" }
  ],
  "total": 18,
  "from": "2026-06-18T00:00:00Z",
  "to": "2026-06-19T00:00:00Z"
}
```

查詢參數和逐筆查詢共用（type、name、from、to），額外的 `group_by` 指定分群欄位（name 或 type）。

### SQL 實作

SQLite backend 下直接用 GROUP BY：

```sql
SELECT name, COUNT(*) as count, MAX(timestamp) as last_seen
FROM events
WHERE type = 'error' AND timestamp BETWEEN ? AND ?
GROUP BY name
ORDER BY count DESC
LIMIT 100
```

有 type + timestamp 複合索引時，這個查詢在 10 萬筆資料內的效能和逐筆查詢相當 — GROUP BY 在索引掃描後做，不需要全表掃描。

### 和逐筆查詢的定位差異

| 面向       | 逐筆查詢 `/v1/events`                  | 聚合查詢 `/v1/events/summary`        |
| ---------- | -------------------------------------- | ------------------------------------ |
| 回答       | 發生了什麼（事件列表）                 | 發生了多少（統計摘要）               |
| 用途       | 看單筆 error 的 stack trace            | 找出最頻繁的 error                   |
| 回傳       | 事件陣列（含完整 JSON）                | 分群摘要（name + count + last_seen） |
| 資料量     | 大（完整事件 body）                    | 小（只有統計值）                     |
| 典型工作流 | 聚合查詢找到問題 name → 逐筆查詢看細節 | 首先使用                             |

兩者是互補的工作流 — 聚合查詢定位問題方向，逐筆查詢深入細節。Dashboard 的 Error 列表頁面直接消費聚合查詢的結果。

## CLI vs HTTP 的定位

| 面向   | CLI (grep + jq)       | HTTP endpoint          |
| ------ | --------------------- | ---------------------- |
| 使用者 | 開發者                | 自動化工具、dashboard  |
| 適合   | 即時探索、ad-hoc 查詢 | 結構化查詢、程式化存取 |
| 優勢   | 零安裝、可組合        | 遠端存取、標準化       |
| 限制   | 需要 SSH 存取 server  | 需要 collector 啟動    |

兩種介面共存 — CLI 用於開發者日常 debug，HTTP endpoint 用於自動化和遠端存取。兩者底層讀取同一份 JSONL 檔案，結果一致。

## 下一步路由

- JSONL 儲存的設計 → [JSONL 儲存設計](/monitoring/04-collector/jsonl-storage/)
- Rule engine 的自動化處理 → [Rule engine 設計](/monitoring/04-collector/rule-engine/)
- Collector 的完整架構 → [Collector 架構](/monitoring/04-collector/architecture/)
