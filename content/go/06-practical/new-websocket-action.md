---
title: "6.1 如何新增一個即時訊息 action"
date: 2026-04-22
description: "修改 client message、路由與 handler"
weight: 1
---

新增即時訊息 action 的核心流程是先定義 client 意圖，再把 action 轉成 application command，而不是讓 WebSocket handler 直接修改 domain state。本章用一個簡化的 topic subscription action 示範完整路徑。

## 本章目標

學完本章後，你將能夠：

1. 用 action type 表達 client intent
2. 用 request struct 定義 JSON payload 邊界
3. 把 WebSocket message 轉成 application command
4. 設計穩定的 response 與 error 格式
5. 把 router、usecase 與 WebSocket integration test 分層測試

---

## 【觀察】action 表達 client intent

action 的核心語意是 client 想要系統做什麼。它不是 UI 按鈕名稱，也不是 handler 函式名稱，而是 client 和 server 之間的訊息合約。

例如即時通知服務可能有三種 action：

| action              | client 意圖               |
| ------------------- | ------------------------- |
| `subscribe_topic`   | 訂閱某個 topic 的即時通知 |
| `unsubscribe_topic` | 取消某個 topic 的訂閱     |
| `get_snapshot`      | 取得目前狀態快照          |

用字串常數定義 action，可以避免 handler 到處散落 magic string：

```go
const (
    ActionSubscribeTopic   = "subscribe_topic"
    ActionUnsubscribeTopic = "unsubscribe_topic"
    ActionGetSnapshot      = "get_snapshot"
)
```

action 名稱應該描述行為意圖，而不是描述傳輸細節。`subscribe_topic` 比 `ws_subscribe` 更穩定，因為未來同一個 usecase 也可能被 HTTP endpoint 或 background job 呼叫。

## 【判讀】外部訊息先進入 envelope

WebSocket message 的核心邊界是 envelope。client 傳來的 JSON 應該先被解析成一個共同外殼，再根據 action 解析 payload。

```go
type ClientMessage struct {
    ID      string          `json:"id"`
    Action  string          `json:"action"`
    Payload json.RawMessage `json:"payload"`
}
```

`ID` 是 client message ID，可用來讓 response 對應原始 request。`Action` 決定路由方向。`Payload` 使用 `json.RawMessage`，讓 router 可以先看 action，再把 payload 解成對應 struct。

例如 client 可以送出：

```json
{
  "id": "msg_1001",
  "action": "subscribe_topic",
  "payload": {
    "topic": "deployments",
    "includeHistory": true
  }
}
```

這種 envelope 設計讓新 action 可以共用同一套外層格式。新增 action 時，不需要改整個 WebSocket 讀取流程，只要新增 payload struct 與路由分支。

## 【策略】payload struct 要表達資料語意

payload struct 的核心責任是把外部 JSON 轉成明確的 Go 型別。必填欄位、可選欄位與相容性都應該在 struct 與驗證函式中清楚表達。

```go
type SubscribeTopicRequest struct {
    Topic          string `json:"topic"`
    IncludeHistory bool   `json:"includeHistory,omitempty"`
}
```

`Topic` 是必填欄位，因為沒有 topic 就無法訂閱。`IncludeHistory` 是可選欄位，零值 `false` 可以代表「不要求歷史資料」。這裡使用 `omitempty` 是在表達：輸出 response 或轉送資料時，這個欄位可以省略；它不是必填資料。

驗證規則應該靠明確函式完成，而不是散落在 router 分支中：

```go
func (r SubscribeTopicRequest) Validate() error {
    if strings.TrimSpace(r.Topic) == "" {
        return fmt.Errorf("topic is required")
    }
    return nil
}
```

外部資料進入系統後，要先完成解碼與驗證，才轉成 application command。這可以避免 usecase 同時處理 JSON 格式、欄位缺漏與業務規則。

## 【執行】router 只做解析、驗證與轉換

message router 的核心責任是把 client message 轉成 application command。router 不應直接修改 repository，也不應保存訂閱狀態；它只處理傳輸邊界。

先定義 usecase 需要的 command：

```go
type SubscribeTopicCommand struct {
    ClientID       string
    Topic          string
    IncludeHistory bool
}
```

command 不需要 JSON tag，因為它不是外部傳輸格式。它是 application layer 的輸入模型，只描述 usecase 需要的資料。

接著定義 usecase 介面：

```go
type SubscriptionUsecase interface {
    SubscribeTopic(ctx context.Context, cmd SubscribeTopicCommand) error
}
```

這個介面小而明確，只描述 router 目前需要的能力。不要一開始就建立大型 `Service` 介面，把所有 action 都塞進去。

router 可以這樣組裝：

```go
type MessageRouter struct {
    subscriptions SubscriptionUsecase
}

func NewMessageRouter(subscriptions SubscriptionUsecase) *MessageRouter {
    return &MessageRouter{subscriptions: subscriptions}
}
```

