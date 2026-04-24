---
title: "2.4 慢客戶端與 send buffer 管理"
date: 2026-04-22
description: "控制推送佇列與記憶體風險"
weight: 4
---

慢客戶端管理的核心問題是單一 client 的讀取速度可能低於 server 推送速度。若 send [buffer](/backend/knowledge-cards/buffer/) 沒有上限，慢 client 會把訊息堆在記憶體裡；若 hub 使用 blocking send，慢 client 會拖住所有 client。

## 本章目標

學完本章後，你將能夠：

1. 分辨慢 client 對 hub、write pump、記憶體的影響
2. 用 bounded send channel 限制單一 client 的排隊量
3. 設計 [queue](/backend/knowledge-cards/queue/) full 時的 drop、disconnect、coalesce 策略
4. 在必要時用 byte budget 管理大型 payload
5. 測試 send buffer 滿載與 client unregister 行為

---

## 【觀察】慢 client 會把局部問題變成全域問題

慢 client 的核心風險是它不只影響自己。若 hub broadcast 時對每個 client 使用 blocking send，其中一個 client 的 `send` channel 滿了，hub 就可能卡住，其他 client 也收不到訊息。

反模式：

```go
func (h *Hub) Broadcast(message ServerMessage) {
    for client := range h.clients {
        client.send <- message
    }
}
```

這段程式看起來保證送達，但實際上把整個 hub 的可用性綁在最慢的 client 上。只要一個 client 不讀，所有 broadcast 都可能停住。

## 【判讀】send channel 是每個 client 的容量邊界

Send channel 的核心責任是作為單一 client 的輸出佇列。它必須有容量上限，否則 server 會替慢 client 無限制保存訊息。

```go
const sendBufferSize = 64

type Client struct {
    id   string
    send chan ServerMessage
}

func NewClient(id string) *Client {
    return &Client{
        id:   id,
        send: make(chan ServerMessage, sendBufferSize),
    }
}
```

Buffer 的目的只是吸收短暫尖峰，不是讓 client 長期落後。若 client 長期消費速度低於推送速度，任何有限 buffer 都會滿。

## 【策略】滿載策略取決於訊息語意

慢 client 滿載的核心決策是訊息能不能遺失。不同資料類型需要不同策略。

| 訊息類型                                         | 常見策略                                                  | 理由                       |
| ------------------------------------------------ | --------------------------------------------------------- | -------------------------- |
| 即時狀態 snapshot                                | 可丟棄舊訊息或 coalesce                                   | 最新狀態比每個中間狀態重要 |
| action result                                    | 優先送達，滿載時可斷線                                    | client 需要知道操作結果    |
| 診斷 [log](/backend/knowledge-cards/log/) stream | 可取樣或丟棄                                              | 資料量大，通常不是唯一真相 |
| 金流、訂單、稽核事件                             | 不應只靠 [WebSocket](/backend/knowledge-cards/websocket/) | 需要可靠儲存或可重播來源   |

WebSocket send buffer 不應承擔資料可靠性。若訊息不能遺失，可靠性應放在資料庫、queue 或 [event log](/backend/knowledge-cards/event-log/)，WebSocket 只負責即時通知。

## 【執行】non-blocking send 保護 hub

Hub 的核心保護是 broadcast 時不被單一 client 阻塞。`TrySend` 可以讓 hub 立即知道該 client 是否已滿載。

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

Hub 可以把滿載 client 送進 unregister：

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

這種策略犧牲慢 client，保護整體服務。對即時通知服務來說，讓慢 client 重連並重新取得 snapshot，通常比讓所有 client 等它更合理。

## 【策略】drop newest、drop oldest、disconnect 是不同語意

Queue full 策略的核心差異是保留哪一筆資料，以及是否繼續維持連線。

| 策略        | 行為                  | 適用情境                                                |
| ----------- | --------------------- | ------------------------------------------------------- |
| drop newest | 新訊息不進 queue      | 舊訊息仍有價值                                          |
| drop oldest | 移除舊訊息，保留最新  | 狀態型更新                                              |
| disconnect  | 關閉 client，要求重連 | client 已明顯跟不上                                     |
| coalesce    | 合併多筆更新成一筆    | [topic](/backend/knowledge-cards/topic/) 最新狀態可覆蓋 |

Drop oldest 範例：

```go
func (c *Client) TrySendLatest(message ServerMessage) bool {
    select {
    case c.send <- message:
        return true
    default:
    }

    select {
    case <-c.send:
    default:
    }

    select {
    case c.send <- message:
        return true
    default:
        return false
    }
}
```

這段程式表示「新狀態比舊狀態重要」。它不適合 action result 或不可遺失事件，因為它會主動丟掉尚未送出的舊訊息。

## 【策略】byte budget 比 message count 更接近記憶體風險

Message count 的核心限制是每筆訊息大小不同。64 筆小訊息和 64 筆大型 JSON payload 的記憶體成本差很多；當 payload 大小差異明顯時，可以加上 byte budget。

