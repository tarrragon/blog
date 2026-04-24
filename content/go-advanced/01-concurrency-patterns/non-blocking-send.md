---
title: "1.3 非阻塞送出與事件丟棄策略"
date: 2026-04-22
description: "設計 channel 滿載時的服務行為"
weight: 3
---

非阻塞送出的核心取捨是用明確降級換取呼叫端可用性。當 channel 滿載時，程式可以等待、回錯、丟棄、覆蓋或轉交可靠儲存；選擇哪一個是服務語意，不是 `select` 語法偏好。

## 本章目標

學完本章後，你將能夠：

1. 分辨 blocking send 與 non-blocking send 的服務語意
2. 為 HTTP、worker、即時推送設計不同滿載策略
3. 判斷哪些事件可以丟、哪些不能丟
4. 為 drop 與 [queue](../../backend/knowledge-cards/queue) full 建立 [log](../../backend/knowledge-cards/log)/metric
5. 測試 channel 滿載時的行為

---

## 【觀察】channel 滿載是容量訊號

Channel 滿載的核心意義是下游處理速度跟不上上游輸入速度。這可能是短暫尖峰，也可能是系統長期容量不足。

最直接的 send 會接受 [backpressure](../../backend/knowledge-cards/backpressure) ：

```go
events <- event
```

如果 `events` 沒有 [buffer](../../backend/knowledge-cards/buffer)，或 buffer 已滿，sender 會等待 receiver。這能保留資料，但也可能讓 HTTP handler、connection writer 或其他 goroutine 卡住。

對批次 worker 來說，等待可能合理；對使用者 request 來說，無限等待通常會變成 [timeout](../../backend/knowledge-cards/timeout) 或 goroutine 堆積。

## 【判讀】blocking send 表示願意等待

Blocking send 的核心語意是 sender 接受下游 backpressure 。資料不會被丟掉，但 sender 的生命週期會被 receiver 影響。

有 context 的 blocking send：

```go
func Enqueue(ctx context.Context, events chan<- Event, event Event) error {
    select {
    case events <- event:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

這種寫法仍然願意等待，但不會無限等待。若 request 被取消或 timeout，send 也會停止。

Blocking send 適合資料不能丟、上游能等待、且等待時間受 context 控制的情境。若沒有 context，blocking send 在服務入口通常風險較高。

## 【判讀】non-blocking send 表示立即選擇替代路徑

Non-blocking send 的核心語意是「能送就送，不能送就立刻走其他策略」。Go 常用 `select` 加 `default` 表達。

```go
var ErrQueueFull = errors.New("event queue is full")

func TryEnqueue(events chan<- Event, event Event) error {
    select {
    case events <- event:
        return nil
    default:
        return ErrQueueFull
    }
}
```

這段程式不會等待 receiver。當 buffer 滿載時，呼叫端會立刻拿到 `ErrQueueFull`，並可以決定回 HTTP 錯誤、記錄 drop、或改走其他儲存。

Non-blocking send 不是比較進階的寫法。它只是把 backpressure 從「等待」改成「立即決策」。

## 【策略】先定義事件的保留等級

滿載策略的核心判斷是資料語意。每種事件都應先定義保留等級：必須保存、可降級、可覆蓋、可取樣，或可延後處理。這個等級決定 channel 滿載時要等待、回錯、丟棄、覆蓋或轉交可靠儲存。

| 事件類型                                                | 建議策略                       | 理由                                                                           |
| ------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------ |
| [audit log](../../backend/knowledge-cards/audit-log)    | 不應直接丟，應寫可靠儲存或回錯 | 資料遺失會破壞稽核                                                             |
| UI 即時提示                                             | 可丟棄或覆蓋                   | 使用者可重新查詢狀態                                                           |
| 狀態轉移事件                                            | 通常不應丟                     | 會造成 [source of truth](../../backend/knowledge-cards/source-of-truth) 不一致 |
| [metrics](../../backend/knowledge-cards/metrics) sample | 可取樣或丟棄                   | 趨勢比單筆資料重要                                                             |
| background refresh                                      | 可跳過本輪                     | 下次仍可重新計算                                                               |

這個表格的重點不是固定答案，而是要求每種事件都要有明確策略。若團隊只說「channel 滿了就 default」，通常代表資料語意還沒有想清楚。

## 【執行】HTTP 入口要把滿載轉成狀態碼

HTTP 入口的核心責任是把內部滿載轉成呼叫端能理解的結果。不要讓 request 一直等到 timeout，也不要把未接受的事件回成成功。

```go
func EventHandler(events chan<- Event) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        event := Event{ID: r.Header.Get("X-Request-ID")}

        if err := TryEnqueue(events, event); err != nil {
            if errors.Is(err, ErrQueueFull) {
                w.Header().Set("Retry-After", "5")
                http.Error(w, "event queue is full", http.StatusServiceUnavailable)
                return
            }
            http.Error(w, "event enqueue failed", http.StatusInternalServerError)
            return
        }

        w.WriteHeader(http.StatusAccepted)
    }
}
```

`202 Accepted` 表示事件已被服務接受進入後續處理。`503 Service Unavailable` 表示服務目前無法接受更多事件，呼叫端可以稍後重試。

若事件不能丟，HTTP handler 應該回錯或寫入可靠儲存，不應假裝成功。

## 【執行】即時推送可以選擇 drop 或 disconnect

即時推送的核心問題是慢 client 不能拖住整個服務。若某個連線的 send buffer 滿了，服務要決定丟掉該訊息、丟掉舊訊息，還是關閉連線。

```go
type Client struct {
    send chan Message
}

