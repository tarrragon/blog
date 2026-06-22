---
title: "Collector 架構"
date: 2026-06-19
description: "HTTP endpoint → JSON Schema 驗證 → 儲存 → 查詢 → rule engine 的五段式處理鏈路"
weight: 1
tags: ["monitoring", "collector", "architecture", "go", "pipeline"]
---

Collector 是監控資料的接收與處理中心，職責是把 SDK 送來的事件資料轉換成可查詢、可觸發動作的持久化記錄。整條鏈路由五段組成，每段有明確的輸入和輸出，段與段之間用結構化資料傳遞。

## 五段處理鏈路

### 第一段：HTTP endpoint 接收

Collector 對外提供一個 HTTP POST endpoint（例如 `/v1/events`），接收 SDK 送來的 JSON body。每個 request 可以是單一事件或批次事件陣列。

Endpoint 的職責只有兩件事：驗證 HTTP 層面的基本條件（Content-Type、body size limit、認證 token），然後把 body 傳給下一段。HTTP 層面的錯誤（413 body too large、401 unauthorized）在這裡回應，不進入後續處理。

自用工具場景下，Go 的 `net/http` 標準庫提供的 HTTP server 已足夠。一個 `http.HandleFunc("/v1/events", handler)` 加上 `json.NewDecoder(r.Body).Decode(&events)` 就完成接收。不需要 framework。

### 第二段：JSON Schema 驗證

收到的 JSON body 用 JSON Schema 驗證結構正確性 — 必要欄位是否存在、型別是否正確、值是否在合法範圍內。驗證失敗的事件被拒絕並記錄原因，通過的事件進入下一段。

Schema 驗證是 collector 的品質閘門。沒有驗證的 collector 會累積格式不一致的資料，查詢時需要處理各種邊界條件。驗證在寫入前攔截問題，比寫入後清理成本低。

驗證的粒度是事件級 — 批次中的一個事件驗證失敗不影響其他事件。回應中標明哪些事件被接受、哪些被拒絕及原因。

### Ingestion 回應格式

回應格式把「接受了幾筆、拒絕了幾筆、拒絕原因」三件事用一套一致的結構表達。SDK 端只需要判斷 status code 就知道怎麼處理 buffer。

```json
// 200 OK — 單筆成功或批次全部成功
{ "accepted": 1 }

// 207 Multi-Status — 批次部分失敗
{
  "accepted": 1,
  "rejected": 1,
  "errors": [
    { "index": 1, "message": "missing required field: type", "fields": ["type"] }
  ]
}

// 400 Bad Request — 單筆失敗或批次全部失敗
{
  "error": "schema validation failed",
  "details": [
    { "field": "type", "message": "missing required field" }
  ]
}

// 503 Service Unavailable — 寫入端暫時不可用
{ "error": "service temporarily unavailable", "retry_after": 5 }
```

設計選擇：207 的 `errors` 陣列用 `index` 標明失敗事件在原始 batch 中的位置（0-based），SDK 可以用 index 對照原始事件做 debug log。合法事件不因部分失敗而被丟棄 — 部分成功是 batch 收集的核心價值。400 和 207 的差異是「全軍覆沒 vs 部分存活」，SDK 端的處理策略不同：400 直接清 buffer（schema 問題重試也不會過），207 只清成功的部分。

### Health endpoint 回應

Health endpoint 回傳 collector 自身的運行狀態，不包含事件內容。用途是 SDK 端確認 collector 可達、監控腳本定期探測。

```json
// GET /health → 200 OK
{
  "status": "ok",
  "uptime_seconds": 3600,
  "total_events": 1234,
  "storage_bytes": 5242880,
  "version": "0.1.0"
}
```

`total_events` 和 `storage_bytes` 讓監控腳本判斷 collector 的負載趨勢。`version` 讓 SDK 確認 collector 版本（schema 不匹配時的第一個 debug 線索）。

### 第三段：儲存

