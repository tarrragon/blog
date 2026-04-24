---
title: "4.1 事件來源、處理流程與狀態邊界"
date: 2026-04-22
description: "分辨事件來源、事件融合、處理流程、狀態真相與推送邊界"
weight: 1
---

事件系統的核心邊界是把「收到訊號」、「轉成事件」、「套用規則」、「更新狀態」與「輸出結果」拆開。每個邊界都應該有自己的型別與測試，否則一個 handler 或 worker 很快就會同時負責協定、驗證、去重、狀態與推送。

## 本章目標

學完本章後，你將能夠：

1. 分辨 event source、normalizer、processor、repository、publisher 的責任
2. 用 Go interface 表達元件能力，而不是表達資料夾模板
3. 把外部格式限制在 adapter 內
4. 讓狀態更新集中到 repository 或 state owner
5. 用測試驗證每個邊界是否可替換

---

## 【觀察】事件流程容易被寫成一團

事件流程膨脹的常見原因是入口程式碼太方便。HTTP handler 可以 decode JSON、驗證欄位、查 map、送通知；worker 也可以讀 [queue](/backend/knowledge-cards/queue/)、判斷重複、更新狀態、寫 [log](/backend/knowledge-cards/log/)。短期看起來直接，長期會讓每個入口都複製一套規則。

反模式示意：

```go
func handleCallback(w http.ResponseWriter, r *http.Request) {
    var raw CallbackPayload
    json.NewDecoder(r.Body).Decode(&raw)

    if raw.ID == "" {
        http.Error(w, "missing id", http.StatusBadRequest)
        return
    }

    if seen[raw.ID] {
        w.WriteHeader(http.StatusNoContent)
        return
    }

    seen[raw.ID] = true
    states[raw.AccountID] = "active"
    hub.Broadcast(raw.AccountID, "active")
}
```

這段程式的問題不是行數，而是責任混在一起。HTTP 協定、輸入格式、去重策略、狀態更新與推送規則都被綁在同一個函式，任何一項改變都會影響整個入口。

## 【判讀】事件邊界應該按照責任切開

事件邊界的核心規則是每一層只知道自己必須知道的資訊。adapter 知道外部協定，normalizer 知道格式轉換，processor 知道事件規則，repository 知道狀態保存，publisher 知道輸出方式。

一個可維護的事件流程可以長這樣：

```text
HTTP / queue / timer
        │
        ▼
    adapter
        │ raw input
        ▼
   normalizer
        │ DomainEvent
        ▼
   processor
        │
        ├── deduper
        ├── repository
        └── publisher
```

這不是資料夾要求，而是依賴方向。外部來源依賴內部事件模型；內部處理流程不依賴外部 raw payload。

## 【策略】先定義內部事件模型

內部事件模型的核心責任是提供穩定語意。不同來源可以有不同欄位名稱與時間格式，但進入 processor 前都應轉成同一種事件。

```go
type EventType string

const (
    EventNotificationCreated EventType = "notification.created"
    EventAccountActivated    EventType = "account.activated"
    EventJobFinished         EventType = "job.finished"
)

type EventSource string

const (
    SourceHTTPCallback EventSource = "http_callback"
    SourceQueue        EventSource = "queue"
    SourceTimer        EventSource = "timer"
)

type DomainEvent struct {
    ID         string
    Source     EventSource
    Type       EventType
    SubjectID  string
    OccurredAt time.Time
    ReceivedAt time.Time
    Payload    json.RawMessage
}
```

`OccurredAt` 是事件發生時間，`ReceivedAt` 是系統收到時間。這兩個欄位要分開，因為外部事件可能延遲送達；去重與排序通常看事件語意時間，操作監控通常看收到時間。

## 【執行】adapter 只負責外部格式

adapter 的核心責任是把外部輸入轉成內部事件或 command。它可以知道 JSON tag、HTTP status、queue [ack](/backend/knowledge-cards/ack-nack/)、header，但不應直接修改狀態。

```go
type CallbackPayload struct {
    EventID   string `json:"event_id"`
    AccountID string `json:"account_id"`
    EventName string `json:"event_name"`
    Timestamp string `json:"timestamp"`
}

type CallbackHandler struct {
    processor *EventProcessor
    now       func() time.Time
}

func (h CallbackHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    var payload CallbackPayload
    if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json")
        return
    }

    event, err := NormalizeCallback(payload, h.now())
    if err != nil {
        writeError(w, http.StatusBadRequest, "invalid_event")
        return
    }

    if err := h.processor.Process(r.Context(), event); err != nil {
        writeError(w, http.StatusInternalServerError, "process_event_failed")
        return
    }

    w.WriteHeader(http.StatusAccepted)
}
```

handler 的測試應該檢查 HTTP 行為與 normalize 錯誤對應。事件規則的測試不應透過 HTTP handler 才能執行，否則 processor 的變化會被協定細節干擾。

## 【執行】normalizer 負責轉換與基本合約

normalizer 的核心責任是把 raw input 轉成 `DomainEvent`，並拒絕語意不完整的資料。它是外部世界與內部模型的邊界。