func (c *Client) TrySend(message Message) bool {
    select {
    case c.send <- message:
        return true
    default:
        return false
    }
}
```

呼叫端可以根據 `false` 決定策略：

```go
if ok := client.TrySend(message); !ok {
    metrics.Inc("client_send_dropped")
    logger.Warn("drop client message", "reason", "send_buffer_full")
}
```

對狀態型 UI 來說，丟掉中間更新可能可以接受，因為下一次 snapshot 會補上最新狀態。對逐筆不可遺失訊息來說，應改用可靠佇列或明確斷線重連協定。

## 【策略】buffer 只能吸收短暫尖峰

Buffer 的核心作用是平滑短時間流量差，不是解決長期處理能力不足。把 channel buffer 調大，只是延後滿載時間，也可能增加記憶體與延遲。

```go
events := make(chan Event, 1024)
```

設計 buffer 時至少要考慮：

- 單筆事件大小
- [producer](../../backend/knowledge-cards/producer) 峰值速度
- [consumer](../../backend/knowledge-cards/consumer) 穩定處理速度
- 允許排隊延遲
- 滿載時的回應策略

若 producer 每秒 1000 筆、consumer 每秒 100 筆，任何有限 buffer 都會滿。這時要改善 consumer 能力、增加 worker、做取樣、回錯或使用可靠 queue，而不是只調大數字。

## 【策略】丟棄一定要可觀測

Drop strategy 的核心要求是可觀測。只要系統選擇丟棄或降級，就應該留下 metric 或 structured log，否則資料遺失會變成隱性 bug。

```go
func TryEnqueueWithMetrics(events chan<- Event, event Event, logger *slog.Logger) error {
    select {
    case events <- event:
        metrics.Inc("event_enqueue_success")
        return nil
    default:
        metrics.Inc("event_enqueue_dropped")
        logger.Warn("drop event",
            "reason", "queue_full",
            "event_type", event.Type,
            "subject_id", event.SubjectID,
        )
        return ErrQueueFull
    }
}
```

Log 適合保留單次事件脈絡，metric 適合觀察趨勢。若 drop rate 升高，代表服務正在降級；這應該能被監控看見。

## 【測試】滿載行為要直接測

Non-blocking send 的測試核心是先讓 channel 滿載，再確認函式立刻回錯。不要用 sleep 等待「可能會滿」。

```go
func TestTryEnqueueReturnsQueueFull(t *testing.T) {
    events := make(chan Event, 1)
    events <- Event{ID: "already_full"}

    err := TryEnqueue(events, Event{ID: "next"})
    if !errors.Is(err, ErrQueueFull) {
        t.Fatalf("error = %v, want ErrQueueFull", err)
    }
}
```

Blocking send with context 也可以測：

```go
func TestEnqueueStopsWhenContextCanceled(t *testing.T) {
    events := make(chan Event)
    ctx, cancel := context.WithCancel(context.Background())
    cancel()

    err := Enqueue(ctx, events, Event{ID: "evt_1"})
    if !errors.Is(err, context.Canceled) {
        t.Fatalf("error = %v, want context canceled", err)
    }
}
```

這些測試把滿載和取消變成可重現條件，不需要依賴時間推測。

## 本章不處理

本章先處理單一 process 內的滿載處理策略；當訊息需要持久化、重試或跨 process 傳遞時，會在下列章節再往外延伸：

- [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)
- [Go 進階：Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)

## 和 Go 教材的關係

這一章承接的是 channel backpressure 、worker capacity 與事件丟棄策略；如果你要先回看語言教材，可以讀：

- [Go：channel：資料傳遞與 backpressure ](../../go/04-concurrency/channel/)
- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：rate limiting 與 backpressure ](rate-limit/)
- [Go：多來源 event 融合](../../go-advanced/04-architecture-boundaries/event-fusion/)

## 小結

非阻塞送出是服務策略，不是語法技巧。Channel 滿載時，系統必須明確選擇等待、回錯、丟棄、覆蓋或轉交可靠儲存。選擇之前先定義事件的保留等級，選擇之後補上 log、metric 與測試，才能讓 backpressure 成為可管理的服務行為。