通過驗證的事件寫入 Storage Backend。Collector 使用可插拔的 Storage interface — day-one 預設用 SQLite（零依賴、嵌入式），分析需求觸發時切換到 PostgreSQL。具體的 backend 選擇和功能分層見 [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)，可插拔架構見 [規模演進](/monitoring/04-collector/scaling-evolution/)。

### 第四段：查詢

儲存的事件透過 CLI 指令或 HTTP 查詢 endpoint 存取。SQLite backend 下用 SQL 查詢；匯出為 JSONL 格式後也可用 `grep` + `jq` 做臨時分析。

查詢設計見 [查詢 API 設計](/monitoring/04-collector/query-api/)。

### 第五段：Rule engine

Rule engine 在事件寫入後觸發，檢查事件是否匹配預定義的規則。匹配時執行對應的動作（發通知、寫 summary、觸發 webhook）。

Rule engine 設計見 [Rule engine 設計](/monitoring/04-collector/rule-engine/)。

## 並發寫入策略

Go 的 HTTP server 為每個 request 分配一個 goroutine。多個 SDK 同時 flush 時，collector 同時收到多個寫入請求。Storage Backend 的並發能力決定了這些 goroutine 怎麼協調。

### SQLite Backend：單寫者模型

SQLite 的 WAL mode 允許一個 writer 和多個 concurrent reader — 讀寫不互相阻塞，但多個 writer 之間是序列化的。Go 端有兩種處理 pattern：

**Single-writer goroutine + channel**：所有 `Store()` 呼叫把事件送進一個 Go channel，由一個專屬的 goroutine 從 channel 讀取並序列寫入 SQLite。HTTP handler 送完 channel 後等待確認（或用 buffered channel 異步）。優點是背壓控制清晰 — channel 滿時 HTTP handler 自然阻塞，可以回 503。缺點是多一層間接。

**Busy timeout fallback**：不在 Go 層管序列化，讓 SQLite driver 自己處理。設定 `_pragma=busy_timeout(5000)`，多個 goroutine 同時呼叫 `Store()` 時，SQLite 讓等待的 goroutine block 直到寫入鎖釋放（最多 5 秒）。優點是實作簡單（不需要 channel 和額外 goroutine）。缺點是背壓不可控 — goroutine 數量可能累積。

自用工具場景推薦 busy timeout（簡單）、寫入量增長到出現超時錯誤時切換到 channel pattern。

### PostgreSQL Backend：連線池

PostgreSQL 透過連線池（`database/sql` 的 `SetMaxOpenConns`）支援並行寫入。多個 goroutine 可以同時寫入不同的連線，不需要額外的序列化機制。

## Go 單一 binary 的設計選擇

Collector 用 Go 編譯成單一 binary，不依賴外部 runtime（JVM、Python interpreter、Node.js）。部署是複製一個檔案，啟動是執行一個指令。

這個選擇在自用工具場景下有特定優勢：server 和 collector 在同一台機器上，部署流程是 `scp collector user@host:` + `ssh user@host ./collector`。不需要 package manager、不需要 container registry、不需要 orchestration。

Go 的 `net/http` 標準庫提供 production-ready 的 HTTP server，JSON 處理用標準庫的 `encoding/json`，SQLite 用 `modernc.org/sqlite`（pure Go、無 CGO 依賴）。整個 collector 的核心邏輯可以在 500 行以內完成。

具體的部署步驟（systemd service 檔案、啟動參數、設定檔格式）和 Quick Start（從零到第一筆事件出現在 collector）見 monitor repo 的 deployment guide。

## 下一步路由

- 功能分層與 Backend 選擇 → [功能分層與 Backend 選擇](/monitoring/04-collector/feature-tier-boundary/)
- 可插拔 Storage Backend 架構 → [規模演進](/monitoring/04-collector/scaling-evolution/)
- JSONL 匯出與備份格式 → [JSONL 儲存設計](/monitoring/04-collector/jsonl-storage/)
- 查詢 API 的設計 → [查詢 API 設計](/monitoring/04-collector/query-api/)
- Rule engine → [Rule engine 設計](/monitoring/04-collector/rule-engine/)
- 背壓與流量管控的基礎概念 → [DevOps 流量管控](/devops/03-traffic-management/)
