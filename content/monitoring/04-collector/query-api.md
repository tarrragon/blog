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

### 實作策略

HTTP 查詢 endpoint 的底層實作可以直接讀取 JSONL 檔案 — 根據 from/to 確定要讀哪些日期的檔案，逐行 parse 並過濾。這個實作在資料量小（單日萬筆以下）時足夠快。

當查詢效能成為問題時，在 JSONL 之上加一層索引（按 type/name 建立反向索引），或演進到 SQLite 儲存（見 [規模演進](/monitoring/04-collector/scaling-evolution/)）。

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
