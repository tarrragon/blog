---
title: "4.4 多來源 event 融合"
date: 2026-04-22
description: "合併 HTTP、queue、timer 與外部事件來源"
weight: 4
---

事件融合的核心目標是讓不同來源的同類事件進入同一套內部規則。HTTP callback、queue message、timer scan 與檔案 reader 都只是輸入方式；進入 processor 前，它們應該被轉成一致的 `DomainEvent`。

## 本章目標

學完本章後，你將能夠：

1. 分辨來源差異與 domain 規則差異
2. 為不同來源設計 adapter 與 normalize
3. 用 channel 或直接呼叫收斂事件入口
4. 為突發流量設計 backpressure 策略
5. 決定錯誤應回給上游、重試、丟棄或記錄

---

## 【觀察】來源增加後規則容易分裂

事件來源增加的核心風險是每個來源各自實作一套處理規則。HTTP handler 有一套 validation，queue consumer 有一套 retry 判斷，timer worker 又有一套狀態更新；最後同一種 domain event 在不同入口產生不同結果。

反模式示意：

```text
HTTP callback ──> validate A ──> update state A
queue message ──> validate B ──> update state B
timer scan    ──> validate C ──> update state C
```

這種結構的問題不是來源多，而是 domain 規則分裂。新增來源時，應該新增 adapter，不應複製 processor。

## 【判讀】來源差異應限制在 adapter

事件融合的核心原則是來源差異停在 adapter 與 normalizer。來源可以有不同 authentication、ack、HTTP status、payload 格式與重試語意；但轉成 `DomainEvent` 後，processor 應該面對一致模型。

目標結構：

```text
HTTP callback ─┐
queue message ─┼─> normalize ─> DomainEvent ─> processor
timer scan    ─┘
```

這個結構讓新增來源變成局部擴充。你新增一個 adapter 與 normalize test，而不是複製 validation、dedup、repository update 與 publish 邏輯。

## 【策略】先定義每個來源的責任

來源設計的核心動作是明確寫出每個 adapter 對上游的承諾。不同來源的錯誤回應方式不同，但進入 processor 的事件語意應一致。

| 來源           | adapter 責任                             | 失敗回應           |
| -------------- | ---------------------------------------- | ------------------ |
| HTTP callback  | decode JSON、驗證簽章、normalize         | 回 4xx/5xx         |
| queue consumer | decode message、控制 ack/nack、normalize | ack、nack 或 retry |
| timer scan     | 讀取本地狀態、產生內部事件               | 記錄錯誤或下次再掃 |
| file reader    | 讀取增量資料、normalize                  | 記錄 offset 或停下 |

表格不是文件裝飾，而是設計工具。若某一列寫不清楚，代表 adapter 與 processor 的邊界還不清楚。

## 【執行】HTTP adapter 轉成 DomainEvent

HTTP adapter 的核心責任是處理 HTTP 協定與外部 payload。它可以回應 status code，但不應直接決定狀態如何更新。

```go
type HTTPEventHandler struct {
    processor *EventProcessor
    now       func() time.Time
}

func (h HTTPEventHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    var raw RawHTTPEvent
    if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json")
        return
    }

    event, err := NormalizeHTTPEvent(raw, h.now())
    if err != nil {
        writeError(w, http.StatusBadRequest, "invalid_event")
        return
    }

    if err := h.processor.Process(r.Context(), event); err != nil {
        writeError(w, http.StatusServiceUnavailable, "event_not_accepted")
        return
    }

    w.WriteHeader(http.StatusAccepted)
}
```

`StatusAccepted` 表示事件已被系統接收，不一定表示所有下游推送都完成。若 API 語意要求同步完成，就需要在文件與測試中明確定義成功條件。

## 【執行】queue adapter 控制 ack/nack

queue adapter 的核心責任是把 message lifecycle 對應到 processor 結果。processor 不應知道 ack、nack 或 delivery tag。

```go
type QueueMessage struct {
    Body        []byte
    Ack         func() error
    Nack        func(requeue bool) error
}

type QueueConsumer struct {
    processor *EventProcessor
    now       func() time.Time
}

func (c QueueConsumer) Handle(ctx context.Context, msg QueueMessage) error {
    event, err := NormalizeQueueMessage(msg.Body, c.now())
    if err != nil {
        return msg.Nack(false)
    }

    if err := c.processor.Process(ctx, event); err != nil {
        return msg.Nack(true)
    }

    return msg.Ack()
}
```

這段程式把 queue 的重試決策留在 adapter。對 processor 來說，事件只是一筆 `DomainEvent`；對 queue 來說，錯誤需要轉成 ack/nack 策略。

## 【策略】共用 channel 需要 backpressure

共用 channel 的核心用途是把多個來源收斂到同一個處理 loop。它不是必要架構，但在多來源、突發流量或單一 worker 順序處理時很有用。

```go
events := make(chan DomainEvent, 1024)
```

channel 一旦有容量限制，就必須設計滿載策略。沒有滿載策略的 channel 只會把問題延後到 goroutine 堆積或 request 卡住。

