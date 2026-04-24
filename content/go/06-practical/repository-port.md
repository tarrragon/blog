---
title: "6.6 如何新增 repository port"
date: 2026-04-22
description: "先建立儲存邊界，再決定 memory、SQLite 或外部資料庫實作"
weight: 6
---

新增 repository port 的核心目標是讓 application layer 依賴資料能力，而不是依賴具體儲存技術。先建立 port，才能在 memory、SQLite 或其他資料庫之間替換。

## 本章目標

學完本章後，你將能夠：

1. 判斷何時需要 repository port
2. 由 usecase 定義小而明確的 repository interface
3. 實作 map + mutex 的 in-memory repository
4. 保留 context、error 與 [database](/backend/knowledge-cards/database/)-ready 邊界
5. 分開撰寫 usecase fake test 與 repository contract test

---

## 【觀察】repository port 表達資料能力

repository port 的核心語意是 usecase 需要哪些資料能力。它應描述 application layer 的讀寫需求，而不是照搬資料庫 CRUD 方法或把所有資料操作塞進同一個巨大 `Repository`。

例如通知服務的 usecase 可能需要三種能力：

| usecase 需求                                       | repository 能力                  |
| -------------------------------------------------- | -------------------------------- |
| 建立通知                                           | 儲存一筆 notification            |
| 查詢 [topic](/backend/knowledge-cards/topic/) 通知 | 依 topic 列出 notification       |
| 避免重複建立                                       | 依 ID 查詢 notification 是否存在 |

這些能力可以先用 memory 實作，未來再換成 SQLite、PostgreSQL 或外部服務。usecase 不應知道底層儲存技術。

## 【判讀】repository 服務共享讀寫邊界

是否需要 repository 的核心判斷是資料是否需要一致的讀寫邊界。暫時變數、單次函式內部結果或不共享的 cache，不一定需要 repository。

適合 repository 的情境：

- 多個 usecase 需要一致讀寫同一組資料
- 資料需要被測試替身取代
- 讀寫規則需要集中
- 未來可能從 memory 換成資料庫
- 需要保護 map、slice 或 pointer 不被外部修改

不一定需要 repository 的情境：

- 只在單一函式內暫存
- 只是純計算結果
- 還沒有共享或替換需求
- 只有一個簡單 struct 可以直接傳遞

repository 是邊界工具，不是成熟專案的儀式。過早建立 repository 會讓小程式變得難讀。

## 【策略】interface 放在使用端

repository interface 的核心規則是由使用端定義需要的能力。usecase 需要什麼，就在 usecase 所在 package 定義什麼；adapter 或 infrastructure 實作它。

```go
type NotificationRepository interface {
    Save(ctx context.Context, notification Notification) error
    FindByID(ctx context.Context, id string) (Notification, bool, error)
    ListByTopic(ctx context.Context, topic string) ([]Notification, error)
}
```

方法名稱應該表達業務能力，而不是資料庫操作細節。`ListByTopic` 比 `SelectWhereTopicEquals` 更適合 usecase。

先定義 domain model：

```go
type Notification struct {
    ID        string
    Topic     string
    Title     string
    CreatedAt time.Time
}
```

domain model 不需要 JSON tag。對外 JSON 格式應交給 response struct，repository 儲存的是內部資料。

## 【執行】usecase 依賴 port，不依賴 implementation

usecase 的核心責任是協調資料能力與行為規則。它接收 repository port，而不是具體 memory repository。

```go
type CreateNotificationCommand struct {
    ID        string
    Topic     string
    Title     string
    CreatedAt time.Time
}

type NotificationService struct {
    repository NotificationRepository
}

func NewNotificationService(repository NotificationRepository) *NotificationService {
    return &NotificationService{repository: repository}
}
```

建立通知時，usecase 可以檢查重複與必填欄位：

```go
func (s *NotificationService) Create(ctx context.Context, cmd CreateNotificationCommand) error {
    if strings.TrimSpace(cmd.ID) == "" {
        return fmt.Errorf("notification id is required")
    }
    if strings.TrimSpace(cmd.Topic) == "" {
        return fmt.Errorf("topic is required")
    }

    if _, exists, err := s.repository.FindByID(ctx, cmd.ID); err != nil {
        return fmt.Errorf("find notification: %w", err)
    } else if exists {
        return fmt.Errorf("notification %s already exists", cmd.ID)
    }

    notification := Notification{
        ID:        cmd.ID,
        Topic:     cmd.Topic,
        Title:     cmd.Title,
        CreatedAt: cmd.CreatedAt,
    }

    if err := s.repository.Save(ctx, notification); err != nil {
        return fmt.Errorf("save notification: %w", err)
    }

    return nil
}
```

這段 usecase 不知道資料存在 map、SQLite 或遠端 API。它只依賴「可以查詢與儲存 notification」這個能力。

