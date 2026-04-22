---
title: "7.3 事件去重邏輯的重構策略"
date: 2026-04-22
description: "保留語義鍵並降低重複流程"
weight: 3
---

# 事件去重邏輯的重構策略

事件去重重構的核心目標是把語義鍵、時間窗口與來源優先順序整理成可測規則。本章用一般事件處理流程說明如何降低重複邏輯，同時保留事件合併的判斷依據。

## 本章目標

學完本章後，你將能夠：

1. 辨識 raw payload 去重的風險
2. 用 domain dedup key 表達同一件事
3. 把去重邏輯抽成 `Deduper`
4. 設計時間窗口與 cleanup
5. 測試同窗口、跨窗口、不同來源與過期清理

---

## 【觀察】重複事件通常先散落在入口層

去重邏輯重構的核心觸發點是多個入口開始各自判斷「這筆事件看過了嗎」。HTTP callback、queue consumer、background worker 或 WebSocket action 都可能收到同一件事，若每個入口各自去重，規則很快會不一致。

重構前常見寫法：

```go
var seenHTTPEvents = map[string]bool{}

func handleCallback(w http.ResponseWriter, r *http.Request) {
    var raw RawNotificationCallback
    _ = json.NewDecoder(r.Body).Decode(&raw)

    key := raw.NotificationID + ":" + raw.EventName + ":" + raw.Timestamp
    if seenHTTPEvents[key] {
        w.WriteHeader(http.StatusOK)
        return
    }
    seenHTTPEvents[key] = true

    // update state...
}
```

worker 裡又有另一套：

```go
var seenWorkerEvents = map[string]time.Time{}

func handleWorkerUpdate(update RawNotificationUpdate) {
    key := update.ID
    if _, ok := seenWorkerEvents[key]; ok {
        return
    }
    seenWorkerEvents[key] = time.Now()

    // update state...
}
```

這兩段程式都在去重，但依據不同。一個用 notification ID、event name、timestamp；另一個用 raw event ID。當兩個來源描述同一件 domain event 時，它們無法互相辨識。

## 【判讀】raw payload 不適合當去重依據

raw payload 去重的核心問題是來源格式不是 domain 語意。不同來源可能使用不同欄位名稱、timestamp 精度、metadata 或 request ID，但仍然描述同一件事。

容易造成誤判的欄位：

| 欄位 | 問題 |
|------|------|
| request ID | 每次重送都可能不同 |
| received timestamp | 取決於系統收到時間，不是發生時間 |
| raw payload hash | 欄位順序或 metadata 變化會改變 hash |
| source-specific ID | 不同來源可能沒有共同 ID |
| debug metadata | 不代表事件語意 |

去重應該發生在 normalized `DomainEvent` 上，而不是 raw HTTP body、queue message 或 worker update 上。

## 【策略】domain dedup key 表達同一件事

domain dedup key 的核心責任是回答「哪兩筆事件應該被視為同一件 domain fact」。常見欄位是 subject kind、subject ID、event type 與時間窗口。

```go
type DedupKey struct {
    SubjectKind SubjectKind
    SubjectID   string
    EventType   EventType
    Window      int64
}

func NewDedupKey(event DomainEvent, window time.Duration) DedupKey {
    return DedupKey{
        SubjectKind: event.SubjectKind,
        SubjectID:   event.SubjectID,
        EventType:   event.Type,
        Window:      event.OccurredAt.UnixNano() / int64(window),
    }
}
```

這個 key 不包含 `Source`，因為不同來源可能送來同一件事。是否包含 source 是一個 domain 決策：如果不同來源代表不同事實，就包含；如果不同來源只是同一事實的不同通道，就不要包含。

時間窗口是容忍來源時間差的折衷。窗口太小會漏掉重複事件，窗口太大可能合併兩件獨立事件。

## 【執行】抽出 Deduper

`Deduper` 的核心責任是保存已看過的 key，並回報目前事件是否重複。它不應知道 HTTP、WebSocket 或 queue，也不應更新狀態。

