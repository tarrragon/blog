---
title: "6.5 如何新增結構化記錄欄位"
date: 2026-04-22
description: "區分 operational log、domain event log 與狀態資料"
weight: 5
---

新增結構化記錄欄位的核心規則是先判斷這筆資訊是給工程師除錯、給系統重播，還是給使用者查詢。不同用途對應不同記錄邊界，資料應依用途進入 [log](../../backend/knowledge-cards/log)、[event log](../../backend/knowledge-cards/event-log) 或 repository。

## 本章目標

學完本章後，你將能夠：

1. 分辨 structured log、domain event log 與 state repository
2. 設計穩定的 log 欄位名稱
3. 判斷哪些資料不應寫進 log
4. 用 `EventLog.Append` 表達事件記錄邊界
5. 測試穩定欄位，而不是測自由文字

---

## 【觀察】先判斷記錄用途

記錄邊界的核心問題是資料要服務誰。工程師除錯、系統重播、使用者查詢是三種不同用途，對應三種不同儲存與格式責任。

| 記錄類型         | 用途                          | 範例                                                                             |
| ---------------- | ----------------------------- | -------------------------------------------------------------------------------- |
| structured log   | 操作診斷、除錯、聚合查詢      | [queue](../../backend/knowledge-cards/queue) full、event rejected、worker failed |
| domain event log | 記錄已發生事實、audit、replay | `notification.created`、`job.failed`                                             |
| state repository | 查詢目前狀態或投影            | job current status、notification summary                                         |

structured log 服務操作診斷，event log 保存 normalized fact，state repository 回答目前狀態。先分清楚用途，才知道欄位該放哪裡。

## 【判讀】structured log 是操作訊號

structured log 的核心用途是讓工程師知道系統正在發生什麼，並且能用欄位查詢。它應該記錄操作訊號，而不是完整業務資料。

```go
logger.Info(
    "event accepted",
    "layer", "adapter",
    "event_type", string(event.Type),
    "event_id", event.ID,
    "subject_id", event.SubjectID,
    "correlation_id", event.CorrelationID,
)
```

`message` 給人讀，欄位給查詢工具使用。若未來要查某種事件是否大量進入系統，`event_type` 欄位比文字搜尋更可靠。

常見 log 欄位可以先定義成 helper，避免不同地方拼出不同名稱：

```go
func LogAttrsForEvent(event DomainEvent) []any {
    return []any{
        "event_id", event.ID,
        "event_type", string(event.Type),
        "subject_kind", string(event.SubjectKind),
        "subject_id", event.SubjectID,
        "correlation_id", event.CorrelationID,
        "schema_version", event.SchemaVersion,
    }
}
```

使用時可以展開欄位：

```go
logger.Info("event accepted", LogAttrsForEvent(event)...)
```

這個 helper 保護的是 [log schema](../../backend/knowledge-cards/log-schema)。欄位名稱穩定，查詢與 [dashboard](../../backend/knowledge-cards/dashboard) 才能穩定。

## 【策略】reason 欄位要像 enum

`reason` 的核心語意是可聚合的原因分類。它應使用小集合穩定值；完整錯誤訊息則放在 `error` 欄位協助診斷。

```go
const (
    ReasonInvalidPayload = "invalid_payload"
    ReasonQueueFull      = "queue_full"
    ReasonDuplicateEvent = "duplicate_event"
    ReasonTimeout        = "timeout"
)
```

記錄拒絕事件時：

```go
logger.Warn(
    "event rejected",
    "layer", "adapter",
    "reason", ReasonInvalidPayload,
    "event_type", string(event.Type),
    "error", err,
)
```

`reason` 用來統計，`error` 用來診斷，message 用來讓人快速理解。這三者不要混成一個大字串。

## 【判讀】event log 記錄 normalized fact

domain event log 的核心責任是保存已正規化的 domain event。它記錄的是系統承認的事實；raw request、debug log 與目前狀態分別屬於不同記錄邊界。

先定義 port：

```go
type EventLog interface {
    Append(ctx context.Context, event DomainEvent) error
}
```

memory implementation 可以先這樣寫：

```go
type InMemoryEventLog struct {
    mu     sync.Mutex
    events []DomainEvent
}

func NewInMemoryEventLog() *InMemoryEventLog {
    return &InMemoryEventLog{}
}

func (l *InMemoryEventLog) Append(ctx context.Context, event DomainEvent) error {
    l.mu.Lock()
    defer l.mu.Unlock()

    l.events = append(l.events, cloneDomainEvent(event))
    return nil
}
```