處理入口接收原始 JSON bytes，回傳可序列化的 response：

```go
func (r *MessageRouter) Handle(ctx context.Context, clientID string, data []byte) ServerMessage {
    var msg ClientMessage
    if err := json.Unmarshal(data, &msg); err != nil {
        return ErrorMessage("", "invalid_json", "message must be valid JSON")
    }

    switch msg.Action {
    case ActionSubscribeTopic:
        return r.handleSubscribeTopic(ctx, clientID, msg)
    default:
        return ErrorMessage(msg.ID, "unknown_action", "action is not supported")
    }
}
```

`Handle` 不知道 WebSocket connection 怎麼讀寫，也不處理網路錯誤。這讓 router 可以被普通單元測試覆蓋。

`subscribe_topic` 的分支負責 payload 解碼、驗證與 command 建立：

```go
func (r *MessageRouter) handleSubscribeTopic(ctx context.Context, clientID string, msg ClientMessage) ServerMessage {
    var req SubscribeTopicRequest
    if err := json.Unmarshal(msg.Payload, &req); err != nil {
        return ErrorMessage(msg.ID, "invalid_payload", "payload must match subscribe_topic schema")
    }

    if err := req.Validate(); err != nil {
        return ErrorMessage(msg.ID, "invalid_payload", err.Error())
    }

    cmd := SubscribeTopicCommand{
        ClientID:       clientID,
        Topic:          req.Topic,
        IncludeHistory: req.IncludeHistory,
    }

    if err := r.subscriptions.SubscribeTopic(ctx, cmd); err != nil {
        return ErrorMessage(msg.ID, "subscribe_failed", "topic subscription failed")
    }

    return OKMessage(msg.ID, map[string]string{
        "topic": req.Topic,
    })
}
```

這段程式保留了清楚的轉換路徑：JSON message -> request struct -> command -> usecase。每一層只處理自己的責任。

## 【判讀】response 也需要穩定格式

response 格式的核心目標是讓 client 能穩定判斷一個 action 的結果。成功、輸入錯誤與不支援 action 都應該使用同一個外層格式。

```go
type ServerMessage struct {
    ReplyTo string `json:"replyTo,omitempty"`
    OK      bool   `json:"ok"`
    Code    string `json:"code,omitempty"`
    Message string `json:"message,omitempty"`
    Data    any    `json:"data,omitempty"`
}
```

成功 response 可以用 helper 建立：

```go
func OKMessage(replyTo string, data any) ServerMessage {
    return ServerMessage{
        ReplyTo: replyTo,
        OK:      true,
        Data:    data,
    }
}
```

錯誤 response 也應該用 helper 建立：

```go
func ErrorMessage(replyTo string, code string, message string) ServerMessage {
    return ServerMessage{
        ReplyTo: replyTo,
        OK:      false,
        Code:    code,
        Message: message,
    }
}
```

WebSocket action 失敗不一定要關閉連線。JSON 格式錯誤、未知 action 或 payload 驗證失敗，通常可以回一筆 error message，讓 client 修正下一次請求；只有協定嚴重錯誤、授權失效或連線狀態不可恢復時，才考慮關閉連線。

## 【策略】WebSocket handler 不應承載所有邏輯

WebSocket handler 的核心責任是 connection I/O。它可以讀 message、呼叫 router、寫 response，但不應該直接知道每種 action 的業務規則。

簡化後的連線處理可以像這樣：

```go
func handleClientMessage(ctx context.Context, router *MessageRouter, clientID string, data []byte) []byte {
    resp := router.Handle(ctx, clientID, data)

    encoded, err := json.Marshal(resp)
    if err != nil {
        fallback := ErrorMessage("", "encode_failed", "response could not be encoded")
        encoded, _ = json.Marshal(fallback)
    }

    return encoded
}
```

真實 WebSocket server 會有 read loop、write loop、heartbeat 與 slow client 處理。這些都屬於連線生命週期，不應和 action routing 混在一起。

## 【執行】router 測試先覆蓋協定行為

router 測試的核心目標是確認 message 進入後會產生正確 command 與 response。這類測試不需要啟動真實 WebSocket server。

先建立 fake usecase：

```go
type fakeSubscriptionUsecase struct {
    got SubscribeTopicCommand
    err error
}

func (f *fakeSubscriptionUsecase) SubscribeTopic(ctx context.Context, cmd SubscribeTopicCommand) error {
    if f.err != nil {
        return f.err
    }
    f.got = cmd
    return nil
}
```

成功案例測試可以檢查 command 是否正確：

