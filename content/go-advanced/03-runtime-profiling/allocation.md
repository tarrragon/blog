---
title: "3.4 資料結構與 allocation 壓力"
date: 2026-04-22
description: "分析列表、歷史資料與 WebSocket payload 的配置成本"
weight: 4
---

Allocation 分析的核心目標是區分必要的安全複製與可優化的重複配置。Go 服務中很多配置來自 slice 成長、map/list 複製、JSON marshal、[buffer](/backend/knowledge-cards/buffer/) 建立與 [WebSocket](/backend/knowledge-cards/websocket/) payload；優化前要先確認配置是否位於熱路徑，且不能破壞狀態邊界。

## 本章目標

學完本章後，你將能夠：

1. 理解 allocation 如何增加 GC 壓力
2. 分辨必要 copy boundary 與不必要重複配置
3. 用預配置降低 slice 成長成本
4. 判斷 JSON marshal 與 WebSocket payload 的重用邊界
5. 用 pprof 的 `alloc_space` 與 `inuse_space` 決定優化方向

---

## 【觀察】allocation 壓力會放大 GC 成本

Allocation 的核心影響是增加 heap 成長速度，進而增加 GC 工作量。即使物件很快被回收，大量短命配置仍可能造成 CPU 與 latency 壓力。

常見熱路徑：

- 每次 WebSocket broadcast 都對每個 client 重新 marshal。
- 每次 API list 都建立大型 slice。
- 每次 repository 查詢都 copy 大型 map。
- 每次 [log](/backend/knowledge-cards/log/) 都組大量臨時欄位。
- 每次 encode 都建立新的 `bytes.Buffer`。

不是所有 allocation 都要消除。診斷重點是找出高頻、可避免、且不破壞邊界的配置。

## 【判讀】預配置解決的是成長成本

Slice 預配置的核心用途是讓底層 array 成長符合預期。若結果長度可預估，應用 `make` 設定容量。

未預配置：

```go
func BuildNames(users []User) []string {
    var names []string
    for _, user := range users {
        names = append(names, user.Name)
    }
    return names
}
```

預配置：

```go
func BuildNames(users []User) []string {
    names := make([]string, 0, len(users))
    for _, user := range users {
        names = append(names, user.Name)
    }
    return names
}
```

這不是微優化。若這段程式在高頻 list API、background [projection](/backend/knowledge-cards/projection/) 或 broadcast path 中執行，預配置可以減少反覆擴容與 copy。

## 【判讀】copy boundary 是必要成本

安全複製的核心目的不是效能，而是保護內部可變狀態。Repository 回傳資料時 copy slice 或 map，會增加 allocation，但能避免外部突變與 data race。

```go
func (r *UserRepository) ListUsers(ctx context.Context) ([]User, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()

    users := make([]User, 0, len(r.users))
    for _, user := range r.users {
        users = append(users, user)
    }
    return users, nil
}
```

這個 allocation 是狀態邊界的成本。優化前要先確認它是否真的是瓶頸，不能只因為 profile 看到配置就移除 copy。

若列表很大且讀取頻繁，應考慮分頁、projection、snapshot cache 或只回傳必要欄位。不要為了省配置而直接暴露內部 map。

## 【策略】大型 list 優先改資料形狀

大型 list allocation 的核心問題常常不是 copy 本身，而是 API 一次回太多資料。若每次請求都複製整個 repository，配置與延遲都會隨資料量線性成長。

可選策略：

| 策略               | 適用情境               | 代價                                                          |
| ------------------ | ---------------------- | ------------------------------------------------------------- |
| 分頁               | 使用者只需要部分資料   | API 需要 cursor 或 [offset](/backend/knowledge-cards/offset/) |
| projection         | 只需要摘要欄位         | 要維護讀取模型                                                |
| snapshot cache     | 讀多寫少               | 要處理快取失效                                                |
| incremental update | WebSocket 推送最新變化 | client 要能合併狀態                                           |

優化資料形狀通常比取消 copy 更安全。Copy boundary 保護正確性，資料形狀決定每次 copy 的成本。

## 【執行】JSON marshal 是 WebSocket 常見配置來源

JSON 序列化的核心成本是把 Go 資料結構轉成 bytes。高頻 WebSocket 推送若對每個 client 反覆 marshal 同一份 message，會造成大量短命配置。

反模式：

```go
for _, client := range clients {
    payload, err := json.Marshal(message)
    if err != nil {
        return err
    }
    client.SendBytes(payload)
}
```

同一份 message 可以先 marshal 一次：

```go
payload, err := json.Marshal(message)
if err != nil {
    return err
}

for _, client := range clients {
    client.SendBytes(payload)
}
```

這個優化的前提是 `payload` 被視為只讀。Send path 不應修改傳入的 bytes；若某個 client 需要修改，就應在該 client 邊界 copy，而不是讓共享 payload 被改動。

## 【判讀】bytes 重用要先定義所有權

Bytes 重用的核心風險是共享 slice 被修改。`[]byte` 是可變資料，傳給多個 client 時要明確規定它只讀。

可以用型別或註解表達語意：

```go
type EncodedMessage []byte

func (c *Client) SendEncoded(message EncodedMessage) bool {
    return c.TrySend(ServerMessage{
        Encoded: message,
    })
}
```