event log 應該保存 `DomainEvent` envelope 中的穩定欄位，例如 event ID、type、subject、schema version、occurred/received time。它不需要保存 adapter 的 raw input，除非你已經明確設計 raw [audit log](../../backend/knowledge-cards/audit-log)。

## 【執行】event log 要保護 copy boundary

event log 的核心資料也是內部狀態。若 event 包含 slice、map 或 `json.RawMessage`，append 與讀取時都要避免外部修改內部資料。

```go
func cloneDomainEvent(event DomainEvent) DomainEvent {
    cloned := event
    if event.Payload != nil {
        cloned.Payload = append(json.RawMessage(nil), event.Payload...)
    }
    return cloned
}
```

若要提供查詢方法，也要回傳複製資料：

```go
func (l *InMemoryEventLog) List() []DomainEvent {
    l.mu.Lock()
    defer l.mu.Unlock()

    result := make([]DomainEvent, len(l.events))
    for i, event := range l.events {
        result[i] = cloneDomainEvent(event)
    }
    return result
}
```

這裡展示的是教學用記錄邊界。真正 event store 還需要持久化、排序、[schema [migration](../../backend/knowledge-cards/migration)](../../backend/knowledge-cards/schema-migration)、重播策略與交易語意。

## 【策略】state repository 保存目前狀態

state repository 的核心責任是回答目前狀態。它可以由 event 更新，但用途不同於保存所有歷史事實的 event log。

例如：

```go
type JobRepository interface {
    Apply(ctx context.Context, event DomainEvent) error
    Get(ctx context.Context, id string) (JobProjection, bool, error)
}
```

event log 和 state repository 可以在 processor 中各自被呼叫：

```go
type RecordingEventProcessor struct {
    eventLog   EventLog
    repository JobRepository
    logger     *slog.Logger
}

func (p *RecordingEventProcessor) Process(ctx context.Context, event DomainEvent) error {
    if err := p.eventLog.Append(ctx, event); err != nil {
        return fmt.Errorf("append event log: %w", err)
    }

    if err := p.repository.Apply(ctx, event); err != nil {
        return fmt.Errorf("apply state projection: %w", err)
    }

    p.logger.Info("event processed", LogAttrsForEvent(event)...)
    return nil
}
```

這段程式展示三種記錄邊界：event log 保存事實，repository 更新目前狀態，structured log 記錄操作訊號。

## 【判讀】記錄位置要跟錯誤發生層一致

記錄位置的核心規則是在哪一層能提供最多上下文，就在哪一層記錄。同一個錯誤通常選擇一個主要層次記錄，避免 log 被重複訊號淹沒。

常見位置：

| 發生位置       | 應記錄內容                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------ |
| adapter        | raw input decode/normalize 失敗                                                            |
| router/usecase | command 被拒絕、權限不足、狀態不允許                                                       |
| processor      | event validation、dedup、[projection](../../backend/knowledge-cards/projection) apply 結果 |
| worker         | queue full、外部來源失敗、重試結果                                                         |

例如 adapter 解碼失敗：

```go
logger.Warn(
    "callback rejected",
    "layer", "adapter",
    "reason", ReasonInvalidPayload,
    "payload_bytes", len(body),
)
```

這裡記錄 payload 大小即可診斷資料是否異常；完整 payload 可能包含敏感資料或過大內容。

## 【策略】敏感資料預設不進 log

敏感資料邊界的核心規則是 log 會被保存、轉發與搜尋，所以 token、password、完整 payload、完整個資應排除在 log 之外。

可以記錄：

- ID 或 opaque identifier
- payload byte length
- schema version
- 欄位是否存在
- hash 或 checksum

不應記錄：

- password
- access token
- cookie
- 完整 request body
- 完整 personal data

若需要追蹤同一筆資料，可以記錄安全識別碼：

```go
logger.Debug(
    "payload received",
    "payload_bytes", len(body),
    "payload_sha256", sha256Hex(body),
)
```

debug log 也需要遵守同樣規則；只要可能被集中收集，就要先控制敏感資料。

## 【執行】log helper 測試只測穩定欄位

log helper 測試的核心目標是保護欄位名稱與值。log message 文案是給人讀的內容，通常保留調整空間。

