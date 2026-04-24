---
title: "5.3 race condition 檢查"
date: 2026-04-22
description: "用 go test -race 找資料競爭"
weight: 3
---

Race detector 的核心作用是找出測試執行期間發生的 data race。它能指出未同步讀寫同一份記憶體的位置，但不能取代 ownership、mutex、channel 與狀態邊界設計。

## 本章目標

學完本章後，你將能夠：

1. 分辨 data race 與一般邏輯競爭
2. 用 `go test -race ./...` 檢查並發路徑
3. 寫出能觸發共享狀態讀寫的測試
4. 依 race report 找到讀寫來源
5. 選擇 mutex、channel owner 或 atomic 修正同步邊界

---

## 【觀察】並發 bug 常常不會穩定重現

Data race 的核心問題是測試可能偶爾通過、偶爾失敗，也可能完全不失敗但資料已經不安全。單次執行結果正確，不代表沒有未同步讀寫。

反模式：

```go
var count int

func increment() {
    count++
}
```

`count++` 不是原子操作。它包含讀取、加一、寫回。多個 goroutine 同時執行時，可能互相覆蓋結果，也可能被 race detector 偵測到未同步讀寫。

## 【判讀】data race 是未同步的並發讀寫

Data race 的核心定義是至少兩個 goroutine 同時存取同一份記憶體，其中至少一個是寫入，而且沒有同步保護。

觸發測試：

```go
func TestIncrementRace(t *testing.T) {
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            increment()
        }()
    }

    wg.Wait()
}
```

一般 `go test` 不一定會失敗。`go test -race` 會在 runtime 偵測這類未同步讀寫，並輸出讀取與寫入發生的位置。

## 【執行】用 go test -race 跑到相關路徑

Race detector 的核心限制是只能檢查實際執行到的程式路徑。沒有被測試覆蓋的 goroutine、handler、repository 或 broadcast path，不會被它發現。

```bash
go test -race ./...
```

這個指令會用 race detector 跑所有 package 的測試。它會比一般測試慢，但對含有 goroutine、共享 map、[WebSocket](../../../backend/knowledge-cards/websocket/) hub、background worker 的服務非常重要。

若專案很大，可以先針對相關 package：

```bash
go test -race ./internal/websocket ./internal/storage ./internal/worker
```

範圍縮小能讓日常執行更快，但合併前仍應跑完整路徑。

## 【策略】併發測試要讓共享狀態真的被同時讀寫

Race detector 的核心前提是測試要製造相關路徑。只建立 repository 卻不並發讀寫，race detector 沒有機會回報。

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

這個測試的主要斷言不在輸出值，而在「讓 race detector 執行共享 map 的讀寫路徑」。若 repository 忘記加 lock，`-race` 會指出問題。

## 【執行】WebSocket hub 也需要 race path

WebSocket hub 的核心並發風險是 client 註冊、取消註冊、訂閱變更與 broadcast 可能同時發生。測試應讓這些路徑交錯執行。

```go
func TestHubConcurrentBroadcastAndUnregister(t *testing.T) {
    hub := NewHub()
    clients := make([]*Client, 0, 100)

    for i := 0; i < 100; i++ {
        client := NewTestClient(fmt.Sprintf("client_%d", i), 8)
        client.Subscribe("alerts")
        hub.clients[client] = struct{}{}
        clients = append(clients, client)
    }

    var wg sync.WaitGroup
    wg.Add(2)

    go func() {
        defer wg.Done()
        for i := 0; i < 100; i++ {
            hub.Broadcast("alerts", ServerMessage{Type: "notification"})
        }
    }()

    go func() {
        defer wg.Done()
        for _, client := range clients {
            hub.unregisterClient(client)
        }
    }()

    wg.Wait()
}
```

這個測試是否需要 lock，取決於 hub 的設計。如果 hub 保證所有操作都在單一 event loop 中執行，測試就應該透過 channel 操作，而不是直接呼叫未同步方法。測試要符合 ownership 設計，不應製造不被 API 允許的並發。

