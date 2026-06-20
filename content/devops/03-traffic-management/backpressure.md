---
title: "背壓機制"
date: 2026-06-20
description: "下游處理慢時上游怎麼減速 — 有限 buffer + 回壓訊號的設計、和 rate limit 的區別"
weight: 1
tags: ["devops", "traffic-management", "backpressure", "buffer", "429"]
---

背壓是一種被動的流量控制機制 — 當下游（處理端）的速度跟不上上游（請求端）時，下游透過訊號讓上游知道「慢一點」。背壓不拒絕請求，而是讓請求的發送者自己決定要等待、重試還是放棄。

## 背壓 vs Rate Limit

背壓和 rate limit 都是流量控制，但觸發邏輯不同：

| 維度       | 背壓                                                 | Rate Limit                          |
| ---------- | ---------------------------------------------------- | ----------------------------------- |
| 觸發條件   | 下游實際變慢了（buffer 滿）                          | 請求速率超過預設上限                |
| 性質       | 被動（根據實際負載）                                 | 主動（根據預設規則）                |
| 訊號       | HTTP 429 + Retry-After / TCP 窗口縮小 / channel 阻塞 | HTTP 429 + 固定的 rate limit header |
| 發送者行為 | 根據 Retry-After 動態調整                            | 等待限速窗口重設                    |

背壓在系統真的撐不住時才觸發，rate limit 在到達預設上限時就觸發（即使系統還有餘裕）。兩者互補：rate limit 防止單一來源打爆系統，背壓防止所有來源加起來打爆系統。

## 實作模式

### 有限 buffer + 回壓訊號

最常見的背壓實作是在處理管線中加一個有限容量的 buffer。Buffer 滿了代表下游處理不完，這時對新請求回傳「忙碌」訊號。

在 Go 的 HTTP server 中，buffer 可以是一個有限容量的 channel：

```go
var ingestCh = make(chan Event, 10000) // 有限 buffer

func handleIngest(w http.ResponseWriter, r *http.Request) {
    event := parseEvent(r)
    select {
    case ingestCh <- event:
        w.WriteHeader(http.StatusAccepted) // 202
    default:
        w.Header().Set("Retry-After", "5")
        w.WriteHeader(http.StatusTooManyRequests) // 429
    }
}
```

Buffer 容量的選擇取決於下游的處理速度和可接受的記憶體用量。每個 event 約 1KB 時，10000 容量的 buffer 佔 ~10MB — 對多數服務來說可以接受。

### HTTP 429 + Retry-After

HTTP 429 Too Many Requests 是標準的回壓訊號。`Retry-After` header 告訴 client 多少秒後重試。

`Retry-After` 的值可以是固定的（如 5 秒），也可以根據 buffer 的填充程度動態計算 — buffer 越滿、Retry-After 越長。

### TCP 層的背壓

TCP 協議本身有背壓機制 — 接收端的 receive window 縮小時，發送端自動減速。但 HTTP 層的背壓比 TCP 層更精確，因為 HTTP 可以回傳語意化的狀態碼和 header，client 可以根據語意做出更智慧的回應（如優先重試 error 事件、放棄 event 事件）。

## 監控系統的應用

監控系統的 [collector](/monitoring/04-collector/) 是背壓的典型場景：多個 SDK 同時 flush 事件到 collector，collector 的寫入速度（SQLite / PostgreSQL）是瓶頸。

背壓鏈路：SDK flush → collector HTTP endpoint → 寫入 channel（有限容量）→ 寫入 goroutine → storage。Channel 滿時回 429，SDK 的離線 buffer 機制接手 — 事件暫存本地，等 collector 恢復後補發。

這個設計讓 collector 在高峰時不崩潰（有限 buffer 控制記憶體）、SDK 端不丟事件（離線 buffer 暫存）。代價是事件的到達有延遲（Retry-After 時間 + 補發時間）。

## 下一步路由

- 主動的流量限制 → [Rate Limiting](/devops/03-traffic-management/rate-limiting/)
- 依賴服務失敗時的防護 → [熔斷器](/devops/03-traffic-management/circuit-breaker/)
- 突發流量時的組合策略 → [模組七 突發流量](/devops/07-burst-traffic/)
