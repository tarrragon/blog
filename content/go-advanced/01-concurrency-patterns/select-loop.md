---
title: "1.2 select loop 的生命週期設計"
date: 2026-04-22
description: "理解長時間運行 goroutine 如何同時處理事件、ticker 與取消"
weight: 2
---

`select` loop 的核心責任是管理長時間 goroutine 的生命週期。它不只是等待多個 channel 的語法，而是決定元件如何接收輸入、處理定時任務、回應取消、釋放資源與停止。

## 本章目標

學完本章後，你將能夠：

1. 拆解 `select` loop 中每個 case 的責任
2. 用 `ctx.Done()` 設計一致的退出路徑
3. 正確建立與停止 ticker
4. 處理 channel 關閉後的 nil channel pattern
5. 測試 worker 在事件、ticker、取消下的行為

---

## 【觀察】長期 goroutine 通常同時等待多種訊號

長期 goroutine 的核心特徵是它不只處理一種資料。背景 worker 可能同時等待外部事件、定時掃描、清理工作與停止訊號。

```go
func (w Worker) Run(ctx context.Context) error {
    statusTicker := time.NewTicker(w.statusInterval)
    defer statusTicker.Stop()

    cleanupTicker := time.NewTicker(w.cleanupInterval)
    defer cleanupTicker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case event, ok := <-w.events:
            if !ok {
                return nil
            }
            w.processEvent(ctx, event)
        case <-statusTicker.C:
            w.scanStatus(ctx)
        case <-cleanupTicker.C:
            w.cleanup(ctx)
        }
    }
}
```

這個 loop 的責任不是「跑一個無限迴圈」，而是定義 worker 活著時能接受哪些訊號，以及停止時要如何退出。

## 【判讀】select loop 是元件的生命週期表

`select` loop 的核心價值是把元件生命週期寫成明確表格。每個 case 都應該能回答：收到什麼訊號、代表什麼意思、下一步做什麼。

| case              | 系統意義           | 下一步             |
| ----------------- | ------------------ | ------------------ |
| `ctx.Done()`      | 上層要求停止       | 回傳 context error |
| `w.events`        | 收到外部事件       | 套用處理流程       |
| `statusTicker.C`  | 到時間掃描狀態     | 執行週期任務       |
| `cleanupTicker.C` | 到時間清理暫存資料 | 回收資源           |

若某個 case 的意義說不清楚，通常代表 worker 責任太多，或事件來源還沒有被整理成清楚的 channel。

## 【策略】每個長期 goroutine 先回答四個問題

Select loop 設計的核心檢查是生命週期，而不是語法。寫 loop 前先回答四個問題：

1. 誰能停止它？
2. 它消費哪些輸入？
3. 它擁有哪些資源？
4. 停止時要回報錯誤、靜默退出，還是交給上層判斷？

例如：

```go
type Worker struct {
    events          <-chan Event
    statusInterval  time.Duration
    cleanupInterval time.Duration
    processor       Processor
}
```

`Worker` 消費 `events`，擁有兩個 ticker，停止訊號來自 `context.Context`。這些資訊應該能從型別與 `Run` 方法看出來，而不是藏在任意 goroutine 裡。

## 【執行】ticker 要由使用者停止

Ticker 的核心規則是建立者負責停止。`time.NewTicker` 會建立 runtime 資源；不再使用時應呼叫 `Stop`。

```go
func (w Worker) Run(ctx context.Context) error {
    ticker := time.NewTicker(w.interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            if err := w.SyncOnce(ctx); err != nil {
                return err
            }
        }
    }
}
```

Ticker 放在 `Run` 裡建立，表示它的生命週期和 `Run` 一致。`defer ticker.Stop()` 讓 worker 不論因為 context、錯誤或 channel 關閉退出，都能釋放 ticker。

如果 ticker 由外部傳入，外部就應該負責停止。擁有權要一致，否則測試和 shutdown 都會變得模糊。

## 【執行】處理已關閉 channel 要避免忙等

已關閉 channel 的核心行為是讀取會立即回傳零值與 `ok=false`。在 `select` loop 裡，如果不處理這件事，loop 可能一直選到同一個已關閉 channel。

當一個輸入關閉後，還要繼續處理其他輸入，可以把它設成 nil：

```go
func (w Worker) Run(ctx context.Context) error {
    events := w.events
    alerts := w.alerts

    for events != nil || alerts != nil {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case event, ok := <-events:
            if !ok {
                events = nil
                continue
            }
            w.processEvent(ctx, event)
        case alert, ok := <-alerts:
            if !ok {
                alerts = nil
                continue
            }
            w.processAlert(ctx, alert)
        }
    }

    return nil
}
```

