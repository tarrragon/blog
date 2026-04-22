---
title: "4.3 Source of Truth：狀態邊界"
date: 2026-04-22
description: "集中狀態更新、保護可變資料、設計查詢 projection"
weight: 3
---

Source of truth 的核心原則是系統中只有一個地方負責判定目前狀態。其他元件可以請求更新、讀取快照或訂閱變化，但不能各自保存一份會被當成真相的資料。

## 本章目標

學完本章後，你將能夠：

1. 判斷狀態真相應該由哪個元件擁有
2. 把狀態轉移集中在 repository 或 state owner
3. 同步更新 current state 與 history
4. 用 copy boundary 保護 slice、map、pointer
5. 分辨 internal state、projection 與 response view

---

## 【觀察】狀態分散會讓系統失去真相

狀態分散的核心風險是每個元件都以為自己看到的是最新資料。handler 可能有 map，worker 可能有 cache，publisher 可能有最後推送狀態；當三者不一致時，系統很難回答「現在到底是什麼狀態」。

反模式示意：

```go
var handlerStates = map[string]string{}
var workerStates = map[string]string{}
var publisherLastSent = map[string]string{}
```

這三份資料可能都叫做 state，但只有一份應該是 source of truth。其他資料如果存在，應該明確標示為 cache、projection 或 delivery record，不能被當成狀態判斷依據。

## 【判讀】source of truth 是寫入權責

source of truth 的核心不是「資料存在哪裡」，而是「誰有權決定狀態如何轉移」。memory map、SQLite、PostgreSQL、Redis 都可以承擔儲存；真正的邊界是所有寫入都經過同一組規則。

```go
type AccountStatus string

const (
    AccountPending AccountStatus = "pending"
    AccountActive  AccountStatus = "active"
    AccountBlocked AccountStatus = "blocked"
)

type AccountState struct {
    ID        string
    Status    AccountStatus
    UpdatedAt time.Time
}
```

`AccountState` 是 domain 狀態，不是 HTTP response。它應該表達系統內部真正需要維護的資料，而不是直接迎合某個 API 的輸出格式。

## 【策略】用明確方法集中狀態轉移

狀態轉移的核心規則是呼叫端不能直接改欄位。外部元件應該送進事件或 command，由 state owner 決定是否合法、如何更新、是否記錄 history。

```go
type StateRepository struct {
    mu      sync.RWMutex
    records map[string]AccountRecord
}

type AccountRecord struct {
    Current AccountState
    History []AccountState
}

func NewStateRepository() *StateRepository {
    return &StateRepository{
        records: make(map[string]AccountRecord),
    }
}
```

repository 擁有 `records` map。其他元件不應取得這個 map 的 reference，也不應繞過 repository 修改狀態。

## 【執行】Apply 把事件轉成狀態變化

`Apply` 的核心責任是把 domain event 套用到 state。它是事件系統與狀態系統的交界。

```go
func (r *StateRepository) Apply(ctx context.Context, event DomainEvent) error {
    r.mu.Lock()
    defer r.mu.Unlock()

    record := r.records[event.SubjectID]
    next, err := transition(record.Current, event)
    if err != nil {
        return err
    }

    record.Current = next
    record.History = append(record.History, next)
    r.records[event.SubjectID] = record

    return nil
}
```

這段程式在同一個 lock 內更新 current 與 history。讀者可以相信目前狀態與歷史紀錄來自同一筆事件，不會出現 current 已更新但 history 漏記的情境。

`transition` 可以是純函式：

```go
func transition(current AccountState, event DomainEvent) (AccountState, error) {
    switch event.Type {
    case EventAccountActivated:
        return AccountState{
            ID:        event.SubjectID,
            Status:    AccountActive,
            UpdatedAt: event.OccurredAt,
        }, nil
    default:
        return AccountState{}, fmt.Errorf("unsupported event type: %s", event.Type)
    }
}
```

純函式讓狀態規則更容易測試。repository 負責 concurrency 與保存，transition 負責 domain 規則。

## 【判讀】current、history、projection 是不同資料

狀態資料的核心分類是 internal state、history 與 projection。三者用途不同，不應混成同一個 struct 到處傳。

| 類型           | 角色                     | 範例              |
| -------------- | ------------------------ | ----------------- |
| internal state | 系統判斷真相的資料       | `AccountState`    |
| history        | 狀態變化紀錄             | `[]AccountState`  |
| projection     | 查詢或 UI 需要的讀取模型 | `AccountSummary`  |
| response view  | 特定 API 的輸出格式      | `accountResponse` |

