---
title: "6.2 如何新增一種 domain event"
date: 2026-04-22
description: "擴展事件常數、輸入驗證與處理流程"
weight: 2
---

新增 domain event 的核心流程是先定義事件語意，再決定哪些外部來源可以轉成這個事件。事件不是常數清單而已，而是系統內部對「發生了什麼」的穩定合約。

## 本章目標

學完本章後，你將能夠：

1. 判斷 event type 是否代表穩定 domain fact
2. 用 `DomainEvent` envelope 承接不同外部來源
3. 把 raw input 轉成內部事件，而不是直接更新狀態
4. 設計 validation 與 dedup key
5. 把 normalize、processor 與 repository 測試分開

---

## 【觀察】event type 代表已經發生的事

domain event 的核心語意是「某件對系統有意義的事已經發生」。它不是 command，也不是 client 想做的事；command 表達意圖，event 表達事實。

例如：

| 名稱                     | 類型           | 語意                |
| ------------------------ | -------------- | ------------------- |
| `subscribe_topic`        | command/action | client 想訂閱 topic |
| `notification.created`   | event          | 一筆通知已建立      |
| `job.started`            | event          | 一個 job 已開始     |
| `account.status_changed` | event          | account 狀態已改變  |

event type 應該用過去式或事實語氣。`notification.create` 比較像指令，`notification.created` 才像事件。這個命名差異會影響後續設計：事件處理器應該處理已發生事實，而不是決定是否允許 client 執行某個意圖。

用 typed constant 可以集中 event type：

```go
type EventType string

const (
    EventNotificationCreated EventType = "notification.created"
    EventJobStarted          EventType = "job.started"
    EventAccountStatusChanged EventType = "account.status_changed"
)
```

若 event type 只是為了對應外部欄位名稱，還沒有內部語意，就不應急著加入 domain event。先把外部 raw input normalize，再判斷它是否真的代表一個穩定事實。

## 【判讀】DomainEvent 是內部事件合約

`DomainEvent` 的核心責任是提供統一 envelope，讓不同來源的事件進入系統後使用同一種語意模型。HTTP callback、client action、timer 或 queue message 都可以被 adapter 轉成 `DomainEvent`。

```go
type EventSource string

const (
    SourceClientCommand EventSource = "client_command"
    SourceHTTPCallback  EventSource = "http_callback"
    SourceTimer         EventSource = "timer"
)

type SubjectKind string

const (
    SubjectNotification SubjectKind = "notification"
    SubjectJob          SubjectKind = "job"
    SubjectAccount      SubjectKind = "account"
)

type DomainEvent struct {
    ID            string          `json:"id"`
    Source        EventSource     `json:"source"`
    Type          EventType       `json:"type"`
    SubjectID     string          `json:"subjectId"`
    SubjectKind   SubjectKind     `json:"subjectKind"`
    CorrelationID string          `json:"correlationId,omitempty"`
    CausationID   string          `json:"causationId,omitempty"`
    OccurredAt    time.Time       `json:"occurredAt"`
    ReceivedAt    time.Time       `json:"receivedAt"`
    SchemaVersion int             `json:"schemaVersion"`
    Payload       json.RawMessage `json:"payload,omitempty"`
}
```

`SubjectID` 和 `SubjectKind` 用來描述事件作用在哪個對象上。`OccurredAt` 表示事件實際發生時間，`ReceivedAt` 表示系統收到事件的時間。這兩個時間不能混用，因為外部事件可能延遲送達。

`CorrelationID` 用來串起同一個使用者操作或 request 造成的一串事件。`CausationID` 用來記錄這筆事件是由哪個 command 或事件引起。初期可以先保留欄位，不必一開始就建立完整 tracing 系統。

## 【策略】payload 是補充資料，不是主要語意

event envelope 的核心語意應該放在固定欄位，不應全部藏在 `Payload`。`Payload` 適合存事件特有資料，但事件分類、主體、時間與來源應該是第一層欄位。

例如通知建立事件的 payload 可以是：

