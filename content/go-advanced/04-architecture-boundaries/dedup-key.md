---
title: "4.2 事件去重與語義鍵設計"
date: 2026-04-22
description: "用 entity ID、event type、來源語意與時間窗口建立去重鍵"
weight: 2
---

# 事件去重與語義鍵設計

事件去重的核心規則是用領域語意判斷「哪兩筆事件代表同一件事」。原始 payload、request ID、收到時間和重試次數常常每次都不同，直接拿來比對會讓去重失效。

## 本章目標

學完本章後，你將能夠：

1. 分辨 event ID 去重與 domain key 去重的差異
2. 用 subject、event type、source group 與時間窗口設計 `DedupKey`
3. 避免把不穩定欄位放進去重鍵
4. 設計去重表的過期與清理策略
5. 用 table-driven test 驗證去重邊界

---

## 【觀察】重複事件不一定長得一樣

重複事件的核心困難是外觀可能不同。HTTP callback 可能每次都有新的 request ID，queue message 可能因 retry 改變 delivery tag，timer 可能在下一輪掃描再次產生類似事件。

兩筆外部輸入可能長這樣：

```json
{
  "request_id": "req_1001",
  "event_id": "provider_7788",
  "account_id": "acct_1",
  "event_name": "activated",
  "timestamp": "2026-04-22T10:00:03Z"
}
```

```json
{
  "request_id": "req_1002",
  "event_id": "provider_7788_retry",
  "account_id": "acct_1",
  "event_name": "activated",
  "timestamp": "2026-04-22T10:00:05Z"
}
```

如果直接比對整包 JSON，這兩筆不同；如果從 domain 看，它們可能都是「同一個 account 在同一小段時間內變成 active」。

## 【判讀】去重鍵是語意決策，不是雜湊技巧

去重鍵的核心責任是把「相同事件」的定義寫進型別。它不是單純把 payload 做 hash；hash 只能回答 bytes 是否相同，不能回答領域事件是否相同。

```go
type DedupKey struct {
    SubjectID string
    Type      EventType
    SourceSet string
    Window    int64
}
```

這個 key 表示：同一個 subject、同一種 event type、同一組來源語意、落在同一個時間窗口的事件，視為同一件事。

`SourceSet` 不一定等於原始來源名稱。多個來源若只是同一件事的不同傳輸管道，可以映射到同一個 source set；若兩個來源代表不同權威資料，則應分開。

## 【策略】先選擇去重層級

去重層級的核心選擇是 event ID、domain key 或兩者並用。不同層級解決的問題不同。

| 去重方式 | 判斷依據 | 適用情境 | 風險 |
|----------|----------|----------|------|
| event ID | 外部或內部 event ID 相同 | 上游提供穩定唯一 ID | 上游 retry 可能換 ID |
| domain key | subject、type、時間窗口相同 | 多來源可能描述同一件事 | key 設太粗會誤殺事件 |
| 兩者並用 | event ID 先判斷，再用 domain key 補強 | 上游 ID 大多可信但不完全穩定 | 實作與測試較複雜 |

小型服務可以先使用 domain key。若上游提供可靠 event ID，則 event ID 可以成為第一層快速去重，domain key 作為跨來源重複的保護。

## 【執行】用內部事件建立 DedupKey

`DedupKey` 應該建立在 `DomainEvent` 上，而不是 raw input 上。這能讓 HTTP、queue、timer 進來的同類事件共用去重規則。

```go
func NewDedupKey(event DomainEvent, window time.Duration) DedupKey {
    return DedupKey{
        SubjectID: event.SubjectID,
        Type:      event.Type,
        SourceSet: sourceSet(event.Source),
        Window:    event.OccurredAt.UnixNano() / int64(window),
    }
}

func sourceSet(source EventSource) string {
    switch source {
    case SourceHTTPCallback, SourceQueue:
        return "external_delivery"
    case SourceTimer:
        return "internal_scan"
    default:
        return string(source)
    }
}
```

`OccurredAt` 通常比 `ReceivedAt` 更適合事件語意去重。兩筆 retry 可能收到時間不同，但實際描述的發生時間相近；若使用收到時間，系統忙碌或網路延遲就會改變去重結果。

## 【判讀】哪些欄位不該放進 key

去重鍵的核心限制是不能包含每次都會變的欄位。這類欄位適合用於追蹤、除錯或觀測，不適合用於判斷是否同一事件。

不適合放進 key 的欄位：

- `request_id`：每次 request 都可能不同。
- `received_at`：取決於系統接收時間，不一定是事件語意。
- `delivery_attempt`：重試次數本身就是重複事件的證據。
- raw payload hash：欄位順序、metadata 或非語意欄位可能改變。
- client IP、瀏覽器識別字串：代表傳輸脈絡，不代表事件本身。

適合放進 key 的欄位：

