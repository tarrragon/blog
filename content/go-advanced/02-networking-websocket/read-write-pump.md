---
title: "2.1 read pump / write pump 模式"
date: 2026-04-22
description: "分離 WebSocket 讀取、寫入與心跳"
weight: 1
---

Read pump / write pump 的核心規則是單一 [WebSocket](/backend/knowledge-cards/websocket/) 連線的讀取與寫入必須分成兩個協調的 goroutine。Read pump 擁有讀取權，write pump 擁有寫入權；其他元件不直接操作底層 connection，而是透過 channel 或 method 協作。

## 本章目標

學完本章後，你將能夠：

1. 分辨 read pump、write pump、hub 的責任
2. 避免多 goroutine 同時寫同一條 WebSocket connection
3. 用 send channel 作為 server-to-client 推送邊界
4. 設計 client unregister 與 close path
5. 用 fake router 測試 read pump 的行為邊界

---

## 【觀察】WebSocket 是一條長生命週期雙向連線

WebSocket 連線的核心特徵是 client 和 server 都可能主動送訊息。Client 可能送 subscribe、unsubscribe、ping 或 command；server 可能推送 notification、status update 或 error。

若讀寫責任不分開，程式很容易出現這種結構：

```go
func handleConnection(conn *websocket.Conn) {
    go func() {
        for msg := range serverMessages {
            conn.WriteJSON(msg)
        }
    }()

    for {
        var msg ClientMessage
        if err := conn.ReadJSON(&msg); err != nil {
            return
        }
        if msg.Action == "subscribe" {
            conn.WriteJSON(ServerMessage{Type: "subscribed"})
        }
    }
}
```

這段程式的問題是多個路徑可能同時寫 connection：背景 goroutine 寫推送，read loop 裡也直接寫回應。多個 goroutine 同時寫 WebSocket 會讓錯誤、資料交錯與 close path 變得難以推理。

## 【判讀】read pump 和 write pump 是 ownership 邊界

Read pump / write pump 的核心價值是 ownership。Read pump 是唯一讀取者，write pump 是唯一寫入者，其他元件只能透過它們的公開邊界互動。

```go
type Client struct {
    id   string
    conn *websocket.Conn
    send chan ServerMessage
}
```

`conn` 是底層連線，`send` 是 server 要推給 client 的訊息佇列。其他元件不直接呼叫 `conn.WriteJSON`，而是把 `ServerMessage` 放進 `send`。

責任表：

| 元件       | 責任                                      | 不應做的事          |
| ---------- | ----------------------------------------- | ------------------- |
| read pump  | 讀 client message、交給 router            | 直接寫 WebSocket    |
| write pump | 寫 server message、送 heartbeat、送 close | 處理 client action  |
| hub        | 註冊、取消註冊、廣播                      | 直接讀寫 connection |
| router     | 解析 action、呼叫 usecase 或更新訂閱      | 關閉底層 connection |

這個分工讓連線生命週期可以被測試與替換，而不是散在多個 goroutine 裡。

## 【策略】Client 型別要表達連線邊界

Client 型別的核心責任是封裝單一連線的狀態與輸出佇列。它不應包含整個系統的業務狀態。

```go
type Client struct {
    id   string
    conn *websocket.Conn
    send chan ServerMessage

    mu            sync.RWMutex
    subscriptions map[string]struct{}
}

func NewClient(id string, conn *websocket.Conn, sendBuffer int) *Client {
    return &Client{
        id:            id,
        conn:          conn,
        send:          make(chan ServerMessage, sendBuffer),
        subscriptions: make(map[string]struct{}),
    }
}
```

`send` 有固定容量，避免慢 client 無限制累積訊息。`subscriptions` 屬於這條連線的狀態，若會被多個 goroutine 讀寫，就需要 mutex 或集中到 hub event loop。

## 【執行】read pump 只處理 client 輸入

Read pump 的核心責任是從 connection 讀訊息、轉成 `ClientMessage`、交給 router。它不應直接操作所有業務規則。

```go
type MessageRouter interface {
    Route(ctx context.Context, client *Client, message ClientMessage) error
}

func (c *Client) readPump(ctx context.Context, hub *Hub, router MessageRouter) {
    defer func() {
        hub.unregister <- c
    }()

    for {
        var message ClientMessage
        if err := c.conn.ReadJSON(&message); err != nil {
            return
        }

        if err := router.Route(ctx, c, message); err != nil {
            c.TrySend(ServerMessage{
                Type:  "error",
                Error: err.Error(),
            })
        }
    }
}
```

Read pump 收到 read error 時退出，並通知 hub unregister。這裡不直接 close `send`，因為 `send` 的關閉責任交給 hub 統一處理。

## 【執行】write pump 是唯一寫入者

Write pump 的核心責任是把 `send` channel 裡的 server message 寫回 WebSocket。所有寫入都集中在這一個 goroutine，能避免 concurrent write。

