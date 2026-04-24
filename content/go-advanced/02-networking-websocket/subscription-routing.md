---
title: "2.3 訂閱模型與訊息路由"
date: 2026-04-22
description: "將 client action 對應到主題訂閱狀態"
weight: 3
---

訂閱模型的核心目標是把 client action 轉成明確的連線狀態與回應訊息。[WebSocket](/backend/knowledge-cards/websocket/) 是長連線，單次 action 失敗通常不應直接關閉連線；router 應把錯誤轉成可理解的 server message。

## 本章目標

學完本章後，你將能夠：

1. 設計穩定的 client action envelope
2. 把 router、handler、usecase 與 client state 分開
3. 用訂閱集合表達 client 想收到的 [topic](/backend/knowledge-cards/topic/)
4. 在 broadcast 前檢查訂閱狀態
5. 測試 action routing、payload validation 與 error response

---

## 【觀察】client message 很容易變成臨時協定

WebSocket action 的核心風險是前後端快速加功能時，訊息格式變成一堆臨時欄位。若 action 名稱依賴按鈕、畫面或短期 UI 狀態，server 很快會累積難以維護的分支。

不穩定的訊息格式：

```json
{
  "button": "watch",
  "tab": "jobs",
  "id": "topic_1"
}
```

這種訊息描述 UI 發生什麼，不是描述 client 想對服務做什麼。服務端應該接收穩定 action，例如 `subscribe_topic`、`unsubscribe_topic`、`list_subscriptions`。

## 【判讀】action 是 client intent

Client action 的核心語意是「client 想做什麼」。它不是 domain event，因為它還沒被驗證、授權或套用規則。Domain event 表示已經發生的事，action 表示請求。

```go
type ClientAction string

const (
    ActionSubscribeTopic   ClientAction = "subscribe_topic"
    ActionUnsubscribeTopic ClientAction = "unsubscribe_topic"
    ActionListTopics       ClientAction = "list_topics"
)

type ClientMessage struct {
    Action ClientAction    `json:"action"`
    Data   json.RawMessage `json:"data,omitempty"`
}
```

外層 envelope 穩定，內層 `Data` 依 action 解析。這讓 read pump 可以先解析 envelope，router 再依 action 決定 payload 型別。

## 【策略】router 負責分派，不擁有全部規則

Router 的核心責任是把 action 分派到對應 handler。它應該知道有哪些 action，但不應把訂閱規則、權限檢查、資料查詢全部塞在一個巨大 switch 裡。

```go
type Router struct {
    subscriptions *SubscriptionService
}

func (r Router) Route(ctx context.Context, client *Client, message ClientMessage) error {
    switch message.Action {
    case ActionSubscribeTopic:
        return r.handleSubscribe(ctx, client, message.Data)
    case ActionUnsubscribeTopic:
        return r.handleUnsubscribe(ctx, client, message.Data)
    case ActionListTopics:
        return r.handleListTopics(ctx, client)
    default:
        return fmt.Errorf("unknown action: %s", message.Action)
    }
}
```

`switch` 讓支援的 action 集中可見。真正的訂閱狀態修改可以交給 `SubscriptionService` 或 client method，避免 router 變成所有規則的聚集地。

## 【執行】payload validation 在 action 邊界完成

Payload validation 的核心責任是讓內部服務只收到有效 command。訂閱 topic 至少要檢查 JSON 格式、topic 是否空白、topic 名稱是否符合規則。

```go
type SubscribeTopicRequest struct {
    Topic string `json:"topic"`
}

type SubscribeTopicCommand struct {
    ClientID string
    Topic    string
}

func (r Router) handleSubscribe(ctx context.Context, client *Client, raw json.RawMessage) error {
    var req SubscribeTopicRequest
    if err := json.Unmarshal(raw, &req); err != nil {
        return fmt.Errorf("decode subscribe request: %w", err)
    }

    topic := strings.TrimSpace(req.Topic)
    if topic == "" {
        return fmt.Errorf("topic is required")
    }

    cmd := SubscribeTopicCommand{
        ClientID: client.ID(),
        Topic:    topic,
    }

    return r.subscriptions.Subscribe(ctx, client, cmd)
}
```

Request struct 是 wire format，command 是內部意圖。兩者分開後，JSON 命名、驗證錯誤與內部服務規則不會混在同一個型別。

## 【執行】訂閱集合是連線狀態

訂閱集合的核心語意是「這個 client 目前想收到哪些 topic」。它可以放在 client 上，也可以由 hub 集中保存；重點是 owner 要明確。

Client owner 版本：

```go
type Client struct {
    id string

    mu            sync.RWMutex
    subscriptions map[string]struct{}
}

func (c *Client) Subscribe(topic string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.subscriptions[topic] = struct{}{}
}

func (c *Client) Unsubscribe(topic string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    delete(c.subscriptions, topic)
}

func (c *Client) IsSubscribed(topic string) bool {
    c.mu.RLock()
    defer c.mu.RUnlock()
    _, ok := c.subscriptions[topic]
    return ok
}
```