projection 可以從 state 與 history 組出來，但 projection 不應反過來成為狀態真相。API 需要新增欄位時，優先新增 response view 或 projection，不要直接污染 internal state。

## 【執行】查詢要回傳 copy

copy boundary 的核心目標是防止呼叫端修改 repository 內部資料。Go 的 slice、map、pointer 都可能讓內部狀態外洩。

```go
func (r *StateRepository) Current(ctx context.Context, id string) (AccountState, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    record, ok := r.records[id]
    if !ok {
        return AccountState{}, false, nil
    }

    return record.Current, true, nil
}
```

`AccountState` 目前只有值型別欄位，直接回傳值即可。history 是 slice，必須複製：

```go
func (r *StateRepository) History(ctx context.Context, id string) ([]AccountState, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    history := r.records[id].History
    result := make([]AccountState, len(history))
    copy(result, history)
    return result, nil
}
```

若 state 內含 map、slice 或 pointer，還需要 deep copy。copy 有成本，但它是狀態邊界的保護；資料量大時應用分頁或 projection，不應直接暴露內部 slice。

## 【策略】projection 讓查詢需求不污染狀態

projection 的核心用途是服務讀取需求。列表頁、儀表板、即時推送可能需要不同欄位，這些需求不應全部塞進 domain state。

```go
type AccountSummary struct {
    ID              string
    Status          AccountStatus
    LastChangedAt   time.Time
    HistoryCount    int
}

func (r *StateRepository) Summary(ctx context.Context, id string) (AccountSummary, bool, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    record, ok := r.records[id]
    if !ok {
        return AccountSummary{}, false, nil
    }

    return AccountSummary{
        ID:            record.Current.ID,
        Status:        record.Current.Status,
        LastChangedAt: record.Current.UpdatedAt,
        HistoryCount:  len(record.History),
    }, true, nil
}
```

projection 可以由 repository 即時計算，也可以由背景 worker 預先維護。選擇哪一種取決於讀取量、資料量與一致性要求；小型服務先即時計算通常更容易理解。

## 【判讀】mutex 與單一 goroutine 都能成為 state owner

狀態擁有權的核心要求是同一時間只有受控路徑能修改資料。mutex 是常見選擇，單一 goroutine 擁有 state 也是 Go 常見模式。

mutex 版本適合直接方法呼叫：

```go
repository.Apply(ctx, event)
```

單一 goroutine 版本適合事件流：

```go
type stateCommand struct {
    event DomainEvent
    reply chan error
}
```

兩者都可以正確。選擇 mutex 時要小心 copy boundary；選擇 goroutine owner 時要設計 shutdown、reply channel 與 backpressure。不要為了使用 channel 而使用 channel，狀態模型簡單時 mutex 通常更直接。

## 【測試】狀態測試要覆蓋轉移與外洩

狀態邊界的測試目標是確認轉移一致、history 同步、呼叫端不能修改內部資料。

```go
func TestHistoryReturnsCopy(t *testing.T) {
    repo := NewStateRepository()
    event := DomainEvent{
        ID:         "evt_1",
        Type:       EventAccountActivated,
        SubjectID:  "acct_1",
        OccurredAt: time.Now(),
        ReceivedAt: time.Now(),
    }

    if err := repo.Apply(context.Background(), event); err != nil {
        t.Fatalf("apply event: %v", err)
    }

    history, err := repo.History(context.Background(), "acct_1")
    if err != nil {
        t.Fatalf("history: %v", err)
    }
    history[0].Status = AccountBlocked

    again, err := repo.History(context.Background(), "acct_1")
    if err != nil {
        t.Fatalf("history again: %v", err)
    }
    if again[0].Status != AccountActive {
        t.Fatalf("repository state was modified through returned history")
    }
}
```

這個測試檢查的是邊界，不只是結果值。對 Go 服務來說，防止 slice/map 外洩是狀態設計的重要一環。

## 本章不處理

本章不處理資料庫 schema migration、transaction isolation 或 CQRS 的完整架構。這些主題可以接在 repository port 之後逐步加入；本章先處理單一服務內部如何避免狀態真相分裂。後續可接 [資料庫 transaction 與 schema migration](../07-distributed-operations/database-transactions/)。

## 小結

Source of truth 是寫入權責，不是某個特定資料庫。狀態轉移應集中在 repository 或 state owner，current 與 history 要在同一邊界更新，查詢要回傳 copy 或 projection。當狀態真相清楚時，handler、worker、publisher 都能保持簡單，系統也能更容易加入資料庫或新的讀取模型。