```go
type NotificationCreatedPayload struct {
    Topic string `json:"topic"`
    Title string `json:"title"`
}
```

建立 event 時，把穩定欄位放在 envelope：

```go
func NewNotificationCreatedEvent(id string, notificationID string, payload NotificationCreatedPayload, now time.Time) (DomainEvent, error) {
    data, err := json.Marshal(payload)
    if err != nil {
        return DomainEvent{}, fmt.Errorf("marshal notification payload: %w", err)
    }

    return DomainEvent{
        ID:            id,
        Source:        SourceClientCommand,
        Type:          EventNotificationCreated,
        SubjectID:     notificationID,
        SubjectKind:   SubjectNotification,
        OccurredAt:    now,
        ReceivedAt:    now,
        SchemaVersion: 1,
        Payload:       data,
    }, nil
}
```

這個函式把事件建立規則集中起來。未來若要補 schema version、correlation ID 或預設時間，也不需要在每個呼叫端重複組 struct。

## 【執行】adapter 負責 raw input 轉換

adapter 的核心責任是把外部格式轉成內部事件。它不應直接更新 repository，也不應把 raw payload 原封不動丟給 domain layer。

假設外部 HTTP callback 長這樣：

```go
type RawNotificationCallback struct {
    EventID        string `json:"event_id"`
    NotificationID string `json:"notification_id"`
    EventName      string `json:"event_name"`
    Topic          string `json:"topic"`
    Title          string `json:"title"`
    Timestamp      string `json:"timestamp"`
}
```

normalize 函式可以把它轉成 `DomainEvent`：

```go
func NormalizeNotificationCallback(raw RawNotificationCallback, receivedAt time.Time) (DomainEvent, error) {
    occurredAt, err := time.Parse(time.RFC3339, raw.Timestamp)
    if err != nil {
        return DomainEvent{}, fmt.Errorf("parse callback timestamp: %w", err)
    }

    payload := NotificationCreatedPayload{
        Topic: raw.Topic,
        Title: raw.Title,
    }

    data, err := json.Marshal(payload)
    if err != nil {
        return DomainEvent{}, fmt.Errorf("marshal callback payload: %w", err)
    }

    event := DomainEvent{
        ID:            raw.EventID,
        Source:        SourceHTTPCallback,
        Type:          EventNotificationCreated,
        SubjectID:     raw.NotificationID,
        SubjectKind:   SubjectNotification,
        OccurredAt:    occurredAt,
        ReceivedAt:    receivedAt,
        SchemaVersion: 1,
        Payload:       data,
    }

    if err := event.Validate(); err != nil {
        return DomainEvent{}, err
    }

    return event, nil
}
```

這段程式把外部欄位名稱、時間格式與 payload 組裝限制在 adapter 內。下游 processor 只需要理解 `DomainEvent`，不需要知道 callback 原始格式。

## 【判讀】validation 保護事件合約

event validation 的核心目標是拒絕語意不完整的事件。缺少 ID、type、subject 或時間的 event 不應進入 processor，否則狀態更新與去重都會失去依據。

```go
func (e DomainEvent) Validate() error {
    if strings.TrimSpace(e.ID) == "" {
        return fmt.Errorf("event id is required")
    }
    if e.Type == "" {
        return fmt.Errorf("event type is required")
    }
    if strings.TrimSpace(e.SubjectID) == "" {
        return fmt.Errorf("subject id is required")
    }
    if e.SubjectKind == "" {
        return fmt.Errorf("subject kind is required")
    }
    if e.OccurredAt.IsZero() {
        return fmt.Errorf("occurred at is required")
    }
    if e.ReceivedAt.IsZero() {
        return fmt.Errorf("received at is required")
    }
    if e.SchemaVersion <= 0 {
        return fmt.Errorf("schema version must be positive")
    }
    return nil
}
```

validation 應該檢查事件 envelope 的基本合約。更細的 payload 規則可以在 normalize 或 processor 中處理，依資料來源與用途決定。

