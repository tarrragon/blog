---
title: "7.2 用 interface 隔離外部依賴"
date: 2026-04-22
description: "建立小而穩定的測試替身"
weight: 2
---

interface 邊界重構的核心規則是由使用端定義需要的能力。介面不是為了包裝所有實作，而是為了讓 usecase 不依賴外部技術細節。

## 本章目標

學完本章後，你將能夠：

1. 辨識哪些依賴值得用 interface 隔離
2. 讓 interface 由使用端定義
3. 設計小而穩定的 port
4. 分辨 fake test 與 contract test
5. 避免過早抽象與巨大 interface

---

## 【觀察】interface 是依賴邊界

interface 重構的核心目標是讓高層邏輯只依賴需要的能力。Go 的 interface 不是為了宣告 class hierarchy，而是為了讓呼叫端不必知道具體實作。

過重依賴常見在這些地方：

- usecase 直接依賴 `*sql.DB`。
- handler 直接依賴 concrete service，測試很難替換。
- background worker 直接呼叫外部 API client。
- processor 直接知道 [WebSocket](../../../backend/knowledge-cards/websocket/) hub。
- 測試為了建一個 usecase，必須初始化真資料庫、真檔案或真網路。

interface 的價值是讓 usecase 可以說：「我只需要儲存 notification」、「我只需要 append event」、「我只需要 publish message」。至於能力怎麼實作，是 adapter 的責任。

## 【判讀】先辨識外部依賴

外部依賴的核心特徵是慢、不穩、難測或帶有技術細節。這些依賴通常適合被 interface 隔離。

| 依賴                                                                                          | 隔離原因                                                                      | 可能 interface                |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------- |
| clock                                                                                         | 測試需要固定時間                                                              | `Clock` 或 `func() time.Time` |
| repository                                                                                    | 儲存技術可替換                                                                | `NotificationRepository`      |
| [event [log](../../../backend/knowledge-cards/log/)](../../backend/knowledge-cards/event-log) | 記錄實作可替換                                                                | `EventLog`                    |
| publisher                                                                                     | WebSocket、[queue](../../../backend/knowledge-cards/queue/)、log 都可能是輸出 | `Publisher`                   |
| external client                                                                               | 網路失敗與測試替身                                                            | `NotificationSource`          |
| command runner                                                                                | 外部程序慢且不穩                                                              | `CommandRunner`               |

不是所有型別都需要 interface。純資料 struct、簡單 helper、沒有替換需求的內部物件，通常先保持 concrete type 更清楚。

## 【策略】interface 放在使用端

interface 位置的核心規則是：誰需要這個能力，誰定義 interface。這會讓 interface 保持小，也避免 implementation 暴露太多方法。

usecase 需要儲存通知，就在 usecase 附近定義：

```go
type NotificationRepository interface {
    Save(ctx context.Context, notification Notification) error
    FindByID(ctx context.Context, id string) (Notification, bool, error)
}
```

in-memory adapter 只要方法集合符合，就自然實作這個 interface：

```go
type InMemoryNotificationRepository struct {
    mu            sync.RWMutex
    notifications map[string]Notification
}

func (r *InMemoryNotificationRepository) Save(ctx context.Context, notification Notification) error {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.notifications[notification.ID] = notification
    return nil
}

func (r *InMemoryNotificationRepository) FindByID(ctx context.Context, id string) (Notification, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    notification, ok := r.notifications[id]
    return notification, ok, nil
}
```

`InMemoryNotificationRepository` 不需要宣告自己 implements 了什麼。Go 的 implicit interface 讓實作端保持乾淨。

## 【執行】用小 port 隔離 event log

event log port 的核心語意是「可以記錄已發生的事件」。usecase 或 processor 不需要知道事件記錄到 memory、檔案還是資料庫。

```go
type EventLog interface {
    Append(ctx context.Context, event DomainEvent) error
}
```

processor 依賴這個 port：