## 【判讀】race report 要看讀寫兩端

Race report 的核心資訊是兩個位置：一端讀或寫，另一端寫。修正時不要只看最後一行，要找出是哪個共享資料缺少同步。

典型報告會包含：

```text
WARNING: DATA RACE
Read at 0x...
  example.com/app.(*UserRepository).Find()

Previous write at 0x...
  example.com/app.(*UserRepository).Save()
```

這表示 `Find` 和 `Save` 同時碰到同一份資料，且缺少同步。修正方向不是在測試裡加等待，而是在 repository owner 補上 mutex、channel ownership 或其他同步邊界。

## 【策略】修正方式要對應狀態形狀

修正 data race 的核心選擇是建立正確同步邊界。常見方法有 mutex、channel owner、atomic。

| 方法          | 適用情境                         | 注意事項                                                                               |
| ------------- | -------------------------------- | -------------------------------------------------------------------------------------- |
| mutex         | 多方法讀寫同一份 map/slice/state | lock 要保護完整不變式                                                                  |
| channel owner | 狀態修改可集中成事件 loop        | 要設計 reply、shutdown、[backpressure](../../../backend/knowledge-cards/backpressure/) |
| atomic        | 單一數值 counter 或 flag         | 不適合複雜狀態                                                                         |

Mutex 範例：

```go
type Counter struct {
    mu    sync.Mutex
    value int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}
```

鎖應該屬於擁有狀態的型別，並保護一個清楚的不變條件。只為了讓 race detector 安靜而到處加鎖，會讓 ownership 分散，後續仍然難以判斷資料一致性。

## 【判讀】race-free 不代表行為正確

Race detector 的核心邊界是它只找 data race，不保證並發邏輯正確。沒有 data race 的程式仍可能 deadlock、漏訊息、順序錯誤、重複 close 或違反資料語意。

例如：

```go
select {
case client.send <- message:
default:
    // drop
}
```

這段程式可能沒有 data race，但「[queue](../../../backend/knowledge-cards/queue/) full 時丟訊息」是否正確是服務語意問題。Race detector 不會告訴你該丟、該斷線、還是該寫可靠 queue。

因此並發測試要分成兩層：

- 用 `go test -race` 找未同步記憶體存取。
- 用行為測試檢查 channel close、queue full、context cancel、cleanup、[timeout](../../../backend/knowledge-cards/timeout/)。

## 【測試】把 race check 納入固定流程

Race check 的核心價值來自重複執行。只在出事後手動跑，效果有限。

建議流程：

```bash
go test ./...
go test -race ./...
```

日常開發可以先跑相關 package，提交前或 CI 跑完整 race suite。若 race suite 太慢，至少讓含有 hub、repository、worker、client state 的 package 固定跑 `-race`。

## 本章不處理

本章先處理共享 state、channel ownership 與 goroutine lifecycle 的 race 風險；lock-free 與完整 memory model，會在下列章節再往外延伸：

- [Go 進階：共享狀態與複製邊界](../../01-concurrency-patterns/shared-state/)
- [Go 進階：channel ownership 與關閉責任](../../01-concurrency-patterns/channel-ownership/)
- [Go 進階：select loop 的生命週期設計](../../01-concurrency-patterns/select-loop/)

## 和 Go 教材的關係

這一章承接的是共享狀態、channel ownership 與 lifecycle；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../../go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與 backpressure ](../../../go/04-concurrency/channel/)
- [Go：狀態管理的安全邊界](../../../go/07-refactoring/state-boundary/)
- [Go：如何新增背景工作流程](../../../go/06-practical/new-background-worker/)

## 小結

`go test -race` 是 Go 並發服務的基本安全網，但它只檢查測試執行到的 data race。你仍然需要設計清楚的 state owner、lock boundary、channel ownership 與行為測試。Race-free 不是正確性的全部；它只是可靠性的第一層檢查。