這不能從型別上完全禁止修改，但能讓 API 語意更清楚。真正保護仍靠 ownership 規則、測試與 code review。

若無法保證下游不修改，就必須 copy：

```go
func CloneBytes(input []byte) []byte {
    output := make([]byte, len(input))
    copy(output, input)
    return output
}
```

效能優化不能建立在模糊的可變資料共享上。

## 【策略】sync.Pool 只適合已證明的熱路徑

`sync.Pool` 的核心用途是複用高頻、短命、可重建的暫存物件。它可以降低配置，但會增加所有權複雜度。

```go
var bufferPool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}

func Encode(value any) ([]byte, error) {
    buf := bufferPool.Get().(*bytes.Buffer)
    defer bufferPool.Put(buf)
    buf.Reset()

    if err := json.NewEncoder(buf).Encode(value); err != nil {
        return nil, err
    }

    output := append([]byte(nil), buf.Bytes()...)
    return output, nil
}
```

這裡仍然 copy 出 `output`，因為 `buf` 會被放回 pool。若直接回傳 `buf.Bytes()`，呼叫端拿到的 slice 可能在 pool 重用後被覆寫。

不要一開始就使用 `sync.Pool`。先用 pprof 證明配置是瓶頸，再評估 pool 是否值得承擔額外複雜度。

## 【判讀】inuse 與 alloc 回答不同問題

Heap profile 的核心判讀是分清 `inuse_space` 與 `alloc_space`。

```bash
go tool pprof http://localhost:8080/debug/pprof/heap
go tool pprof -alloc_space http://localhost:8080/debug/pprof/heap
```

| 指標             | 問題             | 常見修正                               |
| ---------------- | ---------------- | -------------------------------------- |
| `inuse_space` 高 | 現在誰保留記憶體 | cache 淘汰、釋放引用、限制 buffer      |
| `alloc_space` 高 | 誰累積配置最多   | 預配置、重用、減少 marshal、改資料形狀 |

若 `alloc_space` 高但 `inuse_space` 不高，代表配置很多但大多被回收，問題可能是 GC 壓力。若 `inuse_space` 持續上升，代表資料被長期保留，應檢查 cache、map、slice、goroutine reference 或 send buffer。

## 【策略】allocation 優化要保留正確性邊界

Allocation 優化的核心底線是不能破壞狀態安全。以下做法通常不可接受：

- 為了省 copy，直接回傳 repository 內部 map。
- 為了省 bytes，讓多個 client 共享可修改 payload。
- 為了省 allocation，把 buffer 放回 pool 後仍回傳其底層 slice。
- 為了少建立 struct，把 request DTO 和 domain state 混用。

較安全的優化順序：

1. 用 pprof 確認熱點。
2. 預配置已知大小的 slice/map。
3. 減少重複 marshal。
4. 改 API 資料形狀，例如分頁或 projection。
5. 最後才考慮 `sync.Pool`。

這個順序先處理低風險、高可讀性的改動，再處理高複雜度工具。

## 【測試】優化後要補邊界測試

Allocation 優化的測試核心是確保共享資料沒有被外部修改。若你重用 bytes、snapshot 或 pooled buffer，要補測試保護 ownership。

例如 repository list 仍要回傳 copy：

```go
func TestListUsersReturnsCopy(t *testing.T) {
    repo := NewUserRepository()
    ctx := context.Background()
    _ = repo.Save(ctx, User{ID: "user_1"})

    users, err := repo.ListUsers(ctx)
    if err != nil {
        t.Fatalf("list users: %v", err)
    }
    users[0].ID = "changed"

    again, err := repo.ListUsers(ctx)
    if err != nil {
        t.Fatalf("list users again: %v", err)
    }
    if again[0].ID != "user_1" {
        t.Fatalf("repository data was modified through returned slice")
    }
}
```

這種測試能防止未來為了省 allocation 而移除必要 copy。

## 本章不處理

本章先處理熱路徑上的配置與資料形狀；更大範圍的序列化與 payload 策略，會在下列章節再往外延伸：

- [Go 入門：struct 與 JSON tag](/go/02-types-data/struct-json/)
- [Go 入門：slice 與 map](/go/02-types-data/slices-maps/)
- [Go 入門：指標與資料複製邊界](/go/02-types-data/pointers-copy/)
- [Go 進階：pprof 基礎診斷流程](/go-advanced/03-runtime-profiling/pprof/)

## 和 Go 教材的關係

這一章承接的是 copy boundary、JSON 與 runtime profile；如果你要先回看語言教材，可以讀：

- [Go：如何擴展狀態投影欄位](/go/06-practical/state-fields/)
- [Go：如何新增 repository port](/go/06-practical/repository-port/)
- [Go：如何新增一個即時訊息 action](/go/06-practical/new-websocket-action/)
- [Go：狀態管理的安全邊界](/go/07-refactoring/state-boundary/)

## 小結

Allocation 優化要先判斷配置是否必要。保護狀態的 copy 是合理成本，高頻熱路徑的重複配置才是優先目標。JSON marshal、slice 成長、map/list 複製與 buffer 建立都是常見來源；用 pprof 區分 `inuse_space` 與 `alloc_space` 後，再決定預配置、分頁、projection、payload 重用或 `sync.Pool`。
