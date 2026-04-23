---
title: "2.2 heartbeat、deadline 與連線清理"
date: 2026-04-22
description: "用 ping/pong 和 deadline 偵測失效連線"
weight: 2
---

Heartbeat 的核心目標是讓失效的長連線可以被發現並清理。[Deadline](../../backend/knowledge-cards/deadline) 定義讀寫最多能停滯多久，ping/pong 在沒有業務訊息時確認連線仍然活著，unregister 流程負責釋放連線與訂閱狀態。

## 本章目標

學完本章後，你將能夠：

1. 分辨 read deadline、write deadline、ping period、pong wait 的角色
2. 在 read pump 設定 pong handler 與 read limit
3. 在 write pump 用 ticker 統一送 ping
4. 讓 heartbeat 失敗進入同一條 unregister 路徑
5. 測試 [timeout](../../backend/knowledge-cards/timeout) 設定與清理流程的邊界

---

## 【觀察】長連線可能在沒有錯誤訊息時失效

[WebSocket](../../backend/knowledge-cards/websocket) 長連線的核心風險是失效不一定立刻表現成明確錯誤。Client 可能斷網、瀏覽器休眠、代理中斷、行動網路切換，server 的 read 或 write 可能長時間卡住。

沒有 heartbeat 的服務可能出現：

- client 已離線，但 server 還保留 client。
- 訂閱狀態沒有清理，broadcast 仍嘗試推送。
- write pump 卡在慢或失效的 connection。
- goroutine、send [buffer](../../backend/knowledge-cards/buffer)、記憶體逐步累積。

Heartbeat 的目的不是讓連線永遠保持成功，而是讓失敗可以在合理時間內被觀測並進入清理流程。

## 【判讀】四個時間參數負責不同邊界

Heartbeat 設計的核心是四個時間參數的關係。它們不是任意常數，而是讀寫生命週期的合約。

```go
const (
    writeWait  = 10 * time.Second
    pongWait   = 60 * time.Second
    pingPeriod = 50 * time.Second
    maxMessage = 1 << 20
)
```

| 參數         | 角色                         | 常見關係          |
| ------------ | ---------------------------- | ----------------- |
| `writeWait`  | 單次寫入最多等待多久         | 小於 `pongWait`   |
| `pongWait`   | 多久沒讀到資料就視為失效     | 大於 `pingPeriod` |
| `pingPeriod` | 多久主動送一次 ping          | 小於 `pongWait`   |
| `maxMessage` | 單筆 client message 大小上限 | 依協定需求設定    |

`pingPeriod` 應小於 `pongWait`，讓 server 有時間送 ping 並等待 client 回 pong。`writeWait` 保護每次寫入，避免 write pump 無限卡住。

## 【執行】read pump 設定 read deadline 與 pong handler

Read deadline 的核心語意是超過指定時間沒有讀取進展，下一次 read 會失敗。Pong handler 的核心責任是每次收到 pong 時延長 read deadline。

```go
func (c *Client) configureRead() {
    c.conn.SetReadLimit(maxMessage)
    _ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
    c.conn.SetPongHandler(func(string) error {
        return c.conn.SetReadDeadline(time.Now().Add(pongWait))
    })
}
```

Read pump 啟動時先設定：

```go
func (c *Client) readPump(ctx context.Context, hub *Hub, router MessageRouter) {
    defer func() {
        hub.unregister <- c
    }()

    c.configureRead()

    for {
        var message ClientMessage
        if err := c.conn.ReadJSON(&message); err != nil {
            return
        }
        if err := router.Route(ctx, c, message); err != nil {
            c.TrySend(errorMessage(err))
        }
    }
}
```

`ReadJSON` 回錯時，read pump 不需要判斷每一種錯誤都如何清理；它只要退出並通知 hub。錯誤分類可以用於 [log](../../backend/knowledge-cards/log)，但清理路徑應一致。

## 【執行】write pump 用 ticker 送 ping

Ping 的核心規則是由 write pump 送出，因為 ping 也是 WebSocket write。讓其他 goroutine 直接送 ping 會破壞「write pump 是唯一寫入者」的原則。

```go
func (c *Client) writePump() {
    ticker := time.NewTicker(pingPeriod)
    defer ticker.Stop()

    for {
        select {
        case message, ok := <-c.send:
            _ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
            if !ok {
                _ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
                return
            }
            if err := c.conn.WriteJSON(message); err != nil {
                return
            }

        case <-ticker.C:
            _ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
            if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
                return
            }
        }
    }
}
```

