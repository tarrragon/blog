---
title: "Go 平台適配"
date: 2026-06-19
description: "Graceful shutdown、signal handling、HTTP server 自身監控 — Go SDK 和 collector 端共同面對的平台問題"
weight: 4
tags: ["monitoring", "platform", "go", "graceful-shutdown", "signal"]
---

Go 的 monitoring SDK 和其他平台 SDK 的定位不同。JS / Flutter / Python SDK 是 client-side 的事件上報工具，Go SDK 更常用在 server-side — 包括 collector 本身的自身監控。Go 的 goroutine 並行模型、signal handling 機制和 HTTP server 的 graceful shutdown 是 Go 環境中的三個核心適配問題。

## Graceful shutdown

Go 程式收到 SIGTERM 或 SIGINT 時需要在退出前完成清理：flush 剩餘的 buffer、關閉網路連線、寫入最後的 lifecycle 事件。

```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
defer stop()

<-ctx.Done()
// signal received, start graceful shutdown
monitor.Close(context.WithTimeout(context.Background(), 5*time.Second))
```

graceful shutdown 的時間窗口由部署環境決定。Kubernetes 的預設 terminationGracePeriodSeconds 是 30 秒，Docker 的 stop timeout 是 10 秒。SDK 的 Close 方法接受 context 讓呼叫端控制超時。

### HTTP server 的 shutdown 順序

如果 Go 程式同時是 HTTP server 和 monitoring SDK 的使用者，shutdown 順序需要正確：

1. 停止接受新連線（`server.Shutdown(ctx)`）
2. 等待進行中的請求完成
3. flush 監控 buffer（`monitor.Close(ctx)`）
4. 關閉 log 和其他資源

如果先 close monitor 再 shutdown server，進行中的請求產生的事件會在 monitor 已關閉後嘗試送出，被靜默丟棄。

## Signal handling

Go 的 `signal.Notify` 和 `signal.NotifyContext` 是接收 OS signal 的標準方式。SDK 在 init 時不應該自己註冊 signal handler — 這會和應用程式的 signal handling 衝突（Go 的 signal handler 是先到先得，後註冊的覆蓋先註冊的）。

SDK 端的適配方式是提供 `Close` 方法讓應用程式在自己的 signal handler 中呼叫，而非 SDK 內部攔截 signal。應用程式控制 shutdown 流程，SDK 只負責在被告知關閉時 flush 和清理。

### panic recovery

Go 的 panic 會終止當前 goroutine。如果 panic 發生在 main goroutine 且沒有 recover，程式直接退出，SDK 的 buffer 中的事件遺失。

SDK 可以提供 `monitor.RecoverAndReport()` 讓開發者在 goroutine 的入口用 `defer monitor.RecoverAndReport()` 攔截 panic，記錄 error 事件後再 re-panic（保持原有的 crash 行為）。

HTTP handler 的 panic 可以用 middleware 攔截：

```go
func monitorMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer monitor.RecoverAndReport()
        next.ServeHTTP(w, r)
    })
}
```

## HTTP server 自身監控

Go 常用來寫 collector 本身。Collector 需要監控自己的健康狀態 — 請求處理速率、錯誤率、goroutine 數量、記憶體使用量。

Collector 的自身監控和接收外部事件是兩個獨立的管線。自身監控的 metric 可以寫入獨立的 JSONL 檔案（和外部事件分開），或透過 Go 的 `expvar` / `runtime.ReadMemStats` 暴露為 HTTP endpoint。

自身監控的關鍵指標：

- `collector.events.received`：每秒收到的事件數
- `collector.events.invalid`：schema 驗證失敗的事件數
- `collector.storage.write_duration_ms`：寫入 JSONL 的耗時
- `collector.goroutines`：goroutine 數量（洩漏偵測）
- `collector.memory.alloc_mb`：記憶體使用量

## 下一步路由

- 跨平台 timestamp 一致性 → [跨平台 timestamp 一致性](/monitoring/05-platform-adaptation/cross-platform-timestamp/)
- Collector 的架構設計 → [模組四 Collector 設計](/monitoring/04-collector/)
- SDK 公開 API 的 Close 方法 → [模組三 SDK 公開 API](/monitoring/03-sdk-design/public-api/)