- subject ID：事件作用的對象。
- event type：發生了什麼事。
- source set：資料權威或來源語意。
- occurred time window：同一事件可接受的時間範圍。

## 【策略】時間窗口是取捨

時間窗口的核心作用是容忍短時間內的重送。窗口越短，越不容易誤殺不同事件；窗口越長，越能吸收延遲與 retry。

```go
const defaultDedupWindow = 30 * time.Second
```

窗口大小應該依事件語意決定：

| 事件類型 | 可用窗口 | 理由 |
|----------|----------|------|
| account activated | 1-5 分鐘 | 同一 account 短時間重複啟用通常是 retry |
| notification created | 不一定適合時間窗口 | 使用者可能短時間建立多筆通知 |
| job finished | 30 秒-2 分鐘 | job 完成事件通常只應發生一次 |
| heartbeat received | 不應去重成單一事件 | heartbeat 本身就是週期訊號 |

時間窗口不是萬用答案。若事件本身允許短時間內多次發生，就需要更細的 subject 或 event ID，而不是把窗口調小到碰運氣。

## 【執行】Deduper 要保護共享 map

in-memory deduper 的核心責任是記住近期看過的 key，並在多 goroutine 下保持安全。只要 processor 可能同時處理事件，就需要 mutex 或單一 goroutine 擁有去重表。

```go
type Deduper struct {
    mu      sync.Mutex
    seen    map[DedupKey]time.Time
    window  time.Duration
    expires time.Duration
}

func NewDeduper(window, expires time.Duration) *Deduper {
    return &Deduper{
        seen:    make(map[DedupKey]time.Time),
        window:  window,
        expires: expires,
    }
}

func (d *Deduper) Seen(ctx context.Context, event DomainEvent) (bool, error) {
    d.mu.Lock()
    defer d.mu.Unlock()

    key := NewDedupKey(event, d.window)
    if _, ok := d.seen[key]; ok {
        return true, nil
    }

    d.seen[key] = event.ReceivedAt
    return false, nil
}
```

`ctx` 在 memory 實作中可能用不到，但保留在 port 上能讓未來改成 Redis、資料庫或遠端服務時支援取消與逾時。

## 【執行】去重表必須清理

去重表的核心風險是無限制成長。只要把 key 放進 map，就必須定義 key 何時過期。

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

`expires` 通常應該大於 `window`。窗口決定兩筆事件是否可能被視為相同，過期時間決定 key 在記憶體中保留多久；兩者不是同一個概念。

## 【測試】用 table-driven test 固定語意

去重測試的核心目標是把「什麼算相同」寫成案例。這比只測 map 是否有資料更重要。

```go
func TestDedupKey(t *testing.T) {
    base := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    tests := []struct {
        name string
        a    DomainEvent
        b    DomainEvent
        same bool
    }{
        {
            name: "same subject type and window",
            a: DomainEvent{SubjectID: "acct_1", Type: EventAccountActivated, Source: SourceHTTPCallback, OccurredAt: base},
            b: DomainEvent{SubjectID: "acct_1", Type: EventAccountActivated, Source: SourceQueue, OccurredAt: base.Add(5 * time.Second)},
            same: true,
        },
        {
            name: "different subject",
            a: DomainEvent{SubjectID: "acct_1", Type: EventAccountActivated, Source: SourceHTTPCallback, OccurredAt: base},
            b: DomainEvent{SubjectID: "acct_2", Type: EventAccountActivated, Source: SourceHTTPCallback, OccurredAt: base},
            same: false,
        },
        {
            name: "outside window",
            a: DomainEvent{SubjectID: "acct_1", Type: EventAccountActivated, Source: SourceHTTPCallback, OccurredAt: base},
            b: DomainEvent{SubjectID: "acct_1", Type: EventAccountActivated, Source: SourceHTTPCallback, OccurredAt: base.Add(2 * time.Minute)},
            same: false,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := NewDedupKey(tt.a, time.Minute) == NewDedupKey(tt.b, time.Minute)
            if got != tt.same {
                t.Fatalf("same key = %v, want %v", got, tt.same)
            }
        })
    }
}
```

這個測試把來源融合、subject 差異與時間窗口都明確化。未來調整 key 時，測試會提醒你正在改變事件語意，而不只是改一個 struct。

## 本章不處理

本章不處理跨節點去重的一致性問題。多台服務同時消費事件時，memory map 不足以保證全域去重；那需要 Redis、資料庫唯一鍵、queue 去重能力或 idempotency store。後續可接 [Durable queue、outbox 與 idempotency](../07-distributed-operations/outbox-idempotency/)。

## 小結

事件去重是領域語意設計，不是 payload 比對。好的 `DedupKey` 會使用 subject、event type、source set 與合適的 occurred time window，並避免 request ID、收到時間與 raw payload hash 這類不穩定欄位。去重表還必須有清理策略，否則事件系統會用記憶體 leak 換取短期正確性。
