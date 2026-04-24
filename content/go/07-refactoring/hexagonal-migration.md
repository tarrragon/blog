---
title: "7.6 逐步遷移到 ports/adapters 架構"
date: 2026-04-22
description: "用 ports 與 adapters 控制 Go 服務的依賴方向"
weight: 6
---

ports/adapters 遷移的核心目標是讓 application 與 domain 不依賴外部技術細節。HTTP、[WebSocket](../../../backend/knowledge-cards/websocket/)、callback receiver、[database](../../../backend/knowledge-cards/database/) 都是 adapters；usecase 透過 ports 使用它們。

這種重構不需要一次套完整架構。Go 專案更常見的做法是先把過重 handler、外部依賴與狀態寫入切開，再在壓力最大的邊界引入 port。

## 本章目標

學完本章後，你將能夠：

1. 用依賴方向理解 ports/adapters
2. 分辨 inbound adapter 與 outbound adapter
3. 把 usecase 從 handler、repository、publisher 中切出
4. 用新功能先走新架構的方式漸進遷移
5. 驗證 import direction、usecase test 與 adapter integration test

---

## 【觀察】ports/adapters 是依賴方向

ports/adapters 的核心規則是外部技術依賴 application，而不是 application 依賴外部技術。HTTP、WebSocket、database、[queue](../../../backend/knowledge-cards/queue/) 都是可替換的邊界；usecase 應該依賴自己定義的 port。

目標方向：

```text
transport/http      ┐
transport/websocket ├─> application ──> domain
transport/callback  ┘        │
                             ▼
                      ports defined here
                             ▲
storage/memory       ┐       │
eventlog/memory      ├───────┘
publisher/websocket  ┘
```

資料夾名稱可以不同。真正重要的是 import direction：domain 不 import HTTP，application 不 import database implementation，adapter import application 並實作 application 需要的 port。

## 【判讀】inbound adapter 把外部輸入轉成 command

inbound adapter 的核心責任是接收外部訊號，轉成 application command 或 domain event。它不應直接修改 state，也不應保存業務規則。

常見 inbound adapter：

| adapter           | 輸入                | 轉換結果      |
| ----------------- | ------------------- | ------------- |
| HTTP handler      | HTTP request        | command       |
| WebSocket router  | client message      | command       |
| callback receiver | external callback   | domain event  |
| worker            | timer 或 queue item | command/event |

例如 HTTP adapter：

```go
type HTTPNotificationHandler struct {
    usecase *application.CreateNotificationUsecase
    now     func() time.Time
}

func (h HTTPNotificationHandler) Create(w http.ResponseWriter, r *http.Request) {
    var req createNotificationRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json", "request body must be valid JSON")
        return
    }

    cmd := application.CreateNotificationCommand{
        ID:        req.ID,
        Topic:     req.Topic,
        Title:     req.Title,
        CreatedAt: h.now(),
    }

    if err := h.usecase.Execute(r.Context(), cmd); err != nil {
        writeUsecaseError(w, err)
        return
    }

    w.WriteHeader(http.StatusCreated)
}
```

HTTP adapter 知道 JSON、status code、request body。usecase 不知道這些協定細節。

## 【判讀】outbound adapter 實作 application port

outbound adapter 的核心責任是實作 application 定義的 port。application 說「我需要儲存 notification」，adapter 決定用 memory、SQLite 或其他技術完成。

application 定義 port：

```go
package application

type NotificationRepository interface {
    Save(ctx context.Context, notification domain.Notification) error
    FindByID(ctx context.Context, id string) (domain.Notification, bool, error)
}
```

memory adapter 實作：

```go
package memory

type NotificationRepository struct {
    mu            sync.RWMutex
    notifications map[string]domain.Notification
}

func (r *NotificationRepository) Save(ctx context.Context, notification domain.Notification) error {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.notifications[notification.ID] = notification
    return nil
}

func (r *NotificationRepository) FindByID(ctx context.Context, id string) (domain.Notification, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    notification, ok := r.notifications[id]
    return notification, ok, nil
}
```

adapter import application 不一定必要，因為 Go implicit interface 不要求顯式宣告。只要 method set 符合，組裝時就能傳給 usecase。

## 【策略】usecase 是遷移中心

usecase 的核心角色是協調 domain 規則與 ports。它不處理 HTTP，也不操作具體資料庫。

