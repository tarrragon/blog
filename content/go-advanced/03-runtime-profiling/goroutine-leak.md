---
title: "3.3 goroutine leak 偵測"
date: 2026-04-22
description: "判斷背景工作與 client pump 是否正確退出"
weight: 3
---

Goroutine leak 偵測的核心目標是確認已經沒有存在價值的 goroutine 能被停止。它通常不是語法問題，而是生命週期問題：誰取消、誰 close、誰解除 I/O 阻塞、誰停止 ticker。

## 本章目標

學完本章後，你將能夠：

1. 分辨合理長期 goroutine 與 goroutine leak
2. 用 context、done channel、connection close 設計退出路徑
3. 用 pprof goroutine profile 判讀卡住 stack
4. 測試 worker、ticker、WebSocket pump 是否能退出
5. 從 leak pattern 回到 ownership 修正

---

## 【觀察】goroutine leak 是生命週期沒有結束

Goroutine leak 的核心定義是某個 goroutine 已經沒有存在價值，卻仍然活著。它可能卡在 channel receive、channel send、network read、ticker、mutex 或永遠不會觸發的 select case。

反模式：

```go
func StartWorker(jobs <-chan Job) {
    go func() {
        for job := range jobs {
            process(job)
        }
    }()
}
```

這個 worker 只有在 `jobs` 被關閉時才會退出。若呼叫端永遠不關閉 `jobs`，而 worker 也沒有 context，這個 goroutine 可能永久存在。

長期存在不一定是 leak。HTTP server accept loop、metrics exporter、background scheduler 都可能合理存在；問題是它們是否有明確停止條件，且 shutdown 時是否真的會走到。

## 【判讀】每個 goroutine 都要有退出原因

Goroutine lifecycle 的核心檢查是每個 goroutine 都能回答三個問題：

1. 誰要求它停止？
2. 它如果卡在 channel 或 I/O，如何被喚醒？
3. 它停止後如何讓測試或上層知道？

若三題任一題答不出來，就有 leak 風險。

例如 worker 應該有 context：

```go
func RunWorker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-jobs:
            if !ok {
                return
            }
            process(job)
        }
    }
}
```

這個 worker 有兩條退出路徑：上層取消 context，或 jobs channel 被關閉。這比只依賴 channel close 更容易整合到服務 shutdown。

## 【策略】I/O 阻塞需要 deadline 或 close

I/O goroutine 的核心風險是 context 本身不一定能打斷底層阻塞呼叫。WebSocket read、TCP read、file watcher、外部 API call 都要確認是否支援 context、deadline 或 close。

WebSocket read pump 常見退出方式：

```go
func (c *Client) readPump(ctx context.Context, hub *Hub, router MessageRouter) {
    defer func() {
        hub.unregister <- c
    }()

    for {
        var message ClientMessage
        if err := c.conn.ReadJSON(&message); err != nil {
            return
        }
        _ = router.Route(ctx, c, message)
    }
}
```

若 `ReadJSON` 卡住，context 取消不一定直接讓它返回。實務上需要 read deadline、connection close 或 heartbeat 讓 read pump 有機會退出。

## 【執行】done channel 讓測試能觀察退出

測試 goroutine 是否退出的核心問題是需要可觀察訊號。`done` channel 可以在 goroutine 結束時 close。

```go
func RunWorker(ctx context.Context, jobs <-chan Job, done chan<- struct{}) {
    defer close(done)

    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-jobs:
            if !ok {
                return
            }
            process(job)
        }
    }
}
```

測試：

```go
func TestRunWorkerStops(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    jobs := make(chan Job)
    done := make(chan struct{})

    go RunWorker(ctx, jobs, done)
    cancel()

    select {
    case <-done:
    case <-time.After(time.Second):
        t.Fatalf("worker did not stop")
    }
}
```

Timeout 是測試保護，不是功能本身。真正的退出訊號是 `done` 被關閉。

## 【執行】ticker 必須停止

Ticker leak 的核心原因是建立 ticker 後沒有呼叫 `Stop`。Ticker 會持有 runtime 資源；長時間服務若反覆建立不停止，會累積不必要成本。

```go
func RunCleanup(ctx context.Context) {
    ticker := time.NewTicker(time.Minute)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            cleanup()
        }
    }
}
```

`defer ticker.Stop()` 應緊跟在成功建立 ticker 後。這樣不管函式因 context、錯誤或 channel 關閉退出，ticker 都會被停止。