```go
type EventProcessor struct {
    eventLog EventLog
}

func NewEventProcessor(eventLog EventLog) *EventProcessor {
    return &EventProcessor{eventLog: eventLog}
}

func (p *EventProcessor) Process(ctx context.Context, event DomainEvent) error {
    if err := event.Validate(); err != nil {
        return fmt.Errorf("validate event: %w", err)
    }
    if err := p.eventLog.Append(ctx, event); err != nil {
        return fmt.Errorf("append event log: %w", err)
    }
    return nil
}
```

這個 interface 很小，但它已經足夠讓 processor 測試脫離真正儲存實作。

## 【執行】publisher port 隔離輸出技術

publisher port 的核心語意是「把結果送出去」。即時推送可以用 WebSocket，非同步流程可以用 queue，測試可以用 recording fake。

```go
type Publisher interface {
    Publish(ctx context.Context, event DomainEvent) error
}
```

processor 可以同時依賴 event log 與 publisher：

```go
type RecordingProcessor struct {
    eventLog  EventLog
    publisher Publisher
}

func (p *RecordingProcessor) Process(ctx context.Context, event DomainEvent) error {
    if err := p.eventLog.Append(ctx, event); err != nil {
        return fmt.Errorf("append event: %w", err)
    }
    if err := p.publisher.Publish(ctx, event); err != nil {
        return fmt.Errorf("publish event: %w", err)
    }
    return nil
}
```

這裡的 processor 不知道輸出是 WebSocket 還是 message queue。這就是 interface 邊界的目的。

## 【策略】clock 可以用函式，不一定要 interface

時間依賴的核心問題是測試需要固定現在時間。最小解法通常是注入函式，而不是建立完整 interface。

```go
type Clock func() time.Time

type NotificationService struct {
    now Clock
}

func NewNotificationService(now Clock) *NotificationService {
    return &NotificationService{now: now}
}
```

使用時：

```go
func (s *NotificationService) NewNotification(id string, topic string) Notification {
    return Notification{
        ID:        id,
        Topic:     topic,
        CreatedAt: s.now(),
    }
}
```

測試時傳固定時間：

```go
fixedNow := func() time.Time {
    return time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
}
service := NewNotificationService(fixedNow)
```

若只需要「現在時間」，函式比 `Clock interface { Now() time.Time }` 更簡單。Go 的抽象不一定要用 interface。

## 【判讀】小 interface 比大 interface 更穩定

小 interface 的核心好處是測試替身容易寫，使用端只知道自己需要的能力。巨大 interface 會把不相關 usecase 綁在一起。

不佳：

```go
type ApplicationService interface {
    CreateNotification(ctx context.Context, cmd CreateNotificationCommand) error
    ListNotifications(ctx context.Context, topic string) ([]Notification, error)
    AppendEvent(ctx context.Context, event DomainEvent) error
    Publish(ctx context.Context, event DomainEvent) error
    RunSync(ctx context.Context) error
}
```

較佳：

```go
type NotificationCreator interface {
    Create(ctx context.Context, cmd CreateNotificationCommand) error
}

type EventLog interface {
    Append(ctx context.Context, event DomainEvent) error
}

type Publisher interface {
    Publish(ctx context.Context, event DomainEvent) error
}
```

不同呼叫端依賴不同能力。handler 只依賴 creator，processor 只依賴 event log 與 publisher，worker 只依賴 source 與 processor。

## 【執行】fake test 驗證使用端行為

fake test 的核心目標是測使用端怎麼使用依賴。fake 可以很小，只實作測試需要的行為。

```go
type fakeEventLog struct {
    appended []DomainEvent
    err      error
}

func (f *fakeEventLog) Append(ctx context.Context, event DomainEvent) error {
    if f.err != nil {
        return f.err
    }
    f.appended = append(f.appended, event)
    return nil
}
```

測 processor：

```go
func TestEventProcessorAppendsEvent(t *testing.T) {
    eventLog := &fakeEventLog{}
    processor := NewEventProcessor(eventLog)

    event := validDomainEvent()
    if err := processor.Process(context.Background(), event); err != nil {
        t.Fatalf("process event: %v", err)
    }

    if len(eventLog.appended) != 1 {
        t.Fatalf("appended events = %d, want 1", len(eventLog.appended))
    }
}
```

這個測試不關心 event log 如何保存資料。它只驗證 processor 在正確情境下呼叫了 port。

