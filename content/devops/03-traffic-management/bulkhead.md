---
title: "Bulkhead 隔離"
date: 2026-06-20
description: "不同工作負載的資源池隔離 — 一個功能過載不拖垮其他功能的隔艙設計"
weight: 4
tags: ["devops", "traffic-management", "bulkhead", "isolation", "resource-pool"]
---

Bulkhead 的概念來自船舶的隔艙設計 — 船體分成多個獨立的水密隔艙，一個隔艙進水不會讓整艘船沉沒。服務設計中，bulkhead 把不同的工作負載隔離到各自的資源池，一個工作負載的過載或故障不會消耗其他工作負載的資源。

## 隔離什麼

服務中的共享資源是 bulkhead 的隔離對象：

| 共享資源         | 不隔離時的風險                                   | 隔離方式                          |
| ---------------- | ------------------------------------------------ | --------------------------------- |
| Goroutine/Thread | 一個慢查詢佔住所有 goroutine，整個服務不回應     | 每類工作分配獨立的 goroutine pool |
| 資料庫連線       | 一個大查詢佔住 connection pool，其他查詢排隊     | 不同工作類型用不同的連線池        |
| 記憶體           | 一個功能的 buffer 無限增長，OOM 殺掉整個 process | 每個功能的 buffer 有獨立上限      |
| CPU              | 一個計算密集任務佔滿 CPU，其他請求延遲           | cgroup 或 GOMAXPROCS 限制         |

## 實作模式

### 獨立 Goroutine Pool

Go 中用有限容量的 channel 模擬 goroutine pool：

```go
var (
    ingestPool = make(chan struct{}, 100)  // ingestion 最多 100 goroutine
    queryPool  = make(chan struct{}, 20)   // query 最多 20 goroutine
    rulePool   = make(chan struct{}, 10)   // rule engine 最多 10 goroutine
)

func handleIngest(w http.ResponseWriter, r *http.Request) {
    select {
    case ingestPool <- struct{}{}:
        defer func() { <-ingestPool }()
        processIngest(r)
    default:
        http.Error(w, "ingestion overloaded", http.StatusServiceUnavailable)
    }
}
```

Ingestion 的 100 個 goroutine 全部被佔用時，新的 ingestion 請求被拒絕（503），但 query 和 rule engine 的 goroutine 不受影響。

### 獨立 Connection Pool

資料庫連線池按工作類型分開：

```go
ingestDB := sql.Open("sqlite3", "events.db")
ingestDB.SetMaxOpenConns(10) // ingestion 專用

queryDB := sql.Open("sqlite3", "events.db")
queryDB.SetMaxOpenConns(5)   // query 專用
```

SQLite 的特殊情況：SQLite 是檔案級鎖定，多個連線池打開同一個檔案時仍共享 write lock。連線池隔離在 SQLite 上主要隔離的是 Go 層的 goroutine 等待，不是 DB 層的鎖定。PostgreSQL 的連線池隔離則是真正的資源隔離。

## 容量分配

Bulkhead 的每個隔艙分配多少資源是設計決策。分配依據是「這個工作負載的優先順序和預期併發量」：

| 工作負載    | 優先順序             | 預期併發                 | 分配 |
| ----------- | -------------------- | ------------------------ | ---- |
| Ingestion   | 高（不能丟事件）     | 高（多 SDK 同時 flush）  | 60%  |
| Query       | 中（dashboard 查詢） | 低（dashboard 定期刷新） | 25%  |
| Rule engine | 低（觸發可延遲）     | 低（規則命中是少數事件） | 15%  |

分配比例不需要精確 — 重點是每個隔艙有獨立的上限，而非共享一個無差別的總上限。

## 監控系統的應用

[Collector](/monitoring/04-collector/) 同時承載 ingestion（接收事件）、query（dashboard 查詢）和 rule engine（規則評估）三種工作。不隔離時，一個複雜的 dashboard 查詢（full table scan）可能佔住所有資料庫連線，讓 ingestion 的寫入也排隊等待。

Bulkhead 設計讓 ingestion 和 query 各自的過載互不影響：

- Ingestion 的 goroutine pool 滿了 → SDK 收到 429 → 離線 buffer 接手
- Query 的 goroutine pool 滿了 → dashboard 暫時顯示 loading → 不影響 ingestion
- Rule engine 的 goroutine pool 滿了 → 規則評估延遲 → 不影響事件接收和查詢

## 下一步路由

- 背壓的流量控制 → [背壓機制](/devops/03-traffic-management/backpressure/)
- 依賴失敗的快速失敗 → [熔斷器](/devops/03-traffic-management/circuit-breaker/)
- 突發流量時的綜合策略 → [模組七 突發流量](/devops/07-burst-traffic/)