## 【執行】memory implementation 要保護 map

in-memory repository 的核心責任是提供可用的儲存實作，同時保護共享 map。只要 repository 可能被多個 goroutine 使用，就應該用 mutex 保護。

```go
type InMemoryNotificationRepository struct {
    mu            sync.RWMutex
    notifications map[string]Notification
}

func NewInMemoryNotificationRepository() *InMemoryNotificationRepository {
    return &InMemoryNotificationRepository{
        notifications: make(map[string]Notification),
    }
}
```

`Save` 寫入時要複製資料：

```go
func (r *InMemoryNotificationRepository) Save(ctx context.Context, notification Notification) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    r.notifications[notification.ID] = notification
    return nil
}
```

`FindByID` 回傳值與 bool：

```go
func (r *InMemoryNotificationRepository) FindByID(ctx context.Context, id string) (Notification, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    notification, ok := r.notifications[id]
    if !ok {
        return Notification{}, false, nil
    }
    return notification, true, nil
}
```

`ListByTopic` 回傳新 slice，避免呼叫端修改內部資料：

```go
func (r *InMemoryNotificationRepository) ListByTopic(ctx context.Context, topic string) ([]Notification, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    result := make([]Notification, 0)
    for _, notification := range r.notifications {
        if notification.Topic == topic {
            result = append(result, notification)
        }
    }
    return result, nil
}
```

目前 `Notification` 只有值型別欄位，所以回傳值與新 slice 已足夠。若未來加上 slice、map 或 pointer 欄位，就要補 clone 函式。

## 【策略】context 和 error 是未來資料庫邊界

repository method 接收 context 的核心原因是未來可能出現 I/O。memory 實作可能不使用 context，但資料庫查詢、遠端 API 或 [transaction](/backend/knowledge-cards/transaction/) 會需要取消與逾時。

```go
Save(ctx context.Context, notification Notification) error
```

error wrapping 的核心規則是保留失敗位置與原始錯誤：

```go
if err := s.repository.Save(ctx, notification); err != nil {
    return fmt.Errorf("save notification: %w", err)
}
```

不要過早抽象 transaction。只有當一個 usecase 真的需要多筆寫入同時成功或失敗時，再設計 [transaction boundary](/backend/knowledge-cards/transaction-boundary/)。否則 repository interface 會提前背負資料庫細節。

## 【判讀】fake 和 in-memory 用於不同測試

測試替身的核心差異是 fake 服務 usecase 測試，in-memory implementation 服務 repository 行為測試。兩者可以長得像，但用途不同。

usecase 測試可以用簡單 fake：

```go
type fakeNotificationRepository struct {
    existing map[string]Notification
    saved    []Notification
    err      error
}

func (f *fakeNotificationRepository) Save(ctx context.Context, notification Notification) error {
    if f.err != nil {
        return f.err
    }
    f.saved = append(f.saved, notification)
    return nil
}

func (f *fakeNotificationRepository) FindByID(ctx context.Context, id string) (Notification, bool, error) {
    if f.err != nil {
        return Notification{}, false, f.err
    }
    notification, ok := f.existing[id]
    return notification, ok, nil
}

func (f *fakeNotificationRepository) ListByTopic(ctx context.Context, topic string) ([]Notification, error) {
    return nil, nil
}
```

這個 fake 只支援測試需要的行為，不必成為完整 repository。

## 【執行】usecase 測試檢查行為規則

usecase 測試的核心目標是驗證 command 進來後是否呼叫正確資料能力。它不應測 memory map 的 lock 或 copy 行為。

```go
func TestNotificationServiceCreate(t *testing.T) {
    repo := &fakeNotificationRepository{
        existing: make(map[string]Notification),
    }
    service := NewNotificationService(repo)

    err := service.Create(context.Background(), CreateNotificationCommand{
        ID:        "ntf_1",
        Topic:     "deployments",
        Title:     "Deploy finished",
        CreatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
    })
    if err != nil {
        t.Fatalf("create notification: %v", err)
    }

    if len(repo.saved) != 1 {
        t.Fatalf("saved notifications = %d, want 1", len(repo.saved))
    }
}
```

重複 ID 測試可以讓 fake 回傳 existing notification：

```go
func TestNotificationServiceCreateDuplicate(t *testing.T) {
    repo := &fakeNotificationRepository{
        existing: map[string]Notification{
            "ntf_1": {ID: "ntf_1"},
        },
    }
    service := NewNotificationService(repo)

    err := service.Create(context.Background(), CreateNotificationCommand{
        ID:        "ntf_1",
        Topic:     "deployments",
        Title:     "Deploy finished",
        CreatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
    })
    if err == nil {
        t.Fatalf("expected duplicate error")
    }
}
```

這些測試讓 usecase 不依賴具體 repository implementation。

## 【執行】repository contract test 保護實作行為

