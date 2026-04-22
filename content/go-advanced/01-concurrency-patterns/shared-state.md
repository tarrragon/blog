---
title: "1.4 共享狀態與複製邊界"
date: 2026-04-22
description: "用 lock 與 copy 保護長期服務的狀態資料"
weight: 4
---

共享狀態的核心規則是同一份可變資料若會被多個 goroutine 存取，就必須有明確 owner 與保護邊界。Map 需要同步，slice 回傳前通常要 copy，可變指標不能隨意暴露，修改行為應集中在擁有狀態的型別內。

## 本章目標

學完本章後，你將能夠：

1. 判斷哪個型別擁有共享狀態
2. 用 `sync.RWMutex` 保護 map 與 slice
3. 避免回傳內部 map、slice、pointer
4. 分辨 shallow copy 與 deep copy 的邊界
5. 用測試與 race detector 驗證共享狀態安全性

---

## 【觀察】共享狀態錯誤通常不是立刻出現

共享狀態的核心風險是錯誤可能只在特定併發時序下出現。單元測試可能通過，本地手動操作也正常，但高流量下會出現 data race、map panic、狀態被外部修改或歷史資料被覆蓋。

反模式示意：

```go
type Store struct {
    users map[string]User
}

func (s *Store) Save(user User) {
    s.users[user.ID] = user
}

func (s *Store) Users() map[string]User {
    return s.users
}
```

這個型別有兩個問題：map 沒有同步保護，且 `Users` 直接暴露內部 map。呼叫端拿到 map 後可以繞過 `Store` 修改資料。

## 【判讀】mutex 保護的是狀態不變式

Mutex 的核心責任不是讓程式「不會同時跑」，而是保護某一組資料的不變式。只要讀寫同一份可變資料，就應該由同一個 owner 控制 lock。

```go
type UserRepository struct {
    mu    sync.RWMutex
    users map[string]User
}

func NewUserRepository() *UserRepository {
    return &UserRepository{
        users: make(map[string]User),
    }
}
```

`UserRepository` 是 `users` map 的 owner。外部程式不應持有 `users` 的 reference，也不應知道它用 map、資料庫或其他結構保存。

## 【執行】所有讀寫都經過 owner method

共享 map 的核心規則是所有讀寫都經過同一組方法。寫入使用 `Lock`，讀取使用 `RLock`。

```go
func (r *UserRepository) Save(ctx context.Context, user User) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    r.users[user.ID] = user
    return nil
}

func (r *UserRepository) Find(ctx context.Context, id string) (User, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    user, ok := r.users[id]
    return user, ok, nil
}
```

`context.Context` 在 memory repository 裡可能用不到，但保留在 method signature 可以讓未來改成資料庫或遠端儲存時支援取消。這是 repository port 常見的演進邊界。

## 【判讀】回傳內部 map 會破壞 lock

回傳 map 的核心風險是鎖只保護到方法結束。方法回傳後，呼叫端拿到的仍然是同一份 map，任何修改都會繞過 owner。

反模式：

```go
func (r *UserRepository) UnsafeUsers(ctx context.Context) map[string]User {
    r.mu.RLock()
    defer r.mu.RUnlock()

    return r.users
}
```

這段程式看起來有加鎖，但鎖釋放後外部仍能修改內部 map：

```go
users := repo.UnsafeUsers(ctx)
delete(users, "user_1")
```

安全做法是回傳 copy：

```go
func (r *UserRepository) Users(ctx context.Context) (map[string]User, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    result := make(map[string]User, len(r.users))
    for id, user := range r.users {
        result[id] = user
    }
    return result, nil
}
```

呼叫端可以自由修改 `result`，不會影響 repository 內部狀態。

## 【判讀】slice copy 保護的是底層 array

Slice 的核心風險是 slice header 會被複製，但底層 array 可能共享。直接回傳 slice 會讓呼叫端修改 owner 的內部資料。

```go
type RecentEvents struct {
    mu     sync.RWMutex
    events []Event
}

func (r *RecentEvents) Append(ctx context.Context, event Event) {
    r.mu.Lock()
    defer r.mu.Unlock()

    r.events = append(r.events, event)
}
```

安全的 list method：

```go
func (r *RecentEvents) List(ctx context.Context) []Event {
    r.mu.RLock()
    defer r.mu.RUnlock()

    result := make([]Event, len(r.events))
    copy(result, r.events)
    return result
}
```

`copy` 建立新的底層 array。呼叫端對 `result` 排序、截斷、append 或修改元素，不會改到 `r.events`。

## 【策略】值型別可以 shallow copy，可變欄位需要 deep copy

Copy boundary 的核心判斷是資料裡是否還包含可變 reference。若 struct 只有 string、int、time.Time 這類值型別，shallow copy 通常足夠；若 struct 包含 map、slice 或 pointer，就要考慮 deep copy。

值型別範例：

```go
type Event struct {
    ID        string
    Type      string
    CreatedAt time.Time
}
```

這種 `Event` 放在 slice 裡，用 `copy` 複製 slice 通常足夠。

含可變欄位的範例：

```go
type Event struct {
    ID       string
    Type     string
    Metadata map[string]string
}
```

這時只 copy slice 不夠，因為每個 `Event.Metadata` 仍然指向同一份 map。需要 clone：

```go
func CloneEvent(event Event) Event {
    cloned := event
    if event.Metadata != nil {
        cloned.Metadata = make(map[string]string, len(event.Metadata))
        for key, value := range event.Metadata {
            cloned.Metadata[key] = value
        }
    }
    return cloned
}
```

是否需要 deep copy 取決於 API 承諾。如果呼叫端不應修改 repository 內部資料，就要複製所有可變 reference。

