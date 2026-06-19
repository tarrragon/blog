---
title: "Collector 架構"
date: 2026-06-19
description: "HTTP endpoint → JSON Schema 驗證 → JSONL 儲存 → CLI 查詢 → rule engine 的五段式處理鏈路"
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

### 第三段：JSONL 儲存

通過驗證的事件以 JSONL 格式（每行一個 JSON 物件）寫入檔案。JSONL 是 append-only 的格式 — 新事件追加到檔案尾端，不修改既有內容。

JSONL 的設計取捨見 [JSONL 儲存設計](/monitoring/04-collector/jsonl-storage/)。

### 第四段：CLI 查詢

儲存的 JSONL 檔案可以用 `grep` + `jq` 直接查詢。Collector 額外提供 HTTP 查詢 endpoint 讓非 CLI 使用者也能查詢。

查詢設計見 [查詢 API 設計](/monitoring/04-collector/query-api/)。

### 第五段：Rule engine

Rule engine 在事件寫入後觸發，檢查事件是否匹配預定義的規則。匹配時執行對應的動作（發通知、寫 summary、觸發 webhook）。

Rule engine 設計見 [Rule engine 設計](/monitoring/04-collector/rule-engine/)。

## Go 單一 binary 的設計選擇

Collector 用 Go 編譯成單一 binary，不依賴外部 runtime（JVM、Python interpreter、Node.js）。部署是複製一個檔案，啟動是執行一個指令。

這個選擇在自用工具場景下有特定優勢：server 和 collector 在同一台機器上，部署流程是 `scp collector user@host:` + `ssh user@host ./collector`。不需要 package manager、不需要 container registry、不需要 orchestration。

Go 的 `net/http` 標準庫提供 production-ready 的 HTTP server，JSON 處理用標準庫的 `encoding/json`，JSONL 寫入用標準庫的 `os.OpenFile` + `bufio.Writer`。整個 collector 的核心邏輯可以在 500 行以內完成。

## 下一步路由

- JSONL 儲存的設計取捨 → [JSONL 儲存設計](/monitoring/04-collector/jsonl-storage/)
- 查詢 API 的設計 → [查詢 API 設計](/monitoring/04-collector/query-api/)
- Rule engine → [Rule engine 設計](/monitoring/04-collector/rule-engine/)
- 規模成長後的演進路徑 → [規模演進](/monitoring/04-collector/scaling-evolution/)