`map[string]struct{}` 是 Go 常見 set 表示法。若 read pump 修改訂閱，hub broadcast 讀取訂閱，就需要 lock 或把所有訂閱操作集中到 hub event loop。

## 【策略】訂閱狀態也需要 copy boundary

訂閱列表的核心風險是直接回傳 map 會暴露內部狀態。若需要列出目前訂閱，應回傳 slice 或 map copy。

```go
func (c *Client) Subscriptions() []string {
    c.mu.RLock()
    defer c.mu.RUnlock()

    topics := make([]string, 0, len(c.subscriptions))
    for topic := range c.subscriptions {
        topics = append(topics, topic)
    }
    sort.Strings(topics)
    return topics
}
```

回傳 sorted slice 讓測試更穩定，也避免呼叫端修改內部 map。排序不是業務必要條件，但對 API response 與測試可讀性有幫助。

## 【執行】成功與失敗都應回 server message

WebSocket action 的核心互動模式是 request-like，但連線不會因單次 action 結束。成功或失敗都應回一筆 server message，讓 client 能更新 UI 或顯示錯誤。

```go
type ServerMessage struct {
    Type  string `json:"type"`
    Topic string `json:"topic,omitempty"`
    Error string `json:"error,omitempty"`
}

func (s *SubscriptionService) Subscribe(ctx context.Context, client *Client, cmd SubscribeTopicCommand) error {
    client.Subscribe(cmd.Topic)
    ok := client.TrySend(ServerMessage{
        Type:  "topic_subscribed",
        Topic: cmd.Topic,
    })
    if !ok {
        return ErrClientQueueFull
    }
    return nil
}
```

若 action 失敗，read pump 或 router wrapper 可以把錯誤轉成 `ServerMessage{Type: "error"}`。不要只寫 server [log](/backend/knowledge-cards/log/)，因為 client 需要知道該 action 沒有成功。

## 【執行】broadcast 前檢查訂閱

Broadcast 的核心規則是 [producer](/backend/knowledge-cards/producer/) 只產生 topic 與 message，hub 決定哪些 client 應該收到。訂閱邏輯不應散落在每個 producer 裡。

```go
func (h *Hub) Broadcast(topic string, message ServerMessage) {
    for client := range h.clients {
        if !client.IsSubscribed(topic) {
            continue
        }

        if ok := client.TrySend(message); !ok {
            h.unregister <- client
        }
    }
}
```

這段程式先檢查訂閱，再嘗試送出。若 client 的 send [buffer](/backend/knowledge-cards/buffer/) 滿了，hub 可以 unregister 或採用其他慢 client 策略；下一章會專門處理。

## 【測試】router test 不需要真實 WebSocket

Router 的測試核心是 action 到行為的對應。它不需要真實 WebSocket connection，只需要 fake client 或檢查 client state。

```go
func TestSubscribeActionAddsTopic(t *testing.T) {
    client := NewTestClient("client_1")
    router := Router{subscriptions: NewSubscriptionService()}

    data := json.RawMessage(`{"topic":"alerts"}`)
    err := router.Route(context.Background(), client, ClientMessage{
        Action: ActionSubscribeTopic,
        Data:   data,
    })
    if err != nil {
        t.Fatalf("route subscribe: %v", err)
    }

    if !client.IsSubscribed("alerts") {
        t.Fatalf("client should subscribe to alerts")
    }
}
```

Payload validation 也應獨立測：

```go
func TestSubscribeActionRequiresTopic(t *testing.T) {
    client := NewTestClient("client_1")
    router := Router{subscriptions: NewSubscriptionService()}

    err := router.Route(context.Background(), client, ClientMessage{
        Action: ActionSubscribeTopic,
        Data:   json.RawMessage(`{"topic":" "}`),
    })
    if err == nil {
        t.Fatalf("empty topic should return error")
    }
}
```

WebSocket integration test 留給「真實 client/server 互動」；router 單元測試先確保協定語意正確。

## 本章不處理

本章先處理 action envelope 到 subscription 的路由與 ownership；授權、presence 與跨節點同步，會在下列章節延伸：

- [Go 進階：跨節點 WebSocket、presence 與重連協定](/go-advanced/07-distributed-operations/cross-node-websocket/)

## 和 Go 教材的關係

這一章承接的是 WebSocket action、event fusion 與 handler boundary；如果你要先回看語言教材，可以讀：

- [Go：如何新增一個即時訊息 action](/go/06-practical/new-websocket-action/)
- [Go：如何新增一種 domain event](/go/06-practical/new-event-type/)
- [Go：事件融合](/go-advanced/04-architecture-boundaries/event-fusion/)
- [Go：把 handler 邏輯拆成可測單元](/go/07-refactoring/handler-boundary/)
- [Backend：快取與 Redis](/backend/02-cache-redis/)
- [Backend：訊息佇列與事件傳遞](/backend/03-message-queue/)

## 小結

訂閱模型把 client action 轉成連線狀態與 server response。Action 是 client intent，不是 domain event；router 負責分派，payload validation 在邊界完成，訂閱集合要有明確 owner，broadcast 由 hub 統一檢查訂閱。這樣新增 action 或 topic 時，修改範圍會清楚且可測。