```go
package application

type CreateNotificationUsecase struct {
    repository NotificationRepository
    eventLog   EventLog
}

func NewCreateNotificationUsecase(repository NotificationRepository, eventLog EventLog) *CreateNotificationUsecase {
    return &CreateNotificationUsecase{
        repository: repository,
        eventLog:   eventLog,
    }
}

func (u *CreateNotificationUsecase) Execute(ctx context.Context, cmd CreateNotificationCommand) error {
    notification := domain.Notification{
        ID:        cmd.ID,
        Topic:     cmd.Topic,
        Title:     cmd.Title,
        CreatedAt: cmd.CreatedAt,
    }

    if err := u.repository.Save(ctx, notification); err != nil {
        return fmt.Errorf("save notification: %w", err)
    }

    event := domain.NewNotificationCreated(notification)
    if err := u.eventLog.Append(ctx, event); err != nil {
        return fmt.Errorf("append event: %w", err)
    }

    return nil
}
```

這個 usecase 只依賴 domain 與 ports。HTTP handler、WebSocket router、memory repository、[event [log](../../../backend/knowledge-cards/log/)](../../backend/knowledge-cards/event-log) implementation 都在外面。

## 【執行】組裝放在 main 或 composition root

composition root 的核心責任是建立 concrete implementation，並把它們接到 usecase 與 adapter。Go 專案常把這件事放在 `main.go` 或 `cmd/.../main.go`。

```go
func main() {
    notificationRepo := memory.NewNotificationRepository()
    eventLog := memory.NewEventLog()

    createNotification := application.NewCreateNotificationUsecase(
        notificationRepo,
        eventLog,
    )

    handler := httpadapter.NewNotificationHandler(createNotification, time.Now)

    mux := http.NewServeMux()
    mux.HandleFunc("POST /notifications", handler.Create)

    server := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }

    if err := server.ListenAndServe(); err != nil {
        log.Fatal(err)
    }
}
```

main 可以知道所有具體實作，因為它負責組裝。這不違反依賴方向；問題是 application 或 domain 不能反過來 import main、HTTP adapter 或 memory adapter。

## 【策略】新功能先走新架構

漸進式遷移的核心策略是新功能先走新邊界，舊功能在被修改時再搬。一次性大重構風險高，容易同時改壞行為與結構。

建議做法：

- 新 endpoint 直接建立 command/usecase。
- 新 repository 先定義小 port。
- 新 event flow 先走 `DomainEvent` 與 processor。
- 舊 handler 只有在新增需求或修 bug 時才拆。
- 保留舊路徑測試，搬移完成再刪掉。

這樣可以讓新架構逐步長出來，而不是一次強迫整個專案符合模板。

## 【執行】從 callback ingestion 開始切

以外部 callback 進入事件系統為例，application usecase 可以叫 `IngestExternalEvent`：

```go
package application

type EventLog interface {
    Append(ctx context.Context, event domain.Event) error
}

type EventProcessor interface {
    Process(ctx context.Context, event domain.Event) error
}

type IngestExternalEvent struct {
    eventLog  EventLog
    processor EventProcessor
}

func (u *IngestExternalEvent) Execute(ctx context.Context, event domain.Event) error {
    if err := event.Validate(); err != nil {
        return fmt.Errorf("validate event: %w", err)
    }
    if err := u.eventLog.Append(ctx, event); err != nil {
        return fmt.Errorf("append event: %w", err)
    }
    if err := u.processor.Process(ctx, event); err != nil {
        return fmt.Errorf("process event: %w", err)
    }
    return nil
}
```

callback adapter 只負責 raw input 轉 domain event：

```go
func (h CallbackHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    var raw RawNotificationCallback
    if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
        writeError(w, http.StatusBadRequest, "invalid_json", "invalid JSON")
        return
    }

    event, err := NormalizeNotificationCallback(raw, time.Now())
    if err != nil {
        writeError(w, http.StatusBadRequest, "invalid_payload", "invalid callback payload")
        return
    }

    if err := h.ingest.Execute(r.Context(), event); err != nil {
        writeError(w, http.StatusInternalServerError, "ingest_failed", "event ingest failed")
        return
    }

    w.WriteHeader(http.StatusAccepted)
}
```

這個切法讓 callback 格式停在 adapter，event log 與 processor 行為停在 application。

## 【判讀】WebSocket adapter 也是 inbound adapter

WebSocket adapter 的核心責任是把 client message 轉成 command。它不應直接知道 repository 或 event log implementation。

```go
type WebSocketAdapter struct {
    router *MessageRouter
}

type MessageRouter struct {
    subscriptions application.SubscriptionUsecase
}
```

router 可以呼叫 application usecase：

```go
func (r *MessageRouter) handleSubscribeTopic(ctx context.Context, clientID string, req SubscribeTopicRequest) ServerMessage {
    cmd := application.SubscribeTopicCommand{
        ClientID:       clientID,
        Topic:          req.Topic,
        IncludeHistory: req.IncludeHistory,
    }

    if err := r.subscriptions.SubscribeTopic(ctx, cmd); err != nil {
        return ErrorMessage("", "subscribe_failed", "topic subscription failed")
    }

    return OKMessage("", map[string]string{"topic": req.Topic})
}
```