## 【策略】去重鍵應建立在 domain 語意上

event dedup 的核心規則是使用語意鍵，而不是直接比對 raw payload。不同來源可能用不同格式描述同一件事，但只要 subject、type 與時間窗口相同，就可能是重複事件。

```go
type DedupKey struct {
    SubjectKind SubjectKind
    SubjectID   string
    Type        EventType
    Window      int64
}

func NewDedupKey(event DomainEvent, window time.Duration) DedupKey {
    return DedupKey{
        SubjectKind: event.SubjectKind,
        SubjectID:   event.SubjectID,
        Type:        event.Type,
        Window:      event.OccurredAt.UnixNano() / int64(window),
    }
}
```

去重鍵不應包含 `ReceivedAt`、raw metadata 或 request ID 這類每次都可能不同的欄位。那些欄位適合記錄觀測資訊，不適合作為「是否同一件事」的判斷依據。

若事件 ID 由可靠上游產生，可以優先用 event ID 去重。若上游 ID 不穩定，才需要 domain dedup key。這個選擇應該寫成明確規則，而不是藏在 map key 的拼接方式裡。

## 【執行】processor 負責套用事件規則

event processor 的核心責任是驗證、去重、更新狀態與發布結果。processor 不負責讀 HTTP request，也不負責解析 WebSocket message。

```go
type EventRepository interface {
    Apply(ctx context.Context, event DomainEvent) error
}

type EventPublisher interface {
    Publish(ctx context.Context, event DomainEvent) error
}

type Deduper interface {
    Seen(event DomainEvent) bool
}
```

processor 可以依賴這些小介面：

```go
type EventProcessor struct {
    repository EventRepository
    publisher  EventPublisher
    deduper    Deduper
}

func NewEventProcessor(repository EventRepository, publisher EventPublisher, deduper Deduper) *EventProcessor {
    return &EventProcessor{
        repository: repository,
        publisher:  publisher,
        deduper:    deduper,
    }
}
```

處理流程保持短而明確：

```go
func (p *EventProcessor) Process(ctx context.Context, event DomainEvent) error {
    if err := event.Validate(); err != nil {
        return fmt.Errorf("validate event: %w", err)
    }

    if p.deduper.Seen(event) {
        return nil
    }

    if err := p.repository.Apply(ctx, event); err != nil {
        return fmt.Errorf("apply event: %w", err)
    }

    if err := p.publisher.Publish(ctx, event); err != nil {
        return fmt.Errorf("publish event: %w", err)
    }

    return nil
}
```

這個 processor 不知道資料來自哪裡，也不知道 repository 是 memory map 還是資料庫。這種邊界讓新增 event source 時不需要重寫狀態規則。

## 【執行】normalize 測試要固定外部輸入

normalize 測試的核心目標是確認 raw input 會被轉成正確內部事件。這類測試應該固定時間，避免測試依賴真實現在時間。

```go
func TestNormalizeNotificationCallback(t *testing.T) {
    receivedAt := time.Date(2026, 4, 22, 10, 1, 0, 0, time.UTC)
    raw := RawNotificationCallback{
        EventID:        "evt_1",
        NotificationID: "ntf_1",
        EventName:      "notification_created",
        Topic:          "deployments",
        Title:          "Deploy finished",
        Timestamp:      "2026-04-22T10:00:00Z",
    }

    event, err := NormalizeNotificationCallback(raw, receivedAt)
    if err != nil {
        t.Fatalf("normalize callback: %v", err)
    }

    if event.Type != EventNotificationCreated {
        t.Fatalf("event type = %q, want %q", event.Type, EventNotificationCreated)
    }
    if event.SubjectID != "ntf_1" {
        t.Fatalf("subject ID = %q, want %q", event.SubjectID, "ntf_1")
    }
    if !event.ReceivedAt.Equal(receivedAt) {
        t.Fatalf("received at = %v, want %v", event.ReceivedAt, receivedAt)
    }
}
```