```go
func EnqueueEvent(ctx context.Context, events chan<- DomainEvent, event DomainEvent) error {
    select {
    case events <- event:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    default:
        return ErrEventQueueFull
    }
}
```

HTTP handler 遇到 `ErrEventQueueFull` 可以回 `503`。queue consumer 可以 nack 並 requeue。timer scan 可以跳過本輪。不同來源的上游回應不同，但進入 channel 的事件模型相同。

## 【執行】processor loop 擁有消費節奏

processor loop 的核心責任是決定事件如何被消費與停止。它應該接受 context，並在 shutdown 時停止讀取新事件。

```go
type EventLoop struct {
    processor *EventProcessor
    events    <-chan DomainEvent
    logger    *slog.Logger
}

func (l EventLoop) Run(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case event := <-l.events:
            if err := l.processor.Process(ctx, event); err != nil {
                l.logger.Error("process event failed",
                    "event_type", event.Type,
                    "subject_id", event.SubjectID,
                    "error", err,
                )
            }
        }
    }
}
```

正式實作還要處理 channel close。若事件來源會關閉 channel，讀取時應使用 `event, ok := <-l.events`；若 channel 由長生命週期服務持有，通常由 context 控制 shutdown。

## 【判讀】錯誤策略要依來源與資料語意決定

錯誤策略的核心問題是「失敗後誰能重送，重送是否安全」。HTTP、queue、timer 的答案不同。

| 錯誤位置           | HTTP callback | queue message              | timer scan |
| ------------------ | ------------- | -------------------------- | ---------- |
| decode 失敗        | 400，不重試   | nack(false) 或 dead-letter | 記錄錯誤   |
| normalize 失敗     | 400，不重試   | nack(false) 或 dead-letter | 記錄錯誤   |
| processor 暫時失敗 | 503，可重試   | nack(true)                 | 下次再掃   |
| duplicate event    | 202 或 204    | ack                        | 忽略       |
| publisher 失敗     | 視語意而定    | 視語意而定                 | 視語意而定 |

錯誤策略不能只看技術來源，也要看資料語意。若事件已經成功更新狀態但即時推送失敗，HTTP 是否要回錯取決於 API 是否承諾推送已完成。

## 【策略】觀測欄位要跨來源一致

事件融合後的 log 與 metric 也應使用共同欄位。這讓你能跨 HTTP、queue、timer 比較同一類事件的行為。

```go
func LogAttrsForEvent(event DomainEvent) []slog.Attr {
    return []slog.Attr{
        slog.String("event_id", event.ID),
        slog.String("event_type", string(event.Type)),
        slog.String("event_source", string(event.Source)),
        slog.String("subject_id", event.SubjectID),
        slog.Time("occurred_at", event.OccurredAt),
        slog.Time("received_at", event.ReceivedAt),
    }
}
```

adapter 可以額外記錄 HTTP path、queue name 或 timer name，但共同欄位應該來自 `DomainEvent`。這樣排查問題時，讀者不用先知道事件從哪個來源進來。

## 【測試】融合測試要驗證同類事件走同一規則

多來源測試的核心目標是確認不同 adapter 產生同一種 `DomainEvent`，並且 processor 對它們套用同一組規則。

```go
func TestHTTPAndQueueNormalizeToSameDomainEvent(t *testing.T) {
    receivedAt := time.Date(2026, 4, 22, 10, 0, 10, 0, time.UTC)

    httpEvent, err := NormalizeHTTPEvent(RawHTTPEvent{
        EventID:   "evt_1",
        AccountID: "acct_1",
        EventName: "activated",
        Timestamp: "2026-04-22T10:00:00Z",
    }, receivedAt)
    if err != nil {
        t.Fatalf("normalize http event: %v", err)
    }

    queueEvent, err := NormalizeQueueMessage([]byte(`{
        "id":"evt_1",
        "subject":"acct_1",
        "type":"account.activated",
        "occurred_at":"2026-04-22T10:00:00Z"
    }`), receivedAt)
    if err != nil {
        t.Fatalf("normalize queue event: %v", err)
    }

    if httpEvent.Type != queueEvent.Type || httpEvent.SubjectID != queueEvent.SubjectID {
        t.Fatalf("sources should normalize to same domain semantics")
    }
}
```

這個測試不是要求兩個 event 完全相同。`Source` 可以不同；重點是 domain semantics 一致，processor 才能共用規則。

## 本章不處理

本章不處理完整 queue driver、dead-letter queue 操作、分散式追蹤或 durable outbox。這些是生產等級事件系統的重要部分，但它們建立在本章的基本邊界之上。後續可接 [Durable queue、outbox 與 idempotency](../07-distributed-operations/outbox-idempotency/) 以及 [Observability pipeline、metrics 與 tracing](../07-distributed-operations/observability-pipeline/)。

## 小結

事件融合的核心是把來源差異限制在 adapter 與 normalizer，讓 processor 只面對一致的 `DomainEvent`。HTTP、queue、timer 可以有不同的 backpressure 與錯誤回應，但不應複製 domain 規則。當來源增加時，系統應該增加 adapter，而不是增加另一套狀態更新流程。