## 【判讀】回傳 pointer 要代表明確修改權

Pointer 回傳的核心語意是呼叫端取得同一份資料的參照。若資料屬於共享狀態，回傳 pointer 通常會破壞 owner 邊界。

容易誤解的 API：

```go
func (r *UserRepository) FindPointer(ctx context.Context, id string) (*User, bool) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    user, ok := r.users[id]
    if !ok {
        return nil, false
    }
    return &user, true
}
```

這段程式回傳的是區域變數 `user` 的指標，不是 map 內部資料的可修改入口。呼叫端修改這個 pointer，不會保存回 repository。API 看起來像能修改，實際不能，語意不清楚。

更清楚的做法是回傳 value，並提供明確 update method：

```go
func (r *UserRepository) UpdateEmail(ctx context.Context, id string, email string) (bool, error) {
    r.mu.Lock()
    defer r.mu.Unlock()

    user, ok := r.users[id]
    if !ok {
        return false, nil
    }

    user.Email = email
    r.users[id] = user
    return true, nil
}
```

修改行為集中在 repository 內，lock、驗證與狀態一致性也留在同一個地方。

## 【策略】mutex 和 channel owner 要按資料形狀選擇

狀態保護的核心選擇是 mutex owner 或 goroutine owner。兩者都符合 Go 的精神，差異在資料存取模式。

| 方法            | 適用情境                 | 代價                            |
| --------------- | ------------------------ | ------------------------------- |
| mutex owner     | 多個方法需要同步讀寫狀態 | 要維護 lock 與 copy boundary    |
| goroutine owner | 所有修改都能表示成訊息   | 要設計 command、reply、shutdown |

Mutex 版本：

```go
repo.Save(ctx, user)
user, ok, err := repo.Find(ctx, id)
```

Goroutine owner 版本：

```go
type command struct {
    kind  string
    user  User
    reply chan result
}
```

不要為了避免 mutex 而把簡單狀態硬改成複雜訊息系統。也不要在需要嚴格順序與單一事件流時到處加 lock。選擇應該來自資料形狀與讀寫模式。

## 【測試】copy boundary 要用外部修改驗證

Copy boundary 的測試核心是呼叫 getter 後修改回傳值，再確認 owner 內部資料沒有被改動。

```go
func TestUsersReturnsCopy(t *testing.T) {
    repo := NewUserRepository()
    ctx := context.Background()

    if err := repo.Save(ctx, User{ID: "user_1", Email: "a@example.com"}); err != nil {
        t.Fatalf("save user: %v", err)
    }

    users, err := repo.Users(ctx)
    if err != nil {
        t.Fatalf("users: %v", err)
    }
    delete(users, "user_1")

    _, ok, err := repo.Find(ctx, "user_1")
    if err != nil {
        t.Fatalf("find user: %v", err)
    }
    if !ok {
        t.Fatalf("repository should not be modified through returned map")
    }
}
```

Slice copy 也用同樣方式測：

```go
func TestEventListReturnsCopy(t *testing.T) {
    events := &RecentEvents{}
    ctx := context.Background()

    events.Append(ctx, Event{ID: "evt_1"})
    got := events.List(ctx)
    got[0].ID = "changed"

    again := events.List(ctx)
    if again[0].ID != "evt_1" {
        t.Fatalf("internal event was modified through returned slice")
    }
}
```

這類測試能直接防止未來有人為了「省 copy」而破壞狀態邊界。

## 【測試】race detector 驗證同步邊界

Race detector 的核心用途是找出未同步的共享記憶體存取。對含有 goroutine、map、slice、repository 的測試，應定期執行：

```bash
go test -race ./...
```

可以用併發測試增加觸發機率：

```go
func TestRepositoryConcurrentAccess(t *testing.T) {
    repo := NewUserRepository()
    ctx := context.Background()

    var wg sync.WaitGroup
    for i := 0; i < 100; i++ {
        i := i
        wg.Add(1)
        go func() {
            defer wg.Done()
            id := fmt.Sprintf("user_%d", i)
            _ = repo.Save(ctx, User{ID: id})
            _, _, _ = repo.Find(ctx, id)
        }()
    }
    wg.Wait()
}
```

這個測試本身不一定能證明沒有所有問題，但搭配 `-race` 可以檢查 repository 方法是否真的包住共享 map。

## 本章不處理

本章先聚焦單一 Go process 內的共享狀態保護；更外層的資料庫交易、快取一致性與資料複製邊界，會在下列章節再往外延伸：

- [Backend：資料庫與持久化](../../backend/01-database/)
- [Backend：快取與 Redis](../../backend/02-cache-redis/)
- [Go 入門：指標與資料複製邊界](../../go/02-types-data/pointers-copy/)

## 和 Go 教材的關係

這一章承接的是 repository、copy boundary 與 state owner；如果你要先回看語言教材，可以讀：

- [Go：如何新增 repository port](../../go/06-practical/repository-port/)
- [Go：如何擴展狀態投影欄位](../../go/06-practical/state-fields/)
- [Go：狀態管理的安全邊界](../../go/07-refactoring/state-boundary/)
- [Go：用 interface 隔離外部依賴](../../go/07-refactoring/interface-boundary/)

## 小結

共享狀態的安全邊界由 owner、lock、copy 與明確修改方法組成。Map/slice 讀寫要經過同一個 owner；getter 不應暴露內部可變資料；含 map、slice、pointer 的 struct 要考慮 deep copy；修改行為應集中在方法內。這些規則能讓長時間運行的 Go 服務避開 data race、外部突變與難以重現的狀態錯誤。