Nil channel 在 `select` 中永遠不會 ready。這讓 worker 能在某個來源關閉後繼續處理其他來源，而不是忙等或提早退出。

## 【判讀】default case 會改變 loop 的語意

`default` 的核心效果是讓 `select` 不等待。這在非阻塞送出很有用，但在長期 worker 的主 loop 中要小心，因為它可能造成 busy loop。

反模式：

```go
for {
    select {
    case <-ctx.Done():
        return
    case event := <-events:
        process(event)
    default:
        cleanup()
    }
}
```

當沒有事件時，這個 loop 會不停執行 `cleanup()`，可能吃滿 CPU。週期任務應該用 ticker 表達，不應用 `default` 假裝閒置時執行。

較清楚的做法：

```go
cleanupTicker := time.NewTicker(time.Minute)
defer cleanupTicker.Stop()

for {
    select {
    case <-ctx.Done():
        return
    case event := <-events:
        process(event)
    case <-cleanupTicker.C:
        cleanup()
    }
}
```

Ticker 讓頻率明確，也讓測試可以透過可控時間或手動觸發 channel 驗證行為。

## 【策略】長工作要移出主要 loop

Select loop 的核心風險是某個 case 裡的工作太久，導致其他訊號無法被處理。若 `processEvent` 可能執行很久，worker 在這段期間就不會回應 context 或 ticker。

可選策略：

| 策略                     | 適用情境                 | 代價                     |
| ------------------------ | ------------------------ | ------------------------ |
| case 內同步執行          | 工作短、需要順序處理     | 慢事件會阻塞整個 loop    |
| 啟動 bounded [worker pool](../../backend/knowledge-cards/worker-pool) | 工作可並行、需要限制併發 | 需要排隊與 shutdown 設計 |
| 送入另一個 [queue](../../backend/knowledge-cards/queue)         | 入口要快速接收           | 需要 [backpressure](../../backend/knowledge-cards/backpressure) 策略   |

長工作需要 bounded worker pool、另一個 queue 或明確的同步策略。無限制地在 case 裡 `go process(event)` 只會把排隊問題從 channel 轉成 goroutine 堆積，並讓 shutdown 和錯誤回報更難處理。

## 【測試】把單次工作抽成方法

Select loop 的測試核心是避免所有邏輯都只能透過無限迴圈測。把單次工作抽成 `SyncOnce`、`ProcessOne` 或 `CleanupOnce`，可以讓規則測試和 lifecycle 測試分開。

```go
func (w Worker) SyncOnce(ctx context.Context) error {
    return w.processor.Sync(ctx)
}
```

`Run` 只負責排程：

```go
case <-ticker.C:
    if err := w.SyncOnce(ctx); err != nil {
        return err
    }
```

單次工作測試：

```go
func TestSyncOnceCallsProcessor(t *testing.T) {
    processor := &fakeProcessor{}
    worker := Worker{processor: processor}

    if err := worker.SyncOnce(context.Background()); err != nil {
        t.Fatalf("sync once: %v", err)
    }
    if !processor.called {
        t.Fatalf("processor should be called")
    }
}
```

Lifecycle 測試則只確認 context 取消能讓 `Run` 退出：

```go
func TestRunStopsOnContextCancel(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    cancel()

    worker := Worker{
        events:          make(chan Event),
        statusInterval:  time.Hour,
        cleanupInterval: time.Hour,
    }

    if err := worker.Run(ctx); !errors.Is(err, context.Canceled) {
        t.Fatalf("run error = %v, want context canceled", err)
    }
}
```

這種拆法讓測試不需要等待真實 ticker，也不需要在無限 loop 裡猜時間。

## 本章不處理

本章先把長生命週期 goroutine 的停止、輸入與排空講清楚；更完整的 worker 協調與平台排程責任，會在下列章節再往外延伸：

- [Go 進階：bounded worker pool](worker-pool/)
- [Go 進階：graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/)
- [Backend：可靠性驗證流程](../../backend/06-reliability/)

## 和 Go 教材的關係

這一章承接的是 goroutine、channel 與 shutdown loop；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與 backpressure ](../../go/04-concurrency/channel/)
- [Go：bounded worker pool](worker-pool/)
- [Go：graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/)

## 小結

`select` loop 是長期 goroutine 的生命週期表。好的 loop 會明確處理 context 取消、輸入 channel、ticker、資源釋放與 channel 關閉。避免在主 loop 中濫用 `default` 或無限制開 goroutine，才能讓服務在高流量、錯誤與 shutdown 情境下保持可預測。