`time.After` 在一次性 timeout 很方便，但在高頻迴圈裡反覆建立 timer 可能造成額外配置。需要重複觸發時，優先使用 `Ticker` 或可重設的 `Timer` 並明確停止。

## 【判讀】pprof goroutine profile 看 stack pattern

Goroutine profile 的核心價值是顯示 goroutine stack。當 goroutine 數量持續上升時，先看它們卡在哪裡。

```bash
curl "http://localhost:8080/debug/pprof/goroutine?debug=2"
```

常見 pattern：

| stack 類型      | 可能原因                             | 回到哪個邊界              |
| --------------- | ------------------------------------ | ------------------------- |
| channel receive | 上游不會再送，也沒 close/context     | channel ownership         |
| channel send    | 下游不再接收或 buffer 滿             | backpressure / unregister |
| network read    | 沒有 deadline 或 connection 未 close | heartbeat / I/O lifecycle |
| ticker loop     | context 沒接上或 ticker 未 stop      | select loop lifecycle     |
| mutex lock      | 鎖競爭或死鎖                         | shared state owner        |

看到 stack 後，下一步不是只殺 goroutine，而是回到對應 lifecycle 設計：誰負責停止，誰負責釋放阻塞點。

## 【策略】WebSocket pump leak 要看 read/write/unregister 三方

WebSocket goroutine leak 的核心常見原因是 read pump、write pump、hub unregister 沒有形成閉環。

目標流程：

```text
read pump error 或 connection close
        │
        ▼
hub unregister
        │
        ├── close client.send
        └── close conn
        │
        ▼
write pump exits
```

若 hub 沒有 close `send`，write pump 可能一直等。若 connection 沒有 close，read pump 可能卡在 read。若 unregister 不是 idempotent，重複 close 可能 panic。

Goroutine profile 若顯示大量 goroutine 卡在 `writePump` 的 send receive，通常要檢查 `client.send` 是否會被 close。若卡在 `ReadJSON`，要檢查 read deadline、heartbeat 與 connection close。

## 【測試】用 goroutine 數量做粗略回歸檢查

Goroutine 數量測試的核心用途是粗略檢查是否有明顯 leak。它不是精準證明，因為 Go runtime 與測試環境本身也會有 goroutine。

```go
func TestNoObviousGoroutineLeak(t *testing.T) {
    before := runtime.NumGoroutine()

    ctx, cancel := context.WithCancel(context.Background())
    done := make(chan struct{})
    go func() {
        defer close(done)
        RunWorker(ctx, make(chan Job))
    }()

    cancel()
    select {
    case <-done:
    case <-time.After(time.Second):
        t.Fatalf("worker did not stop")
    }

    eventually(t, time.Second, func() bool {
        return runtime.NumGoroutine() <= before+2
    })
}
```

這類測試要留緩衝，避免因 runtime 或其他測試 goroutine 造成假失敗。更可靠的測試仍是等待明確 `done` 訊號。

## 【判讀】goroutine leak 修正要改停止路徑

Goroutine leak 的核心修正不是在 goroutine 裡加更多條件，而是補上停止路徑。

常見修正：

- 加入 `ctx.Done()` case。
- 關閉由自己擁有的 output channel。
- 由 coordinator 等 sender 完成再 close。
- 對 network read/write 設定 deadline。
- shutdown 時 close connection。
- ticker 建立後 `defer Stop()`。
- hub unregister 時 close send channel。

修正後要用測試證明退出路徑真的會發生，再用 pprof 或 goroutine count 驗證趨勢。

## 本章不處理

本章先處理 goroutine 的啟動、停止與阻塞邊界；更完整的 worker 全域治理，會在下列章節再往外延伸：

- [Go 進階：channel ownership 與關閉責任](../01-concurrency-patterns/channel-ownership/)
- [Go 進階：bounded worker pool](../01-concurrency-patterns/worker-pool/)
- [Go 進階：select loop 的生命週期設計](../01-concurrency-patterns/select-loop/)

## 和 Go 教材的關係

這一章承接的是 goroutine lifecycle、channel 與 shutdown；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與背壓](../../go/04-concurrency/channel/)
- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：如何新增背景工作流程](../../go/06-practical/new-background-worker/)

## 小結

Goroutine leak 是生命週期問題。每個長期 goroutine 都應知道誰能停止它、如何解除阻塞、如何讓測試觀察退出。Context、done channel、deadline、connection close、ticker stop 與 hub unregister 是主要工具。pprof goroutine profile 則用來確認還活著的 goroutine 卡在哪個邊界。
