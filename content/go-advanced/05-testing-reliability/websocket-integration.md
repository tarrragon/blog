---
title: "5.2 WebSocket integration test"
date: 2026-04-22
description: "驗證 client/server 實際互動"
weight: 2
---

WebSocket integration test 的核心目標是驗證 client 與 server 透過真實連線互動後，協定行為是否正確。它比單元測試慢，但能覆蓋 HTTP upgrade、read/write pump、router、server message、push flow 與 cleanup。

## 本章目標

學完本章後，你將能夠：

1. 用 `httptest.Server` 建立真實 WebSocket 測試入口
2. 將 `http://` 測試 URL 轉成 `ws://`
3. 用 deadline 避免 read/write 永久卡住
4. 驗證 subscribe、push、error response 與 cleanup
5. 分辨 integration test 與 unit test 的責任邊界

---

## 【觀察】WebSocket 的錯誤常出現在元件交界

WebSocket 測試的核心困難是很多錯誤不在單一函式裡。Router 單元測試可能通過，但真實連線仍可能因為 upgrade path、read pump、write pump、send buffer 或 unregister 流程出錯。

Integration test 適合驗證這些交界：

- client 能否成功 dial 到 `/ws`
- server 是否接受 client action
- subscribe 後是否收到 acknowledgement
- server broadcast 是否能推到 client
- client 關閉後 hub 是否清理連線
- 錯誤 action 是否回 error message 而不是斷線

這些不是每個單元測試都該覆蓋的內容。Integration test 的價值在於證明多個元件能透過真實協定協作。

## 【判讀】integration test 補的是協作信心

Integration test 的核心責任是覆蓋協定流程，不是取代所有規則測試。Router validation、topic normalization、dedup key、state transition 應主要用單元測試；WebSocket integration test 只挑關鍵端到端流程。

建議分工：

| 測試類型         | 負責內容                                                 |
| ---------------- | -------------------------------------------------------- |
| unit test        | router、payload validation、subscription state、TrySend  |
| integration test | dial、upgrade、read/write pump、server response、cleanup |
| race test        | hub、client state、repository 的並發存取                 |

如果每個 validation case 都啟動 WebSocket server，測試會變慢且失敗定位不清楚。Integration test 應少量、關鍵、穩定。

## 【執行】用 httptest.Server 建立真實入口

WebSocket integration test 的核心起點是 `httptest.Server`。它提供真實 HTTP server，不需要手動管理 port。

```go
func TestWebSocketSubscribe(t *testing.T) {
    server := httptest.NewServer(newRouter())
    t.Cleanup(server.Close)

    wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws"

    conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
    if err != nil {
        t.Fatalf("dial websocket: %v", err)
    }
    t.Cleanup(func() {
        _ = conn.Close()
    })
}
```

`httptest.NewServer` 產生的是 `http://127.0.0.1:port`，WebSocket client 需要 `ws://127.0.0.1:port/ws`，所以常用字串轉換。

若 handler 需要 hub、router、fake repository，應在測試中明確組裝。這讓 integration test 的依賴可控。

## 【策略】測試 helper 應封裝連線樣板

Integration test 的核心樣板很多：建立 server、轉 URL、dial、設定 cleanup。可以用 helper 降低重複，但不要把協定斷言藏起來。

```go
func newTestWebSocket(t *testing.T, handler http.Handler) (*websocket.Conn, *httptest.Server) {
    t.Helper()

    server := httptest.NewServer(handler)
    t.Cleanup(server.Close)

    wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws"
    conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
    if err != nil {
        t.Fatalf("dial websocket: %v", err)
    }
    t.Cleanup(func() {
        _ = conn.Close()
    })

    return conn, server
}
```

Helper 負責重複 setup。測試本文仍應清楚寫出「送什麼 message、期待什麼 response」。

## 【執行】action 測試要檢查協定語意

Action 測試的核心流程是送 client message、讀 server message、檢查協定欄位。

```go
func TestSubscribeActionReturnsAcknowledgement(t *testing.T) {
    conn, _ := newTestWebSocket(t, newRouter())

    request := ClientMessage{
        Action: ActionSubscribeTopic,
        Data: mustJSON(t, SubscribeTopicRequest{
            Topic: "alerts",
        }),
    }

    if err := conn.WriteJSON(request); err != nil {
        t.Fatalf("write subscribe: %v", err)
    }

    response := readServerMessage(t, conn)
    if response.Type != "topic_subscribed" {
        t.Fatalf("response type = %q, want topic_subscribed", response.Type)
    }
    if response.Topic != "alerts" {
        t.Fatalf("response topic = %q, want alerts", response.Topic)
    }
}
```

