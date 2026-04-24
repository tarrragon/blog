---
title: "6.4 如何新增背景工作流程"
date: 2026-04-22
description: "接入 context、channel 與 shutdown"
weight: 4
---

新增背景工作流程的核心規則是先定義生命週期，再定義資料流。worker 是有 context、輸入、輸出、錯誤處理與 shutdown 協定的長期元件。

## 本章目標

學完本章後，你將能夠：

1. 判斷一段工作是否適合做成 worker
2. 用 `Run(ctx)` 設計 worker 生命週期
3. 用 channel 和 ticker 表達資料流與週期性工作
4. 處理 [queue](../../backend/knowledge-cards/queue) full、shutdown 與錯誤記錄
5. 分開測試 `SyncOnce`、`Run(ctx)` 與 channel 行為

---

## 【觀察】worker 是有生命週期的元件

worker 的核心定義是長時間運行、可被啟動、可被取消、會消費輸入或定期執行工作的元件。任意程式碼包進 `go func()` 只能產生背景 goroutine，還需要生命週期協定才會成為可維護的 worker。

適合做成 worker 的工作通常有三種：

| 工作類型                                                 | 範例                     | worker 責任                           |
| -------------------------------------------------------- | ------------------------ | ------------------------------------- |
| queue [consumer](../../backend/knowledge-cards/consumer) | 從 channel 讀取外部事件  | 驗證、轉送 processor                  |
| periodic task                                            | 每 30 秒同步一次外部狀態 | 產生 command 或 event                 |
| cleanup task                                             | 定期清理過期資料         | 呼叫 repository 或 usecase 的清理方法 |

本章使用「通知同步 worker」作為範例。它定期向外部來源取得通知更新，轉成 domain event，再交給 `EventProcessor` 處理。

## 【判讀】worker 責任要先寫清楚

worker 責任的核心問題是它消費什麼、產生什麼、交給誰處理。worker 應聚焦在資料取得、格式轉換與轉交處理器，業務規則、狀態更新與 client 推送要留給對應的 usecase 或 processor。

先定義外部來源：

```go
type NotificationSource interface {
    FetchUpdates(ctx context.Context) ([]RawNotificationUpdate, error)
}

type RawNotificationUpdate struct {
    ID             string
    NotificationID string
    Topic          string
    Title          string
    OccurredAt     time.Time
}
```

再定義 worker 會呼叫的處理器：

```go
type EventProcessor interface {
    Process(ctx context.Context, event DomainEvent) error
}
```

worker 的責任是把外部更新取回來、normalize 成 `DomainEvent`、交給 processor。repository 寫入與推送規則仍然留在 processor 或 usecase 裡。

## 【策略】把單次工作獨立成 `SyncOnce`

worker 的核心設計技巧是把「單次工作」和「長時間迴圈」分開。`SyncOnce` 負責做一次同步，`Run(ctx)` 負責週期性呼叫它。

```go
type SyncWorker struct {
    source    NotificationSource
    processor EventProcessor
    logger    *slog.Logger
}

func NewSyncWorker(source NotificationSource, processor EventProcessor, logger *slog.Logger) *SyncWorker {
    return &SyncWorker{
        source:    source,
        processor: processor,
        logger:    logger,
    }
}
```

`SyncOnce` 可以像普通函式一樣測試：

```go
func (w *SyncWorker) SyncOnce(ctx context.Context) error {
    updates, err := w.source.FetchUpdates(ctx)
    if err != nil {
        return fmt.Errorf("fetch notification updates: %w", err)
    }

    for _, update := range updates {
        event, err := NormalizeNotificationUpdate(update, time.Now())
        if err != nil {
            w.logger.Warn("skip invalid notification update", "id", update.ID, "error", err)
            continue
        }

        if err := w.processor.Process(ctx, event); err != nil {
            return fmt.Errorf("process notification update %s: %w", update.ID, err)
        }
    }

    return nil
}
```

這裡的 `time.Now()` 先展示基本寫法；如果測試需要固定時間，可以把 clock 注入進 worker。時間注入會在後面測試章節更完整處理。

## 【執行】`Run(ctx)` 管理長時間生命週期

`Run(ctx)` 的核心責任是等待 ticker、呼叫單次工作、尊重取消訊號。它應該在 context 被取消時退出，並釋放 ticker。

```go
func (w *SyncWorker) Run(ctx context.Context, interval time.Duration) error {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            if err := w.SyncOnce(ctx); err != nil {
                w.logger.Error("sync worker failed", "error", err)
            }
        }
    }
}
```

這個版本把單次同步錯誤記錄下來，但不讓 worker 退出。這是策略選擇：若外部來源短暫失敗，worker 可以等待下一輪；若錯誤代表設定失效或授權失效，則可以選擇 return error 讓上層重啟或停止服務。

worker 錯誤策略應該明確。暫時性錯誤通常要記錄後等待下一輪；致命設定錯誤則可以回傳給上層，讓服務決定重啟或停止。