```go
func (c *Client) writePump() {
    for {
        message, ok := <-c.send
        if !ok {
            _ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
            return
        }

        if err := c.conn.WriteJSON(message); err != nil {
            return
        }
    }
}
```

當 `send` 被關閉時，write pump 送出 close message 並退出。這表示 hub 或 connection manager 是 `send` 的 owner，write pump 是 receiver。

下一章會把 heartbeat ticker 加進 write pump。原則不變：ping 也是寫入，所以也要由 write pump 統一執行。

## 【策略】send channel 是推送邊界

`send` channel 的核心意義是把內部事件轉成 client 輸出佇列。其他元件可以嘗試送訊息，但不能直接寫 connection。

```go
func (c *Client) TrySend(message ServerMessage) bool {
    select {
    case c.send <- message:
        return true
    default:
        return false
    }
}
```

`TrySend` 使用 non-blocking send，表示 client [buffer](/backend/knowledge-cards/buffer/) 滿時不阻塞呼叫端。Hub 可以根據 `false` 決定丟棄訊息、取消註冊 client 或記錄 metric。

這個方法把 WebSocket 寫入問題轉成前一模組的 [backpressure](/backend/knowledge-cards/backpressure/) 問題：滿載時要有明確策略。

## 【執行】hub 統一管理 unregister

Unregister 的核心目標是讓清理流程只有一個責任中心。Read pump、write pump、heartbeat 都可能發現連線失效，但不要讓每個地方各自 close channel 和 connection。

```go
type Hub struct {
    clients    map[*Client]struct{}
    register   chan *Client
    unregister chan *Client
    broadcast  chan ServerMessage
}

func (h *Hub) run() {
    for {
        select {
        case client := <-h.register:
            h.clients[client] = struct{}{}

        case client := <-h.unregister:
            if _, ok := h.clients[client]; ok {
                delete(h.clients, client)
                close(client.send)
                _ = client.conn.Close()
            }
        }
    }
}
```

這個設計讓 `client.send` 只會在 hub 中被 close。其他 goroutine 只送 unregister 訊號，不直接關閉資源。

實務上要避免重複 unregister 造成 channel 重複 close。上例透過 `clients` map 判斷 client 是否仍註冊，讓 unregister 具備 idempotent 行為。

## 【判讀】read pump 結束不代表 write pump 立刻結束

Read pump 與 write pump 的核心關係是協作，不是互相任意關閉。Read pump 發現錯誤後通知 hub；hub 關閉 `send`；write pump 收到 `send` 關閉後送 close message 並退出。

流程：

```text
read error
   │
   ▼
hub.unregister <- client
   │
   ▼
hub closes client.send and conn
   │
   ▼
write pump exits
```

這條路徑讓 close ownership 清楚。若 read pump 同時 close `send`，hub 也 close `send`，就會有 double close panic。

## 【測試】router 可以用 fake 驗證 read pump 邊界

Read pump 測試的核心目標是確認 client message 會交給 router，而不是在 read pump 裡塞入業務邏輯。完整 WebSocket integration test 可以留到測試模組；這裡先用 router 的小介面讓行為可替換。

```go
type fakeRouter struct {
    messages []ClientMessage
}

func (r *fakeRouter) Route(ctx context.Context, client *Client, message ClientMessage) error {
    r.messages = append(r.messages, message)
    return nil
}
```

若測試需要真實 connection，可用 `httptest.Server` 建立 WebSocket。若只測 router 規則，應直接測 router，不必繞過 network。

Write pump 的測試通常放在 integration test，因為它依賴真實 connection 寫入行為。單元測試則可以集中在 `TrySend`、router、hub unregister 這些純邊界。

## 本章不處理

本章先處理單一連線的 read/write ownership；跨節點 hub 與 [broker](/backend/knowledge-cards/broker/) 互動，會在下列章節延伸：

- [Go 進階：跨節點 WebSocket、presence 與重連協定](/go-advanced/07-distributed-operations/cross-node-websocket/)

## 和 Go 教材的關係

這一章承接的是 goroutine ownership、channel 與 backpressure；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](/go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與 backpressure ](/go/04-concurrency/channel/)
- [Go：channel ownership 與關閉責任](/go-advanced/01-concurrency-patterns/channel-ownership/)
- [Go：如何新增一個即時訊息 action](/go/06-practical/new-websocket-action/)
- [Backend：訊息佇列與事件傳遞](/backend/03-message-queue/)

## 小結

Read pump / write pump 模式把一條 WebSocket 連線拆成清楚的 ownership：read pump 讀 client message，write pump 寫 server message，hub 統一註冊與清理。`send` channel 是推送邊界，所有 close path 應收斂到同一個 unregister 流程。這樣長連線才不會因為 concurrent write、double close 或慢 client 而失控。