```go
type Client struct {
    send      chan ServerMessage
    sendBytes int64
    maxBytes  int64
}

func (c *Client) TrySend(message ServerMessage) bool {
    size := int64(message.Size())
    if atomic.AddInt64(&c.sendBytes, size) > c.maxBytes {
        atomic.AddInt64(&c.sendBytes, -size)
        return false
    }

    select {
    case c.send <- message:
        return true
    default:
        atomic.AddInt64(&c.sendBytes, -size)
        return false
    }
}
```

Write pump 成功取出並寫出訊息後，必須扣回 byte budget：

```go
func (c *Client) markSent(message ServerMessage) {
    atomic.AddInt64(&c.sendBytes, -int64(message.Size()))
}
```

Byte budget 更接近記憶體風險，但也更複雜。只有在訊息大小差異大、或服務連線數高時才值得加入；小型服務先用固定 buffer 通常足夠。

## 【判讀】write pump 慢不一定是 client 的錯

慢寫入的核心原因可能在 client，也可能在 server。Client 網路慢、瀏覽器停住、行動裝置休眠會造成慢寫；server payload 太大、序列化太慢、單次寫入沒有 [deadline](/backend/knowledge-cards/deadline/) 也會造成問題。

排查方向：

- send buffer 長期接近滿載
- write deadline 錯誤增加
- 單筆 message size 過大
- broadcast 頻率超過 client 消費能力
- 某些 topic 推送量異常高

queue full 的歸因應同時檢查 client 與 server 端訊號。若所有 client 都慢，通常是 server 推送量、payload 大小或下游網路策略出問題。

## 【策略】滿載要有觀測欄位

慢 client 策略的核心要求是可觀測。若系統選擇 drop 或 disconnect，應記錄足夠欄位讓工程師知道原因。

```go
func (h *Hub) handleFullClient(client *Client, topic string) {
    metrics.Inc("websocket_client_send_full")
    h.logger.Warn("websocket client send buffer full",
        "client_id", client.ID(),
        "topic", topic,
        "send_queue_len", len(client.send),
        "send_queue_cap", cap(client.send),
    )
    h.unregister <- client
}
```

Log 用來追單次事件，metric 用來看趨勢。若滿載數量突然增加，可能是某個 topic 推送量上升，也可能是 client 版本或網路環境改變。

## 【測試】滿載測試要先填滿 buffer

慢 client 測試的核心是直接建立滿載條件。容量為 1 的 channel 加上預先填滿的資料，可以穩定製造 queue full；sleep 只是在等待排程運氣。

```go
func TestTrySendReturnsFalseWhenBufferFull(t *testing.T) {
    client := &Client{
        id:   "client_1",
        send: make(chan ServerMessage, 1),
    }
    client.send <- ServerMessage{Type: "first"}

    ok := client.TrySend(ServerMessage{Type: "second"})
    if ok {
        t.Fatalf("TrySend should return false when buffer is full")
    }
}
```

Hub unregister 行為也可以測：

```go
func TestBroadcastUnregistersFullClient(t *testing.T) {
    hub := NewHub()
    client := NewTestClient("client_1", 1)
    client.Subscribe("alerts")
    client.send <- ServerMessage{Type: "existing"}
    hub.clients[client] = struct{}{}

    hub.Broadcast("alerts", ServerMessage{Type: "new"})

    select {
    case got := <-hub.unregister:
        if got != client {
            t.Fatalf("unregister client mismatch")
        }
    default:
        t.Fatalf("full client should be unregistered")
    }
}
```

這類測試直接驗證服務策略：client 滿載時，hub 不阻塞，而是走指定降級路徑。

## 本章不處理

本章先處理單一 server 內的慢 client 與 send buffer 邊界；跨節點 [fan-out](/backend/knowledge-cards/fan-out/) 與持久化同步，會在下列章節延伸：

- [Go 進階：跨節點 WebSocket、presence 與重連協定](/go-advanced/07-distributed-operations/cross-node-websocket/)

## 和 Go 教材的關係

這一章承接的是 channel [backpressure](/backend/knowledge-cards/backpressure/) 、non-blocking send 與 rate limiting；如果你要先回看語言教材，可以讀：

- [Go：channel：資料傳遞與 backpressure ](/go/04-concurrency/channel/)
- [Go：非阻塞送出與事件丟棄策略](/go-advanced/01-concurrency-patterns/non-blocking-send/)
- [Go：rate limiting 與 backpressure ](/backend/knowledge-cards/rate-limit/)
- [Go：bounded worker pool](/backend/knowledge-cards/worker-pool/)
- [Backend：訊息佇列與事件傳遞](/backend/03-message-queue/)
- [Backend：快取與 Redis](/backend/02-cache-redis/)

## 小結

慢客戶端是 WebSocket 服務的容量控制問題。每個 client 的 send buffer 必須有上限，hub broadcast 不應被單一 client 阻塞，queue full 策略要符合訊息語意。必要時可加入 byte budget，但更重要的是明確決定 drop、disconnect、coalesce 或可靠儲存，並用 log、metric、測試讓降級行為可見。