## 【判讀】channel worker 要設計 backpressure

channel worker 的核心問題是接收端跟不上時要怎麼辦。[buffer](../../backend/knowledge-cards/buffer) 大小、blocking send、non-blocking send 都是在回答 [backpressure](../../backend/knowledge-cards/backpressure) 策略。

假設外部 HTTP callback 會把 raw update 送進 worker queue：

```go
type QueueWorker struct {
    updates   chan RawNotificationUpdate
    processor EventProcessor
    logger    *slog.Logger
}

func NewQueueWorker(processor EventProcessor, logger *slog.Logger, bufferSize int) *QueueWorker {
    return &QueueWorker{
        updates:   make(chan RawNotificationUpdate, bufferSize),
        processor: processor,
        logger:    logger,
    }
}
```

送入 queue 可以選擇 blocking 或 non-blocking。若呼叫端不能被背景處理拖慢，可以用 non-blocking send 並回傳錯誤：

```go
var ErrQueueFull = errors.New("notification update queue full")

func (w *QueueWorker) Enqueue(update RawNotificationUpdate) error {
    select {
    case w.updates <- update:
        return nil
    default:
        return ErrQueueFull
    }
}
```

這個設計很誠實：queue 滿了就是系統忙碌。上層可以記錄 [log](../../backend/knowledge-cards/log)、回 `503`，或告訴 client 稍後重試。

## 【執行】queue worker 要同時監聽輸入與取消

queue worker 的核心生命週期是等待 update 或 context cancel。`Run(ctx)` 裡應用 `select` 同時處理這兩件事。

```go
func (w *QueueWorker) Run(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case update, ok := <-w.updates:
            if !ok {
                return nil
            }
            if err := w.handleUpdate(ctx, update); err != nil {
                w.logger.Error("handle notification update failed", "id", update.ID, "error", err)
            }
        }
    }
}
```

`handleUpdate` 負責單筆資料轉換與處理：

```go
func (w *QueueWorker) handleUpdate(ctx context.Context, update RawNotificationUpdate) error {
    event, err := NormalizeNotificationUpdate(update, time.Now())
    if err != nil {
        return fmt.Errorf("normalize update: %w", err)
    }
    return w.processor.Process(ctx, event)
}
```

這裡仍然遵守同一條邊界：worker 不直接改 repository，只把事件交給 processor。

## 【策略】shutdown 是否 drain queue 要先決定

shutdown 的核心決策是取消時要立刻停止，還是處理完 queue 中既有資料。兩種策略都合理，但語意不同。

| 策略        | 做法                           | 適用情境             |
| ----------- | ------------------------------ | -------------------- |
| 立即停止    | 收到 `ctx.Done()` 就 return    | 即時通知、可重試資料 |
| drain queue | 停止接收新資料，處理已排隊資料 | 不可輕易丟棄的資料   |

立即停止比較簡單：

```go
case <-ctx.Done():
    return ctx.Err()
```

drain queue 則需要另一個停止接收的協定，例如由擁有送出端的一方關閉 channel，再讓 worker range 到 channel 關閉。channel close 的所有權要留在送出端，因為送出端最清楚是否還會送資料。

這裡的核心區分是「取消 context」和「關閉 channel」代表不同訊號。context 表示這件工作該停了；channel close 表示不會再有新資料。兩者可以搭配，但語意不同。

## 【判讀】worker 使用服務生命週期 context

worker context 的核心規則是：長時間 worker 使用服務生命週期 context，單次工作可以另外接收 request context。某個 HTTP request 的 context 只適合控制該次請求；request 結束後 context 會被取消。

```go
func (w *QueueWorker) Enqueue(update RawNotificationUpdate) error {
    select {
    case w.updates <- update:
        return nil
    default:
        return ErrQueueFull
    }
}
```

`Enqueue` 不把 request context 存起來。真正處理 update 時，worker 使用自己的 `Run(ctx)` context 控制生命週期。

若某筆 update 需要保留 [request ID](../../backend/knowledge-cards/request-id) 或 [correlation ID](../../backend/knowledge-cards/correlation-id)，應把它放進明確欄位，而不是依賴 context value 在背景工作中長期存在。

## 【執行】`SyncOnce` 測試要隔離時間與外部來源

`SyncOnce` 測試的核心目標是確認單次工作會把外部資料交給 processor。測試重點放在單次同步，不需要等待真實 ticker。

```go
type fakeNotificationSource struct {
    updates []RawNotificationUpdate
    err     error
}

func (f fakeNotificationSource) FetchUpdates(ctx context.Context) ([]RawNotificationUpdate, error) {
    if f.err != nil {
        return nil, f.err
    }
    return f.updates, nil
}

type recordingProcessor struct {
    events []DomainEvent
}

func (p *recordingProcessor) Process(ctx context.Context, event DomainEvent) error {
    p.events = append(p.events, event)
    return nil
}
```

測試單次同步：