```go
type Deduper struct {
    mu      sync.Mutex
    seen    map[DedupKey]time.Time
    window  time.Duration
    expires time.Duration
}

func NewDeduper(window time.Duration, expires time.Duration) *Deduper {
    return &Deduper{
        seen:    make(map[DedupKey]time.Time),
        window:  window,
        expires: expires,
    }
}
```

`Seen` 判斷是否看過：

```go
func (d *Deduper) Seen(event DomainEvent) bool {
    d.mu.Lock()
    defer d.mu.Unlock()

    key := NewDedupKey(event, d.window)
    if _, ok := d.seen[key]; ok {
        return true
    }

    d.seen[key] = event.ReceivedAt
    return false
}
```

這裡用 `ReceivedAt` 作為清理基準，因為清理是系統內部記憶體管理問題；去重 key 則用 `OccurredAt`，因為那是事件發生語意。兩個時間各有用途，不應混用。

## 【執行】processor 使用 Deduper

重構後的核心方向是讓所有來源先 normalize 成 `DomainEvent`，再交給同一個 processor 去重與套用規則。

```go
type EventProcessor struct {
    deduper    *Deduper
    repository EventRepository
    publisher  Publisher
}

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

    return p.publisher.Publish(ctx, event)
}
```

這個位置比 handler 或 worker 更適合去重，因為 processor 已經面對 normalized domain event。新增事件來源時，只要它走同一個 processor，就自然共用同一套去重規則。

## 【策略】來源優先順序要顯式化

來源優先順序的核心問題是重複事件不一定完全相同。有些來源即時但資料少，有些來源延遲但資料完整。若需要合併資料，就要把 priority rule 寫成可測規則。

先定義 priority：

```go
func SourcePriority(source EventSource) int {
    switch source {
    case SourceHTTPCallback:
        return 100
    case SourceClientCommand:
        return 80
    case SourceTimer:
        return 50
    default:
        return 0
    }
}
```

若 deduper 只需要判斷 seen，就不處理 priority。若系統需要「較高 priority 事件可以取代較低 priority 事件」，應把 deduper 改成更明確的 result：

```go
type DedupDecision int

const (
    DedupAccept DedupDecision = iota
    DedupDrop
    DedupReplace
)
```

不要把 priority 規則藏在 `if` 裡。它是 domain policy，應該可以被直接測試。

## 【執行】cleanup 防止去重表無限成長

cleanup 的核心責任是移除過期 key，防止去重表變成記憶體 leak。只要 `seen` 是 map，就必須設計生命週期。

```go
func (d *Deduper) Cleanup(now time.Time) {
    d.mu.Lock()
    defer d.mu.Unlock()

    for key, seenAt := range d.seen {
        if now.Sub(seenAt) > d.expires {
            delete(d.seen, key)
        }
    }
}
```

cleanup 可以由 background worker 定期呼叫：

```go
func RunDeduperCleanup(ctx context.Context, deduper *Deduper, interval time.Duration, now func() time.Time) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            deduper.Cleanup(now())
        }
    }
}
```

這裡注入 `now` 是為了測試。清理策略不應依賴測試中的真實等待。

## 【執行】同窗口去重測試

同窗口測試的核心目標是確認兩筆語意相同、時間接近的事件會共用 key。

```go
func TestDeduperSeenSameWindow(t *testing.T) {
    deduper := NewDeduper(time.Minute, time.Hour)
    base := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    first := DomainEvent{
        ID:          "evt_1",
        Type:        EventNotificationCreated,
        SubjectKind: SubjectNotification,
        SubjectID:   "ntf_1",
        OccurredAt:  base,
        ReceivedAt:  base,
    }
    second := first
    second.ID = "evt_2"
    second.ReceivedAt = base.Add(5 * time.Second)

    if deduper.Seen(first) {
        t.Fatalf("first event should not be duplicate")
    }
    if !deduper.Seen(second) {
        t.Fatalf("second event in same window should be duplicate")
    }
}
```