```go
func TestMessageRouterSubscribeTopic(t *testing.T) {
    fake := &fakeSubscriptionUsecase{}
    router := NewMessageRouter(fake)

    data := []byte(`{
        "id": "msg_1",
        "action": "subscribe_topic",
        "payload": {
            "topic": "deployments",
            "includeHistory": true
        }
    }`)

    resp := router.Handle(context.Background(), "client_1", data)

    if !resp.OK {
        t.Fatalf("response OK = false, want true")
    }
    if fake.got.ClientID != "client_1" {
        t.Fatalf("client ID = %q, want %q", fake.got.ClientID, "client_1")
    }
    if fake.got.Topic != "deployments" {
        t.Fatalf("topic = %q, want %q", fake.got.Topic, "deployments")
    }
    if !fake.got.IncludeHistory {
        t.Fatalf("include history = false, want true")
    }
}
```

輸入錯誤案例應該測 response code，而不是只看錯誤文案：

```go
func TestMessageRouterUnknownAction(t *testing.T) {
    router := NewMessageRouter(&fakeSubscriptionUsecase{})

    resp := router.Handle(context.Background(), "client_1", []byte(`{
        "id": "msg_1",
        "action": "missing_action",
        "payload": {}
    }`))

    if resp.OK {
        t.Fatalf("response OK = true, want false")
    }
    if resp.Code != "unknown_action" {
        t.Fatalf("code = %q, want %q", resp.Code, "unknown_action")
    }
}
```

這些測試保護的是 action 協定。未來 WebSocket library、connection manager 或 repository 改變時，router 行為仍然能被快速驗證。

## 【判讀】usecase 測試要離開傳輸格式

usecase 測試的核心目標是驗證行為規則，而不是 JSON 格式。當 router 已經把 message 轉成 command，usecase 測試就應該直接餵 command。

```go
func TestSubscriptionServiceSubscribeTopic(t *testing.T) {
    repo := NewInMemorySubscriptionRepository()
    service := NewSubscriptionService(repo)

    cmd := SubscribeTopicCommand{
        ClientID:       "client_1",
        Topic:          "deployments",
        IncludeHistory: true,
    }

    if err := service.SubscribeTopic(context.Background(), cmd); err != nil {
        t.Fatalf("subscribe topic: %v", err)
    }

    if !repo.IsSubscribed("client_1", "deployments") {
        t.Fatalf("client should be subscribed")
    }
}
```

這裡不需要出現 JSON、WebSocket 或 `ClientMessage`。usecase 只關心訂閱規則與 repository 狀態。

## 實作檢查清單

新增 action 時，可以依序檢查：

1. action 名稱是否描述 client intent
2. 是否有獨立 request struct
3. 必填欄位是否有驗證
4. router 是否只做解析、驗證與 command 轉換
5. usecase 是否不依賴 WebSocket 型別
6. response 是否有穩定 `ok`、`code`、`message` 格式
7. 錯誤 action 是否回 error message，而不是直接關閉連線
8. router 測試是否覆蓋成功、未知 action、invalid JSON、invalid payload
9. usecase 測試是否直接使用 command

## 常見錯誤

### 錯誤一：handler 直接修改狀態

handler 直接改 map、slice 或 repository 會讓傳輸協定和業務規則綁死。後續若要新增 HTTP API、CLI 或背景工作呼叫同一行為，就會複製一套邏輯。

### 錯誤二：payload 使用 `map[string]any` 傳到底

`map[string]any` 適合短暫承接未知 JSON，不適合傳進 usecase。usecase 應該接收明確 command，讓欄位、型別與驗證規則可讀可測。

### 錯誤三：把 action 失敗等同連線失敗

單一 action payload 錯誤不代表 WebSocket 連線壞掉。多數 client input error 應該用 error response 表達，避免 client 因小錯誤被斷線。

### 錯誤四：一開始建立巨大 router 介面

router 依賴的 interface 應該由當下需要的 usecase 定義。過早建立大型 service interface，會讓每個測試都被迫實作不相關方法。

## 本章不處理

本章先處理單一 server 內的 action routing 與 response contract；完整 WebSocket lifecycle 與跨節點推送，會在下列章節再往外延伸：

- [Go 進階：WebSocket 服務架構](../../go-advanced/02-networking-websocket/)
- [Go 進階：跨節點 WebSocket、presence 與重連協定](../../go-advanced/07-distributed-operations/cross-node-websocket/)

## 和 Go 教材的關係

這一章承接的是 action、command 與 handler 邊界；如果你要先回看語言教材，可以讀：

- [Go：用 interface 隔離外部依賴](../../go/07-refactoring/interface-boundary/)
- [Go：把 handler 邏輯拆成可測單元](../../go/07-refactoring/handler-boundary/)
- [Go：如何新增背景工作流程](../../go/06-practical/new-background-worker/)
- [Go：如何新增一種 domain event](../../go/06-practical/new-event-type/)

## 小結

新增即時訊息 action 的重點是建立清楚的資料路徑：client message 先進入 envelope，再根據 action 解析 payload，接著轉成 application command，最後由 usecase 處理行為規則。WebSocket handler 負責連線 I/O，router 負責協定轉換，usecase 負責行為；這三層分清楚後，新增 action 才會可測、可改，也不會把服務推向難以維護的大型 handler。