這個測試不需要 repository，也不需要 publisher。它只保護 adapter 的轉換規則。

## 【執行】processor 測試要隔離外部來源

processor 測試的核心目標是確認事件規則被正確套用。測試應該直接建立 `DomainEvent`，而不是從 HTTP 或 WebSocket 開始。

```go
type fakeEventRepository struct {
    applied []DomainEvent
}

func (f *fakeEventRepository) Apply(ctx context.Context, event DomainEvent) error {
    f.applied = append(f.applied, event)
    return nil
}

type fakeEventPublisher struct {
    published []DomainEvent
}

func (f *fakeEventPublisher) Publish(ctx context.Context, event DomainEvent) error {
    f.published = append(f.published, event)
    return nil
}

type neverSeenDeduper struct{}

func (neverSeenDeduper) Seen(event DomainEvent) bool {
    return false
}
```

成功案例可以確認 repository 與 publisher 都被呼叫：

```go
func TestEventProcessorProcess(t *testing.T) {
    repo := &fakeEventRepository{}
    publisher := &fakeEventPublisher{}
    processor := NewEventProcessor(repo, publisher, neverSeenDeduper{})

    event := DomainEvent{
        ID:            "evt_1",
        Source:        SourceHTTPCallback,
        Type:          EventNotificationCreated,
        SubjectID:     "ntf_1",
        SubjectKind:   SubjectNotification,
        OccurredAt:    time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
        ReceivedAt:    time.Date(2026, 4, 22, 10, 1, 0, 0, time.UTC),
        SchemaVersion: 1,
    }

    if err := processor.Process(context.Background(), event); err != nil {
        t.Fatalf("process event: %v", err)
    }

    if len(repo.applied) != 1 {
        t.Fatalf("applied events = %d, want 1", len(repo.applied))
    }
    if len(publisher.published) != 1 {
        t.Fatalf("published events = %d, want 1", len(publisher.published))
    }
}
```

processor 測試不應依賴真實 message broker 或資料庫。那些屬於 adapter integration test，不是 processor 單元測試。

## 實作檢查清單

新增 domain event 時，可以依序檢查：

1. event type 是否描述已經發生的事
2. event type 是否是內部穩定語意，而不是外部欄位名稱
3. envelope 是否包含 source、type、subject、occurred/received time
4. payload 是否只放事件特有補充資料
5. raw input 是否先經過 adapter normalize
6. adapter 是否不直接更新 repository
7. validation 是否保護事件基本合約
8. dedup key 是否建立在 domain 語意上
9. normalize、processor、repository 是否分開測試

## 常見錯誤

### 錯誤一：把 command 當 event

`create_notification` 是想做某件事，`notification.created` 是某件事已發生。把兩者混在一起，會讓 processor 不清楚自己是在判斷授權、執行行為，還是在套用事實。

### 錯誤二：把 raw payload 直接傳進 domain layer

raw payload 會帶有外部來源格式、命名與缺漏。domain layer 應該面對內部穩定模型，外部格式應該停在 adapter。

### 錯誤三：所有欄位都塞進 Payload

如果 type、subject、time 都藏在 payload，processor、deduper、repository 都必須解析 payload 才能做事。這會讓事件系統難測，也難以演進 schema。

### 錯誤四：用接收時間判斷事件順序

`ReceivedAt` 是系統看到事件的時間，不一定是事件發生時間。狀態轉移通常應該優先看 `OccurredAt`，再根據延遲與來源可靠度設計補償規則。

## 本章不處理

- 不建立真正的 event store。
- 不依賴任何外部 message broker。
- 不把 WebSocket message 直接當 domain event。

## 小結

新增 domain event 的重點是先定義內部事實，再處理外部來源。`DomainEvent` envelope 提供穩定欄位，adapter 負責 raw input 轉換，processor 負責驗證、去重、狀態更新與發布。當 event type、subject、time 與 payload 邊界清楚時，系統就能新增來源與輸出，而不會讓事件規則分散在 handler、worker 或 repository 裡。