每次寫入前設定 write deadline。這包含正常訊息、ping、close message；只保護部分寫入會留下卡住路徑。

## 【判讀】heartbeat 失敗走共用清理流程

Heartbeat 失敗的核心語意是連線不可用。它應該進入和 read error、write error、client disconnect 相同的 unregister 流程，而不是在 ping 錯誤處重寫一套清理。

推薦流程：

```text
read error / write error / ping error
          │
          ▼
read pump exits or write pump exits
          │
          ▼
hub unregisters client
          │
          ▼
close send, close conn, remove subscriptions
```

實作可以用 hub unregister channel、context cancellation 或 connection manager。重點不是形式，而是所有失效都收斂到同一個 owner。

## 【策略】read pump 和 write pump 都可能先失敗

連線失效的核心不確定性是 read pump 和 write pump 哪個先看到錯誤不可預測。讀不到 pong 可能讓 read pump 先退出；寫 ping 失敗可能讓 write pump 先退出。

因此 unregister 必須可重複呼叫而不出錯：

```go
func (h *Hub) unregisterClient(client *Client) {
    if _, ok := h.clients[client]; !ok {
        return
    }

    delete(h.clients, client)
    close(client.send)
    _ = client.conn.Close()
}
```

用 `clients` map 判斷 client 是否仍註冊，可以避免重複 close `send`。這是 WebSocket cleanup 最容易漏掉的細節之一。

## 【策略】heartbeat 參數要符合部署環境

Heartbeat 參數的核心取捨是偵測速度與誤判風險。偵測太快會讓短暫網路抖動造成大量斷線；偵測太慢會讓失效連線保留太久。

調整時要考慮：

- load balancer 或 proxy idle timeout
- 行動網路與瀏覽器背景分頁行為
- server 可接受的失效連線保留時間
- ping 對大量連線造成的週期性流量
- client 是否會自動重連

若基礎設施會在 60 秒 idle 後關閉連線，server 的 ping period 就不能長於這個時間。這是部署環境合約，不是單純 Go 程式碼問題。

## 【測試】把時間參數和清理邊界拆開測

Heartbeat 的測試核心是不要用真實分鐘級等待。時間參數可以測設定值關係，清理流程可以測 unregister 是否 idempotent。

```go
func TestHeartbeatDurations(t *testing.T) {
    if pingPeriod >= pongWait {
        t.Fatalf("pingPeriod must be smaller than pongWait")
    }
    if writeWait >= pongWait {
        t.Fatalf("writeWait should be smaller than pongWait")
    }
}
```

Unregister 測試：

```go
func TestUnregisterClientIsIdempotent(t *testing.T) {
    hub := NewHub()
    client := NewClient("c1", nil, 1)
    hub.clients[client] = struct{}{}

    hub.unregisterClient(client)
    hub.unregisterClient(client)

    if _, ok := hub.clients[client]; ok {
        t.Fatalf("client should be removed")
    }
}
```

真實 ping/pong 行為適合放在 integration test。單元測試先保證時間合約與 cleanup owner 不會被破壞。

## 本章不處理

本章先處理單一 WebSocket 連線的存活偵測與 cleanup；client 重連與 load balancer 參數，會在下列章節延伸：

- [Go 進階：跨節點 WebSocket、presence 與重連協定](../07-distributed-operations/cross-node-websocket/)

## 和 Go 教材的關係

這一章承接的是 read/write pump、time control 與 shutdown；如果你要先回看語言教材，可以讀：

- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：defer 與資源清理](../../go/03-stdlib/defer-cleanup/)
- [Go 進階：time control](../../go-advanced/05-testing-reliability/time-control/)
- [Go 進階：graceful shutdown 與 signal handling](../../go-advanced/06-production-operations/graceful-shutdown/)
- [Backend：部署平台與網路入口](../../backend/05-deployment-platform/)

## 小結

Heartbeat/deadline 的目的不是讓 WebSocket 永不斷線，而是讓失效連線在可預期時間內被發現並清理。Read deadline 搭配 pong handler 保護讀取端，write deadline 保護每次寫入，ping ticker 由 write pump 統一執行，所有錯誤最後都應進入同一個 unregister 流程。
