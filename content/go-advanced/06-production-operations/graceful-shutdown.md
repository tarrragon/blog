---
title: "6.1 graceful shutdown 與 signal handling"
date: 2026-04-22
description: "用 signal 與 context 傳遞停止訊號"
weight: 1
---

Graceful shutdown 的核心目標是服務收到停止訊號後，不再接受新工作，並給既有工作一段時間完成或清理。Go 服務通常用 signal、root context、`http.Server.Shutdown`、worker context 與 timeout 串起停止流程。

## 本章目標

學完本章後，你將能夠：

1. 把 OS signal 轉成 root context 取消
2. 用 `http.Server.Shutdown` 停止接受新 request
3. 讓 worker、hub、WebSocket pump 觀察同一個停止訊號
4. 設計 shutdown timeout 與強制退出邊界
5. 測試 server 與 worker 的停止流程

---

## 【觀察】直接結束 process 會留下不確定狀態

Shutdown 的核心風險是停止流程不明確。服務可能正在處理 request、WebSocket client 仍在線、worker 正在寫資料、queue message 尚未 ack、diagnostics 還以為服務可接流量。

不完整停止常見後果：

- 新 request 在服務即將關閉時仍被接受。
- WebSocket client 沒收到 close，server 端 goroutine 殘留。
- 背景 worker 寫到一半被中斷。
- readiness 還是 200，負載平衡器繼續送流量。
- 測試結束後留下 goroutine 或開放 port。

Graceful shutdown 不是保證所有工作都完成，而是讓停止策略可預期。

## 【判讀】shutdown 是多階段流程

Graceful shutdown 的核心流程是先停止接新工作，再讓既有工作收尾，最後釋放資源。

建議順序：

```text
receive SIGINT/SIGTERM
        │
        ▼
cancel root context
        │
        ├── readiness becomes false
        ├── HTTP server stops accepting new requests
        ├── workers stop consuming new jobs
        ├── WebSocket hub unregisters clients
        └── diagnostics/log records shutdown reason
        │
        ▼
wait within timeout
        │
        ▼
process exits
```

不同服務會有不同細節，但核心不變：停止訊號要集中，元件各自完成自己的 cleanup，整體流程要有 timeout。

## 【執行】signal 轉成 root context

Signal handling 的核心責任是把作業系統訊號轉成應用程式可理解的取消訊號。Go 1.16 之後可以使用 `signal.NotifyContext`。

```go
func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    if err := run(ctx); err != nil {
        log.Fatal(err)
    }
}
```

`ctx` 是 root context。HTTP server、worker、hub、diagnostics 都應從它派生出自己的 lifecycle，而不是每個元件各自監聽 signal。

Signal handler 不應放大量清理邏輯。它只負責發出停止意圖；實際清理由各元件在自己的 ownership 邊界內完成。

## 【執行】HTTP server 用 Shutdown 停止接新 request

`http.Server.Shutdown` 的核心行為是停止接受新連線，並等待既有 request 在 timeout 內完成。它比直接 `Close` 更適合 graceful shutdown。

```go
func RunHTTPServer(ctx context.Context, handler http.Handler) error {
    server := &http.Server{
        Addr:    ":8080",
        Handler: handler,
    }

    errCh := make(chan error, 1)
    go func() {
        errCh <- server.ListenAndServe()
    }()

    select {
    case <-ctx.Done():
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        return server.Shutdown(shutdownCtx)

    case err := <-errCh:
        if errors.Is(err, http.ErrServerClosed) {
            return nil
        }
        return err
    }
}
```

Shutdown timeout 是必要邊界。沒有 timeout 的 shutdown 可能永遠等待某個卡住 request；timeout 太短則可能讓合理 request 來不及收尾。

## 【策略】readiness 應先變成 false

Readiness 的核心用途是控制服務是否應接新流量。Shutdown 開始後，readiness 應先變成 false，再停止 server 或等待既有工作。

```go
type Lifecycle struct {
    shuttingDown atomic.Bool
}

func (l *Lifecycle) BeginShutdown() {
    l.shuttingDown.Store(true)
}

func (l *Lifecycle) Ready() bool {
    return !l.shuttingDown.Load()
}
```

Signal 收到後：

```go
lifecycle.BeginShutdown()
cancel()
```

這讓負載平衡器或監控能知道服務不應再接新流量。Process 還活著，但 readiness 已經反映操作狀態。

## 【執行】背景工作要觀察 context

背景 worker 的核心 shutdown 條件是每個 loop 都能觀察停止訊號。Ticker、queue consumer、WebSocket hub 都應該有退出路徑。

```go
func RunWorker(ctx context.Context) error {
    ticker := time.NewTicker(time.Minute)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            if err := RunOnce(ctx); err != nil {
                return err
            }
        }
    }
}
```

若 `RunOnce` 可能執行很久，也應接收 context。否則外層 loop 看到 cancel，內層 I/O 或計算仍可能卡住。

## 【策略】WebSocket cleanup 要回到 hub owner

WebSocket shutdown 的核心原則是讓 hub 或 connection manager 統一清理 client。不要讓 signal handler 直接遍歷各種 connection 並隨意 close。

```go
func (h *Hub) Run(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            h.closeAllClients()
            return
        case client := <-h.register:
            h.registerClient(client)
        case client := <-h.unregister:
            h.unregisterClient(client)
        }
    }
}
```

`closeAllClients` 應透過 hub 的既有 owner 邏輯關閉 `send`、移除訂閱、關閉 connection。這延續前面模組的 ownership 原則。

## 【測試】shutdown 測試要觀察明確條件

Shutdown 測試的核心是確認停止訊號能讓元件退出，而不是等待固定時間。

```go
func TestWorkerStopsOnContextCancel(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    done := make(chan struct{})

    go func() {
        defer close(done)
        _ = RunWorker(ctx)
    }()

    cancel()

    select {
    case <-done:
    case <-time.After(time.Second):
        t.Fatalf("worker did not stop")
    }
}
```

HTTP server 測試可以啟動 server 後 cancel context，確認 `RunHTTPServer` 回傳。測試應使用隨機 port 或 `httptest.Server`，避免固定 port 造成衝突。

## 本章不處理

本章不討論 Kubernetes preStop hook、terminationGracePeriod、systemd unit 或雲端 load balancer 的所有細節。這些會影響 shutdown 時間與順序，但 Go 程式內部仍需要清楚的 context、timeout 與 cleanup owner。後續可接 [Kubernetes、systemd 與 load balancer 合約](../07-distributed-operations/deployment-contracts/)。

## 小結

Graceful shutdown 是多階段流程：signal 轉成 root context，readiness 先關閉，HTTP server 停止接新 request，worker 和 WebSocket hub 觀察 context 收尾，整體流程受 timeout 保護。停止訊號越集中，元件 ownership 越清楚，服務在部署、測試與本機開發時越不容易留下殘存 goroutine 或未釋放連線。