## 【執行】contract test 驗證 adapter 行為

contract test 的核心目標是讓不同 adapter 都符合 port 行為。這類測試測 implementation，不測 usecase。

```go
func runEventLogContract(t *testing.T, newLog func() EventLogWithList) {
    t.Helper()

    log := newLog()
    event := validDomainEvent()

    if err := log.Append(context.Background(), event); err != nil {
        t.Fatalf("append event: %v", err)
    }

    events := log.List()
    if len(events) != 1 {
        t.Fatalf("events = %d, want 1", len(events))
    }
    if events[0].ID != event.ID {
        t.Fatalf("event ID = %q, want %q", events[0].ID, event.ID)
    }
}

type EventLogWithList interface {
    EventLog
    List() []DomainEvent
}
```

`List` 不一定屬於 production port，它可以是測試用輔助介面。若未來有 SQLite event log，也可以跑同一套 contract test。

## 【策略】避免過早抽象

避免過早抽象的核心判斷是：沒有替換、測試或技術隔離需求時，先用 concrete type。interface 不是越多越好。

先不要抽 interface 的情境：

- 只有一個 implementation。
- 測試不需要 fake。
- concrete type 很小，直接使用更清楚。
- interface 只是完整複製 concrete type 的所有方法。
- 邊界還不穩，方法很快會變。

可以抽 interface 的情境：

- usecase 不應依賴技術細節。
- 測試需要替換慢或不穩的依賴。
- 同一個能力有多種 implementation。
- 依賴跨越 package 邊界，使用端只需要小部分能力。

重構時可以先寫 concrete type，等第二個使用端或測試壓力出現，再抽出使用端 interface。

## 重構步驟

把 concrete dependency 改成 interface 時，可以按這個順序：

1. 找出使用端真正呼叫的方法。
2. 在使用端附近定義小 interface。
3. 把 struct 欄位型別從 concrete type 改成 interface。
4. 確認現有 concrete type 自然符合 interface。
5. 在測試中建立 fake。
6. 為 adapter 補 contract test。
7. 移除不再需要的直接依賴。

不要先設計一個完美的全域介面。從使用端需要的最小方法開始，介面會更穩。

## 設計檢查

### 檢查一：interface 由使用端定義

implementation 定義的 interface 往往暴露太多方法。使用端定義 interface，才能只依賴自己真正需要的能力。

### 檢查二：有替換需求再建立 interface

`Foo` 搭配 `FooInterface` 不是 Go 的慣例。interface 應該來自使用需求，而不是來自型別存在。

### 檢查三：fake 服務當前測試行為

fake 是測試工具，不是真 adapter。它只需要支援測試情境，不需要重建資料庫、網路或完整狀態機。

### 檢查四：公開 interface 需要穩定承諾

一旦 interface 被多個 package 依賴，修改成本會提高。邊界還在探索時，保持 unexported 或使用 concrete type 更務實。

## 本章不處理

本章先處理 interface 如何讓使用端依賴能力；全專案 DI 框架與 mock generator，會在下列章節再往外延伸：

- [Go 入門：interface：用行為定義依賴](../../02-types-data/interfaces/)
- [Go 入門：testing 基礎](../../05-error-testing/testing-basics/)
- [Go 進階：composition root 與依賴組裝](../composition-root/)

## 和 Go 教材的關係

這一章承接的是 usecase、adapter 與測試替身邊界；如果你要先回看語言教材，可以讀：

- [Go：把 handler 邏輯拆成可測單元](../handler-boundary/)
- [Go：如何新增 repository port](../../06-practical/repository-port/)
- [Go：如何新增背景工作流程](../../06-practical/new-background-worker/)
- [Go：逐步遷移到 ports/adapters 架構](../hexagonal-migration/)

## 小結

interface 邊界的價值是讓使用端依賴能力，而不是依賴技術細節。好的 interface 小、穩定、由使用端定義；fake 測 usecase 怎麼使用能力，contract test 測 adapter 是否符合能力承諾。抽象應該回應測試、替換或依賴方向的壓力，而不是為了讓程式看起來更有架構。