```go
func TestLogAttrsForEvent(t *testing.T) {
    event := DomainEvent{
        ID:            "evt_1",
        Type:          EventNotificationCreated,
        SubjectKind:   SubjectNotification,
        SubjectID:     "ntf_1",
        CorrelationID: "corr_1",
        SchemaVersion: 1,
    }

    attrs := LogAttrsForEvent(event)
    got := attrsToMap(attrs)

    if got["event_id"] != "evt_1" {
        t.Fatalf("event_id = %v, want evt_1", got["event_id"])
    }
    if got["event_type"] != string(EventNotificationCreated) {
        t.Fatalf("event_type = %v, want %s", got["event_type"], EventNotificationCreated)
    }
}
```

測試輔助函式可以把 key-value slice 轉成 map：

```go
func attrsToMap(attrs []any) map[string]any {
    result := make(map[string]any)
    for i := 0; i+1 < len(attrs); i += 2 {
        key, ok := attrs[i].(string)
        if !ok {
            continue
        }
        result[key] = attrs[i+1]
    }
    return result
}
```

這個測試直接檢查 helper 輸出，不需要真的寫 log 或解析 logger output。

## 【執行】event log 測試要保護 append 與 copy

event log 測試的核心目標是確認事件被 append，且外部無法透過原始 payload 或回傳值修改內部紀錄。

```go
func TestInMemoryEventLogAppendCopiesPayload(t *testing.T) {
    log := NewInMemoryEventLog()
    payload := json.RawMessage(`{"topic":"deployments"}`)

    event := DomainEvent{
        ID:            "evt_1",
        Type:          EventNotificationCreated,
        SubjectKind:   SubjectNotification,
        SubjectID:     "ntf_1",
        OccurredAt:    time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
        ReceivedAt:    time.Date(2026, 4, 22, 10, 1, 0, 0, time.UTC),
        SchemaVersion: 1,
        Payload:       payload,
    }

    if err := log.Append(context.Background(), event); err != nil {
        t.Fatalf("append event: %v", err)
    }

    payload[0] = '['

    events := log.List()
    if string(events[0].Payload) != `{"topic":"deployments"}` {
        t.Fatalf("payload was modified through original slice")
    }
}
```

`json.RawMessage` 本質是 `[]byte`，所以需要 copy。這類細節很容易被忽略，測試可以把邊界固定下來。

## 實作檢查清單

新增結構化記錄欄位時，可以依序檢查：

1. 這筆資料是給除錯、重播，還是查詢
2. structured log 是否只保存操作訊號與安全欄位
3. event log 是否保存 normalized domain event
4. state repository 是否只保存目前 projection
5. log 欄位名稱是否穩定
6. `reason` 是否是小集合分類
7. 是否避免完整 payload 與敏感資料
8. event log 是否保護 copy boundary
9. 測試是否檢查穩定欄位，而不是自由文字

## 設計檢查

### 檢查一：log 服務操作診斷

log 是操作診斷訊號，不是穩定查詢 API。需要使用者查詢的目前狀態，應該進 repository 或 [read model](../../backend/knowledge-cards/read-model)。

### 檢查二：event log 保存 normalized fact

event log 記錄的是 normalized fact。若把暫時性錯誤、debug 訊息與 raw payload 全塞進 event log，重播與 audit 會變得不可信。

### 檢查三：欄位名稱維持一致

`event_id`、`eventID`、`id` 混用會讓查詢失效。欄位 schema 要像 API 一樣維持穩定。

### 檢查四：完整 payload 需要明確策略

完整 payload 可能包含敏感資料，也可能非常大。除非有明確安全與保存策略，否則只記錄大小、hash、ID 與必要欄位。

## 本章不處理

本章先處理 log、event log 與 repository 的分工；集中式 log 平台與可重播事件系統，會在下列章節再往外延伸：

- [Go 進階：Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)
- [Go 進階：Observability pipeline、metrics 與 tracing](../../go-advanced/07-distributed-operations/observability-pipeline/)
- [Backend：可觀測性平台](../../backend/04-observability/)

## 和 Go 教材的關係

這一章承接的是 event log、state repository 與 log schema；如果你要先回看語言教材，可以讀：

- [Go：如何新增一種 domain event](new-event-type/)
- [Go：如何新增 repository port](repository-port/)
- [Go：用 interface 隔離外部依賴](../../go/07-refactoring/interface-boundary/)
- [Go：結構化日誌欄位設計](../../go-advanced/06-production-operations/log-fields/)

## 小結

結構化記錄的重點是用途分流。structured log 幫工程師除錯，domain event log 保存已發生事實，state repository 提供目前狀態查詢。新增欄位前先問「這筆資訊要服務誰」，再決定它該進 log、event log 還是 repository。這個判斷比選擇任何 logging package 都重要。