repository contract test 的核心目標是讓不同 implementation 遵守同一組行為。memory repository、SQLite repository 或其他實作都可以跑同一套測試。

```go
func TestNotificationRepositoryContract(t *testing.T) {
    runNotificationRepositoryContract(t, func() NotificationRepository {
        return NewInMemoryNotificationRepository()
    })
}

func runNotificationRepositoryContract(t *testing.T, newRepo func() NotificationRepository) {
    t.Helper()

    repo := newRepo()
    ctx := context.Background()
    notification := Notification{
        ID:        "ntf_1",
        Topic:     "deployments",
        Title:     "Deploy finished",
        CreatedAt: time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC),
    }

    if err := repo.Save(ctx, notification); err != nil {
        t.Fatalf("save notification: %v", err)
    }

    got, ok, err := repo.FindByID(ctx, "ntf_1")
    if err != nil {
        t.Fatalf("find notification: %v", err)
    }
    if !ok {
        t.Fatalf("notification should exist")
    }
    if got.Topic != "deployments" {
        t.Fatalf("topic = %q, want deployments", got.Topic)
    }

    list, err := repo.ListByTopic(ctx, "deployments")
    if err != nil {
        t.Fatalf("list notifications: %v", err)
    }
    if len(list) != 1 {
        t.Fatalf("notifications = %d, want 1", len(list))
    }
}
```

contract test 不需要知道實作細節。它只驗證 port 承諾的行為。

## 【策略】小介面比萬用 repository 穩定

repository interface 的核心風險是變成所有資料操作的大型介面。大型介面會讓每個 usecase、fake 與測試都被迫依賴不需要的方法。

不佳：

```go
type Repository interface {
    SaveNotification(ctx context.Context, notification Notification) error
    ListNotifications(ctx context.Context) ([]Notification, error)
    SaveJob(ctx context.Context, job JobProjection) error
    SaveAccount(ctx context.Context, account Account) error
    AppendEvent(ctx context.Context, event DomainEvent) error
}
```

較佳：

```go
type NotificationRepository interface {
    Save(ctx context.Context, notification Notification) error
    FindByID(ctx context.Context, id string) (Notification, bool, error)
    ListByTopic(ctx context.Context, topic string) ([]Notification, error)
}
```

不同 usecase 可以定義不同 port。若未來多個 port 由同一個 database adapter 實作，那是 adapter 的事，不必讓 usecase 共享巨大介面。

## 實作檢查清單

新增 repository port 時，可以依序檢查：

1. 是否真的需要共享讀寫邊界
2. interface 是否由 usecase 需要定義
3. 方法名稱是否表達業務能力
4. 方法是否接收 `context.Context`
5. error 是否被包上操作脈絡
6. in-memory implementation 是否保護 map
7. 回傳 slice/map/pointer 時是否有 copy boundary
8. usecase 測試是否使用 fake
9. repository implementation 是否跑 contract test
10. 是否避免把所有資料操作塞進巨大介面

## 設計檢查

### 檢查一：repository 來自 usecase 需求

repository 應該來自 usecase 需求。先建一個萬用 `Repository`，通常會讓介面快速膨脹，測試也變得笨重。

### 檢查二：interface 放在使用端

若 interface 是由 implementation 定義，usecase 會被迫接受 implementation 想暴露的能力。Go 更常見的做法是讓使用端定義最小需求。

### 檢查三：memory repository 保護內部資料

回傳內部 slice、map 或 pointer 會讓呼叫端繞過 repository 規則。即使目前只是 memory 實作，也應保護資料擁有權。

### 檢查四：transaction 和 ORM 等需求出現再抽象

沒有跨多筆寫入一致性需求時，transaction 介面只會增加複雜度。先把 context、error、port 邊界放好，等需求出現再擴展。

## 本章不處理

本章先處理 repository port 如何表達資料能力；特定資料庫、ORM 與 transaction，會在下列章節再往外延伸：

- [Go 進階：資料庫 transaction 與 schema migration](/go-advanced/07-distributed-operations/database-transactions/)
- [Backend：資料庫與持久化](/backend/01-database/)

## 和 Go 教材的關係

這一章承接的是 interface、state 與 application boundary；如果你要先回看語言教材，可以讀：

- [Go：用 interface 隔離外部依賴](/go/07-refactoring/interface-boundary/)
- [Go：狀態管理的安全邊界](/go/07-refactoring/state-boundary/)
- [Go：如何新增一種 domain event](/go/06-practical/new-event-type/)
- [Go：如何擴展狀態投影欄位](/go/06-practical/state-fields/)

## 小結

repository port 的價值是讓 usecase 依賴資料能力，而不是依賴儲存技術。小介面、context、error wrapping、copy boundary 與 contract test 會讓 memory 實作可以自然演進到資料庫實作。當資料需要一致讀寫、測試替身或未來替換時，再建立這個邊界。