```go
func NormalizeCallback(raw CallbackPayload, receivedAt time.Time) (DomainEvent, error) {
    occurredAt, err := time.Parse(time.RFC3339, raw.Timestamp)
    if err != nil {
        return DomainEvent{}, fmt.Errorf("parse timestamp: %w", err)
    }

    event := DomainEvent{
        ID:         strings.TrimSpace(raw.EventID),
        Source:     SourceHTTPCallback,
        Type:       mapCallbackEventName(raw.EventName),
        SubjectID:  strings.TrimSpace(raw.AccountID),
        OccurredAt: occurredAt,
        ReceivedAt: receivedAt,
    }

    if err := event.Validate(); err != nil {
        return DomainEvent{}, err
    }
    return event, nil
}

func (e DomainEvent) Validate() error {
    if e.ID == "" {
        return fmt.Errorf("event id is required")
    }
    if e.Type == "" {
        return fmt.Errorf("event type is required")
    }
    if e.SubjectID == "" {
        return fmt.Errorf("subject id is required")
    }
    if e.OccurredAt.IsZero() {
        return fmt.Errorf("occurred at is required")
    }
    if e.ReceivedAt.IsZero() {
        return fmt.Errorf("received at is required")
    }
    return nil
}
```

validation 應該保護 envelope 的必要欄位。更細的 payload 規則可以放在特定事件的 normalizer 或 processor，避免 `Validate` 變成所有事件的巨大規則表。

## 【執行】processor 負責事件規則

processor 的核心責任是套用內部事件規則。它可以驗證、去重、更新狀態、寫入事件紀錄、呼叫 publisher，但不應知道 HTTP body 或 queue message 的原始格式。

```go
type EventRepository interface {
    Apply(ctx context.Context, event DomainEvent) error
}

type Deduper interface {
    Seen(ctx context.Context, event DomainEvent) (bool, error)
}

type Publisher interface {
    Publish(ctx context.Context, event DomainEvent) error
}

type EventProcessor struct {
    deduper    Deduper
    repository EventRepository
    publisher  Publisher
}

func (p *EventProcessor) Process(ctx context.Context, event DomainEvent) error {
    if err := event.Validate(); err != nil {
        return err
    }

    duplicated, err := p.deduper.Seen(ctx, event)
    if err != nil {
        return fmt.Errorf("dedup event: %w", err)
    }
    if duplicated {
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

這個 processor 依賴能力介面，不依賴具體實作。Go 的 implicit interface 讓 memory repository、[database](/backend/knowledge-cards/database/) repository 或測試 fake 都可以自然接上。

## 【判讀】publisher 失敗策略必須明確

publisher 的核心問題是「輸出失敗是否影響狀態成功」。即時通知、審計紀錄、外部 [webhook](/backend/knowledge-cards/webhook/) 的可靠性要求不同，不能一律用同一個錯誤策略。

常見策略：

| 輸出類型     | 失敗策略                   | 適用情境                 |
| ------------ | -------------------------- | ------------------------ |
| 即時 UI 推送 | 記錄錯誤，可允許狀態已更新 | 客戶端可重新查詢最新狀態 |
| 事件紀錄     | 失敗時中止流程             | 紀錄是不可遺失的資料     |
| 外部 webhook | 寫入 outbox，稍後重試      | 下游需要可靠接收         |

若 `repository.Apply` 成功但 `publisher.Publish` 失敗，系統必須知道這是可接受的降級，還是需要重試與補償。這個決策應該寫在 processor 或 usecase 的設計裡，不應藏在 publisher implementation。

## 【測試】每個邊界分開測

事件邊界的測試目標是讓錯誤定位清楚。normalizer 測 raw input 轉換，processor 測規則順序，repository 測狀態一致性，publisher 測輸出協定。

processor fake test 範例：

```go
func TestProcessorSkipsDuplicateEvent(t *testing.T) {
    processor := EventProcessor{
        deduper:    fakeDeduper{duplicated: true},
        repository: &fakeRepository{},
        publisher:  &fakePublisher{},
    }

    err := processor.Process(context.Background(), DomainEvent{
        ID:         "evt_1",
        Type:       EventAccountActivated,
        SubjectID:  "acct_1",
        OccurredAt: time.Now(),
        ReceivedAt: time.Now(),
    })
    if err != nil {
        t.Fatalf("process event: %v", err)
    }

    if processor.repository.(*fakeRepository).applied {
        t.Fatalf("duplicate event should not update repository")
    }
}
```

這種測試不需要 HTTP server。它直接驗證 processor 的規則：重複事件不應更新狀態，也不應送出推送。

## 本章不處理

本章先處理單一 Go 服務內的事件來源與處理邊界；分散式一致性與 event sourcing，會在下列章節再往外延伸：

- [Go 進階：資料庫 transaction 與 schema migration](/go-advanced/07-distributed-operations/database-transactions/)
- [Go 進階：Durable queue、outbox 與 idempotency](/go-advanced/07-distributed-operations/outbox-idempotency/)
- [Backend：資料庫與持久化](/backend/01-database/)

## 和 Go 教材的關係

這一章承接的是 action、event、repository 與 publisher 的邊界；如果你要先回看語言教材，可以讀：

- [Go：如何新增一個即時訊息 action](/go/06-practical/new-websocket-action/)
- [Go：如何新增一種 domain event](/go/06-practical/new-event-type/)
- [Go：用 interface 隔離外部依賴](/go/07-refactoring/interface-boundary/)
- [Go：逐步遷移到 ports/adapters 架構](/go/07-refactoring/hexagonal-migration/)

## 小結

事件系統的可維護性來自清楚邊界：adapter 處理外部格式，normalizer 建立內部事件，processor 套用規則，repository 擁有狀態，publisher 輸出結果。當每個元件只承擔一種責任時，新增來源、新增事件或替換儲存實作都會變成局部修改。