這個測試刻意讓 ID 不同，證明去重不是依賴 raw event ID，而是依賴 domain key。

## 【執行】跨窗口不去重測試

跨窗口測試的核心目標是確認兩件不同時間窗口的事件不會被誤合併。

```go
func TestDeduperSeenDifferentWindow(t *testing.T) {
    deduper := NewDeduper(time.Minute, time.Hour)
    base := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    first := DomainEvent{
        ID:          "evt_1",
        Type:        EventNotificationCreated,
        SubjectKind: SubjectNotification,
        SubjectID:   "ntf_1",
        OccurredAt:  base,
        ReceivedAt:  base,
    }
    second := first
    second.ID = "evt_2"
    second.OccurredAt = base.Add(2 * time.Minute)
    second.ReceivedAt = base.Add(2 * time.Minute)

    _ = deduper.Seen(first)
    if deduper.Seen(second) {
        t.Fatalf("event in different window should not be duplicate")
    }
}
```

窗口大小是一個業務取捨，測試可以讓這個取捨變成明確規格。

## 【執行】cleanup 測試不應 sleep

cleanup 測試的核心目標是確認過期 key 會被移除。測試應直接傳入時間，不要真的等待過期。

```go
func TestDeduperCleanup(t *testing.T) {
    deduper := NewDeduper(time.Minute, time.Minute)
    base := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    event := DomainEvent{
        ID:          "evt_1",
        Type:        EventNotificationCreated,
        SubjectKind: SubjectNotification,
        SubjectID:   "ntf_1",
        OccurredAt:  base,
        ReceivedAt:  base,
    }

    _ = deduper.Seen(event)
    deduper.Cleanup(base.Add(2 * time.Minute))

    if deduper.Seen(event) {
        t.Fatalf("event should be accepted after cleanup")
    }
}
```

這個測試能快速完成，也不受機器速度影響。

## 重構步驟

把散落的去重邏輯收斂到 `Deduper` 時，可以按這個順序：

1. 先列出所有入口目前的去重 key。
2. 找出它們真正想表達的 domain 語意。
3. 建立 `DedupKey`，使用 subject、event type 與時間窗口。
4. 把 raw input 先 normalize 成 `DomainEvent`。
5. 在 processor 中呼叫 `Deduper.Seen`。
6. 移除 handler、worker 內的重複 map。
7. 補同窗口、跨窗口、不同來源與 cleanup 測試。

不要一開始就把所有事件融合規則做完。先把「是否看過」集中，再處理 priority 或 replace policy。

## 常見錯誤

### 錯誤一：用 raw payload hash 去重

payload hash 對格式變化太敏感。欄位順序、metadata 或 timestamp 精度改變，都會讓同一件事看起來不同。

### 錯誤二：把 ReceivedAt 當事件發生時間

`ReceivedAt` 是系統收到時間。事件是否同一件事，通常應看 `OccurredAt` 與 subject 語意。

### 錯誤三：去重表沒有 cleanup

任何「看過的 key」map 都會成長。沒有 cleanup 的 deduper 會在長時間服務中累積記憶體壓力。

### 錯誤四：來源 priority 沒有測試

若不同來源資料完整度不同，priority 是 domain policy。它應該有明確函式與測試，而不是散落在 processor 的條件判斷裡。

## 本章不處理

- 不實作分散式去重。
- 不使用外部 cache 或資料庫保存 dedup key。
- 不設計完整 event sourcing replay。
- 不處理跨服務 exactly-once 語意。

如果去重需要跨 process、queue retry 或 idempotency store，可以接著閱讀 [Go 進階：Durable queue、outbox 與 idempotency](../../go-advanced/07-distributed-operations/outbox-idempotency/)。

## 小結

事件去重重構的重點是把判斷依據從 raw input 移到 domain event。`DedupKey` 表達哪兩筆事件是同一件事，`Deduper` 保存已看過的 key，processor 統一套用去重規則，cleanup 管理記憶體生命週期。當去重變成可測規則，新增來源時才不會複製一套相似但不一致的判斷。