```go
func TestSyncWorkerSyncOnce(t *testing.T) {
    source := fakeNotificationSource{
        updates: []RawNotificationUpdate{
            {
                ID:             "evt_1",
                NotificationID: "ntf_1",
                Topic:          "deployments",
                Title:          "Deploy finished",
                OccurredAt:     time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
            },
        },
    }
    processor := &recordingProcessor{}
    worker := NewSyncWorker(source, processor, slog.Default())

    if err := worker.SyncOnce(context.Background()); err != nil {
        t.Fatalf("sync once: %v", err)
    }

    if len(processor.events) != 1 {
        t.Fatalf("processed events = %d, want 1", len(processor.events))
    }
}
```

這個測試不需要 goroutine。先把單次工作測清楚，再測長時間生命週期。

## 【執行】`Run(ctx)` 測試要能快速取消

`Run(ctx)` 測試的核心目標是確認 worker 會尊重取消訊號。測試應該使用已取消或很短的 context，讓測試快速結束。

```go
func TestSyncWorkerRunStopsWhenContextCanceled(t *testing.T) {
    source := fakeNotificationSource{}
    processor := &recordingProcessor{}
    worker := NewSyncWorker(source, processor, slog.Default())

    ctx, cancel := context.WithCancel(context.Background())
    cancel()

    err := worker.Run(ctx, time.Hour)
    if !errors.Is(err, context.Canceled) {
        t.Fatalf("error = %v, want context.Canceled", err)
    }
}
```

這個測試用 `time.Hour` 當 interval，因為 context 已經取消，`Run` 應該立刻退出，不需要等 ticker。

## 【執行】queue full 測試要固定 buffer

queue full 測試的核心目標是確認 backpressure 策略。buffer 設成 1，先塞滿，再確認第二次 enqueue 回錯。

```go
func TestQueueWorkerEnqueueFull(t *testing.T) {
    worker := NewQueueWorker(&recordingProcessor{}, slog.Default(), 1)

    err := worker.Enqueue(RawNotificationUpdate{ID: "evt_1"})
    if err != nil {
        t.Fatalf("first enqueue: %v", err)
    }

    err = worker.Enqueue(RawNotificationUpdate{ID: "evt_2"})
    if !errors.Is(err, ErrQueueFull) {
        t.Fatalf("error = %v, want ErrQueueFull", err)
    }
}
```

這個測試不啟動 worker，所以 channel 裡第一筆資料不會被消費，第二筆必然遇到 full。這比用 sleep 製造滿載狀態穩定。

## 實作檢查清單

新增 background worker 時，可以依序檢查：

1. worker 責任是否明確：消費什麼，產生什麼，交給誰
2. 是否有 `Run(ctx)` 作為生命週期入口
3. 單次工作是否拆成 `SyncOnce` 或 `handleUpdate`
4. worker 是否尊重 `ctx.Done()`
5. ticker 是否 `defer Stop()`
6. channel buffer 是否有明確 backpressure 策略
7. queue full 是否回錯或記錄，而不是靜默丟棄
8. worker 是否呼叫 usecase/processor，而不是直接改 repository
9. 測試是否避免真實長時間 sleep

## 設計檢查

### 檢查一：goroutine 要有停止條件

長時間 goroutine 需要 context、channel close 或其他退出條件。缺少停止條件時，服務運行越久，越容易累積難以診斷的資源問題。

### 檢查二：worker 透過 processor 或 usecase 修改狀態

worker 透過 processor 或 usecase 修改狀態，可以讓背景流程和即時流程共用同一套規則。worker 直接改 repository 時，狀態規則容易分散。

### 檢查三：queue full 要有明確策略

資料可以丟時，應明確記錄 log 或 metric；資料需要保留時，應 blocking 或回錯。queue full 策略明確，後續追蹤才有依據。

### 檢查四：測試隔離真實時間

測試優先測 `SyncOnce`，再用已取消 context 測 `Run` 的退出行為。真實 ticker 等待數秒會讓測試慢且不穩。

## 本章不處理

本章先處理單一背景工作如何啟動、停止與回報；cron、queue、retry 與 outbox，會在下列章節再往外延伸：

- [Go 進階：bounded worker pool](../../go-advanced/01-concurrency-patterns/worker-pool/)
- [Go 進階：select loop 的生命週期設計](../../go-advanced/01-concurrency-patterns/select-loop/)
- [Go 進階：Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)
- [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)

## 和 Go 教材的關係

這一章承接的是 goroutine 生命週期與 event processing；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../go/04-concurrency/goroutine/)
- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：channel：資料傳遞與 backpressure ](../../go/04-concurrency/channel/)
- [Go：如何新增一種 domain event](../../go/06-practical/new-event-type/)

## 小結

background worker 的重點是生命週期與資料流。`Run(ctx)` 負責啟動、等待與停止；`SyncOnce` 或 `handleUpdate` 負責單次工作；channel 和 ticker 負責輸入節奏；processor 或 usecase 負責真正的行為規則。把這些責任分清楚，worker 才能在服務長時間運行時保持可測、可停、可觀測。