這和 HTTP handler 的方向相同：adapter 處理協定，application 處理行為。

## 【執行】驗證 import direction

架構邊界的核心驗證是 import direction。即使沒有工具，也可以用簡單規則檢查：

```text
domain       不 import application、transport、storage
application  可以 import domain，不 import transport/storage implementation
transport    可以 import application/domain
storage      可以 import application/domain
cmd/main     可以 import 所有 adapter 與 application 做組裝
```

可以用 `go list` 觀察 package 依賴：

```bash
go list -deps ./...
```

也可以在 review 時檢查：如果 `domain/job` import 了 `net/http`，幾乎一定是邊界錯了；如果 `application` import 了 `storage/memory`，則 usecase 已經依賴 implementation。

## 【執行】usecase test 與 adapter integration test 分工

測試分工的核心原則是 usecase 測規則，adapter 測協定轉換與組裝。不要只靠端到端測試保護所有行為。

usecase test：

```go
func TestIngestExternalEventAppendsAndProcesses(t *testing.T) {
    eventLog := &fakeEventLog{}
    processor := &fakeEventProcessor{}
    usecase := &application.IngestExternalEvent{
        eventLog:  eventLog,
        processor: processor,
    }

    event := validDomainEvent()
    if err := usecase.Execute(context.Background(), event); err != nil {
        t.Fatalf("ingest event: %v", err)
    }

    if len(eventLog.appended) != 1 {
        t.Fatalf("appended events = %d, want 1", len(eventLog.appended))
    }
    if len(processor.processed) != 1 {
        t.Fatalf("processed events = %d, want 1", len(processor.processed))
    }
}
```

adapter integration test 則可以用 `httptest` 驗證 request/response 與 usecase fake 是否被呼叫。兩種測試分工清楚，失敗時才知道是規則錯還是協定轉換錯。

## 重構步驟

逐步遷移到 ports/adapters，可以按這個順序：

1. 先找一條最痛的功能路徑，例如新增 notification 或 ingest external event。
2. 把 handler/router 中的規則抽成 command/usecase。
3. 在 application 定義 repository、event log、publisher port。
4. 讓現有 memory store 或 publisher 實作 port。
5. main 組裝 concrete adapter 與 usecase。
6. 新功能只走新路徑。
7. 舊功能被修改時，逐步搬到同樣邊界。
8. 用 import direction review 防止反向依賴。

## 設計檢查

### 檢查一：遷移從單一邊界開始

ports/adapters 的價值是依賴方向。若沒有先拆 usecase 與 port，只是搬資料夾，複雜度會上升但邊界不會變清楚。

### 檢查二：application 依賴 port

application 應依賴 port，不依賴 memory、SQLite 或 database adapter。若 application import storage，依賴方向已經反了。

### 檢查三：業務規則留在 application 或 domain

adapter 可以驗證輸入格式，但業務規則應該在 usecase 或 domain。否則 HTTP 與 WebSocket 會各自複製規則。

### 檢查四：port 跟著使用端分散

port 應靠近使用端。把所有 interface 集中到一個大型 package，常會讓依賴重新糾纏在一起。

## 本章不處理

本章先處理 ports/adapters 的依賴方向；分散式系統、資料庫與平台 wiring，會在下列章節再往外延伸：

- [Go 進階：跨節點與平台整合](../../../go-advanced/07-distributed-operations/)
- [Go 進階：資料庫 transaction 與 schema migration](../../../go-advanced/07-distributed-operations/database-transactions/)
- [Go 進階：Durable queue、outbox 與 idempotency](../../../go-advanced/07-distributed-operations/outbox-idempotency/)
- [Go 進階：Kubernetes、systemd 與 load balancer 合約](../../../go-advanced/07-distributed-operations/deployment-contracts/)

## 和 Go 教材的關係

這一章承接的是 handler、repository、event 與 composition root 的遷移路線；如果你要先回看語言教材，可以讀：

- [Go：把 handler 邏輯拆成可測單元](../handler-boundary/)
- [Go：用 interface 隔離外部依賴](../interface-boundary/)
- [Go：如何新增 repository port](../../06-practical/repository-port/)
- [Go：composition root 與依賴組裝](../composition-root/)

## 小結

ports/adapters 遷移的重點是控制依賴方向：adapter 處理外部技術，application 定義 usecase 與 ports，domain 保存核心語意。Go 專案可以漸進式遷移，新功能先走清楚邊界，舊功能在修改時再搬。架構的價值不在資料夾名稱，而在測試更直接、替換更容易、核心規則不被外部技術綁住。
