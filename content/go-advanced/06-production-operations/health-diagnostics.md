---
title: "6.2 健康檢查與診斷 endpoint"
date: 2026-04-22
description: "區分服務可用性與工程診斷入口"
weight: 2
---

# 健康檢查與診斷 endpoint

健康檢查與診斷 endpoint 的核心差異是使用者與風險不同。`/health` 給監控或負載平衡器判斷 process 是否活著，`/ready` 判斷是否應接流量，`/debug/...` 則給工程師排查問題且必須限制存取。

## 本章目標

學完本章後，你將能夠：

1. 分辨 health、readiness、diagnostics 的語意
2. 設計快速穩定的 `/health`
3. 用 `/ready` 控制是否接新流量
4. 條件啟用 pprof、runtime stats 等診斷入口
5. 測試 status code 與 JSON response 合約

---

## 【觀察】所有狀態都塞進 health 會讓監控失真

Health endpoint 的核心風險是語意混亂。若 `/health` 同時檢查 process、database、queue、外部 API、cache、背景同步，任何依賴短暫波動都可能讓服務被判定死亡。

問題範例：

```text
/health
  ├── process alive?
  ├── database reachable?
  ├── queue lag small?
  ├── external API reachable?
  └── background sync fresh?
```

這些問題不應全部塞進同一個 endpoint。Process 活著、可接流量、依賴降級、工程診斷，是不同操作訊號。

## 【判讀】health、ready、diagnostics 回答不同問題

操作 endpoint 的核心設計是每個 endpoint 只回答一個問題。

| Endpoint | 使用者 | 回答的問題 | 失敗影響 |
|----------|--------|------------|----------|
| `/health` | process monitor | process 是否基本活著 | 可能重啟 process |
| `/ready` | load balancer | 是否應接新流量 | 暫停導流 |
| `/debug/...` | 工程師 | 服務內部狀態如何 | 不應公開 |
| `/metrics` | metrics collector | 可聚合監控資料 | 監控缺資料 |

這樣切分後，某個外部依賴故障不一定要讓 process 被重啟；服務可能只是不 ready，或處於 degraded 狀態。

## 【執行】health endpoint 應簡單快速

Health endpoint 的核心責任是快速回答 process 是否能處理基本 HTTP request。它應該簡單、快速、穩定。

```go
func HandleHealth(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    _, _ = w.Write([]byte(`{"status":"ok"}`))
}
```

`/health` 不應執行昂貴查詢，也不應依賴大量下游服務。若健康檢查本身很慢，監控會把診斷工具變成新問題。

## 【執行】readiness 控制是否接流量

Readiness 的核心責任是回答「服務現在是否應該接新流量」。它可以檢查啟動狀態、必要依賴、shutdown 狀態。

```go
type Readiness struct {
    ready        atomic.Bool
    shuttingDown atomic.Bool
}

func (r *Readiness) Ready() bool {
    return r.ready.Load() && !r.shuttingDown.Load()
}

func HandleReady(readiness *Readiness) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")

        if !readiness.Ready() {
            w.WriteHeader(http.StatusServiceUnavailable)
            _, _ = w.Write([]byte(`{"status":"not_ready"}`))
            return
        }

        w.WriteHeader(http.StatusOK)
        _, _ = w.Write([]byte(`{"status":"ready"}`))
    }
}
```

服務啟動尚未完成、必要背景同步尚未就緒、或 graceful shutdown 已開始時，readiness 應回 `503`。Process 仍然活著，但不應接新流量。

## 【策略】dependency check 依照監控語意分層

依賴檢查的核心判斷是故障是否代表 process 應重啟。Database 暫時不可用不一定代表 process 壞掉；重啟可能無法修復，反而造成更多負載。

建議分層：

- `/health`：只確認 process alive。
- `/ready`：確認必要依賴是否足以接新流量。
- `/diagnostics/dependencies`：提供工程師查看細節。

診斷 response 可以包含穩定欄位：

```json
{
  "status": "degraded",
  "dependencies": {
    "database": "ok",
    "queue": "lagging"
  }
}
```

監控應依賴 status code 與穩定欄位，工程師再用 body 細節診斷問題。自由文字可以輔助閱讀，但不應成為監控規則的依據。

## 【執行】diagnostics endpoint 要條件啟用

Diagnostics endpoint 的核心用途是提供工程師排查問題的資料。pprof、runtime metrics、internal queue length、goroutine count 都屬於這類。

```go
func RegisterDiagnostics(mux *http.ServeMux, enabled bool) {
    if !enabled {
        return
    }

    mux.HandleFunc("/debug/runtime", HandleRuntimeStats)
}

func HandleRuntimeStats(w http.ResponseWriter, r *http.Request) {
    var stats runtime.MemStats
    runtime.ReadMemStats(&stats)

    response := map[string]any{
        "heap_alloc":  stats.HeapAlloc,
        "num_gc":      stats.NumGC,
        "goroutines":  runtime.NumGoroutine(),
    }

    _ = json.NewEncoder(w).Encode(response)
}
```

Diagnostics 可能揭露內部狀態、記憶體資訊、goroutine 數量、路徑與部署細節，不應公開給一般使用者。若需要長期保留，至少應限制在內網、管理 port、認證或防火牆後。

## 【判讀】status code 是監控合約

健康檢查的核心合約是 status code。監控系統通常先看 HTTP code 與 timeout，不會理解複雜 body。

| 狀態 | 意義 |
|------|------|
| `200 OK` | 符合該 endpoint 的健康條件 |
| `503 Service Unavailable` | 暫時不可用或不應接流量 |
| `405 Method Not Allowed` | 呼叫方式錯誤 |
| timeout | endpoint 無法在預期時間內回應 |

Body 可以提供人類可讀資訊，但不應讓監控依賴自由文字。若要機器讀取，使用穩定 JSON 欄位，例如 `status`、`reason`、`dependencies`。

## 【測試】endpoint 測試要鎖定 status code

Endpoint 測試的核心是驗證 status code 與穩定 JSON 欄位，而不是完整自由文字。

```go
func TestReadyReturnsUnavailableWhenShuttingDown(t *testing.T) {
    readiness := &Readiness{}
    readiness.ready.Store(true)
    readiness.shuttingDown.Store(true)

    req := httptest.NewRequest(http.MethodGet, "/ready", nil)
    rec := httptest.NewRecorder()

    HandleReady(readiness).ServeHTTP(rec, req)

    if rec.Code != http.StatusServiceUnavailable {
        t.Fatalf("status = %d, want %d", rec.Code, http.StatusServiceUnavailable)
    }
}
```

Diagnostics endpoint 也應測 gate 關閉時不註冊或回 404，避免診斷入口不小心暴露。

## 本章不處理

本章不討論 Prometheus、OpenTelemetry 或特定雲平台健康檢查設定。這些工具很重要，但 Go 程式本身要先定義清楚 health、readiness、diagnostics 的語意。後續可接 [Observability pipeline、metrics 與 tracing](../07-distributed-operations/observability-pipeline/) 以及 [Kubernetes、systemd 與 load balancer 合約](../07-distributed-operations/deployment-contracts/)。

## 小結

`/health`、`/ready`、diagnostics endpoint 解決不同問題。Health 檢查 process 基本可用性，readiness 控制是否接新流量，diagnostics 支援工程排查且應限制存取。Status code 是監控合約，JSON body 是補充細節；把這些訊號混在一起會讓操作判斷與安全邊界都變模糊。