這個測試檢查的是協定語意，不只是連線沒有斷。Subscribe 的成功條件是 server 明確回覆訂閱成功。

## 【執行】每次讀取前設定 deadline

WebSocket integration test 的核心風險是永久卡住。每次等待 server message 前，都應設定 read deadline。

```go
func readServerMessage(t *testing.T, conn *websocket.Conn) ServerMessage {
    t.Helper()

    if err := conn.SetReadDeadline(time.Now().Add(2 * time.Second)); err != nil {
        t.Fatalf("set read deadline: %v", err)
    }

    var response ServerMessage
    if err := conn.ReadJSON(&response); err != nil {
        t.Fatalf("read server message: %v", err)
    }
    return response
}
```

Deadline 是測試保護。若 server 沒有送出預期訊息，測試會在合理時間內失敗，而不是卡住整個測試套件。

Timeout 不應過短。CI 可能比本機慢，測試應給足合理緩衝，但仍要能快速暴露失敗。

## 【執行】推送測試要先建立可觀察觸發點

Server push 的核心測試流程是先讓 client 訂閱 topic，再從 server 端觸發 broadcast，最後讀取 client 收到的 message。

```go
func TestSubscribedClientReceivesBroadcast(t *testing.T) {
    hub := NewHub()
    go hub.Run()

    conn, _ := newTestWebSocket(t, newRouterWithHub(hub))

    writeClientMessage(t, conn, ClientMessage{
        Action: ActionSubscribeTopic,
        Data:   mustJSON(t, SubscribeTopicRequest{Topic: "alerts"}),
    })
    _ = readServerMessage(t, conn)

    hub.Broadcast("alerts", ServerMessage{
        Type:  "notification",
        Topic: "alerts",
    })

    pushed := readServerMessage(t, conn)
    if pushed.Type != "notification" {
        t.Fatalf("pushed type = %q, want notification", pushed.Type)
    }
}
```

這個測試證明 subscribe state、hub broadcast、write pump 能透過真實 connection 協作。若只想測 `Broadcast` 是否檢查 topic，應寫 hub unit test，不必走 WebSocket。

## 【策略】非同步清理用 eventually，不用固定 sleep

連線清理測試的核心問題是 cleanup 通常非同步發生。測試應等待可觀察條件，而不是固定 sleep。

```go
func eventually(t *testing.T, timeout time.Duration, condition func() bool) {
    t.Helper()

    deadline := time.Now().Add(timeout)
    for time.Now().Before(deadline) {
        if condition() {
            return
        }
        time.Sleep(10 * time.Millisecond)
    }

    t.Fatalf("condition was not met within %s", timeout)
}
```

使用方式：

```go
func TestClientIsRemovedAfterClose(t *testing.T) {
    hub := NewHub()
    conn, _ := newTestWebSocket(t, newRouterWithHub(hub))

    eventually(t, time.Second, func() bool {
        return hub.ClientCount() == 1
    })

    _ = conn.Close()

    eventually(t, time.Second, func() bool {
        return hub.ClientCount() == 0
    })
}
```

`eventually` 不是任意等待；它等待具體條件。失敗時，測試會指出 cleanup 沒發生，而不是把時間耗掉後仍然不清楚原因。

## 【判讀】error action 應測協定，不只測 log

WebSocket action 失敗的核心語意是單次 action 失敗，不一定代表連線失敗。Integration test 應確認 server 回 error message，並且連線仍可繼續使用。

```go
func TestUnknownActionReturnsErrorMessage(t *testing.T) {
    conn, _ := newTestWebSocket(t, newRouter())

    writeClientMessage(t, conn, ClientMessage{
        Action: "unknown_action",
    })

    response := readServerMessage(t, conn)
    if response.Type != "error" {
        t.Fatalf("response type = %q, want error", response.Type)
    }
}
```

若設計上 unknown action 應直接關閉連線，也應明確測出 close 行為。重點是協定行為要可驗證，不要只依賴 server log。

## 本章不處理

本章不處理瀏覽器端測試、跨節點 WebSocket fan-out 或壓力測試。Integration test 的目標是驗證單一 Go server 的協定協作；容量和跨節點行為應用其他測試層處理。後續可接 [跨節點 WebSocket、presence 與重連協定](../07-distributed-operations/cross-node-websocket/) 以及 [CI、fuzz、load test 與 chaos testing](../07-distributed-operations/reliability-pipeline/)。

## 小結

WebSocket integration test 應少量覆蓋關鍵端到端協定：dial、送 action、收 response、server push、錯誤回應與 cleanup。測試要使用真實 `httptest.Server`，每次 read 前設定 deadline，等待非同步清理時使用 `eventually`。單元測試負責大量規則，integration test 負責證明真實連線能把規則串起來。
