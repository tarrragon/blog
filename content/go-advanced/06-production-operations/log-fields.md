---
title: "6.3 結構化日誌欄位設計"
date: 2026-04-22
description: "讓 log 可 grep、可聚合、可追蹤"
weight: 3
---

結構化日誌欄位的核心目標是讓 log 可查詢、可聚合、可追蹤。Message 給人讀，欄位給系統查；重要資訊應放在穩定欄位，不應只藏在自由文字裡。

## 本章目標

學完本章後，你將能夠：

1. 設計穩定 log schema
2. 用 `layer`、`request_id`、`event_type`、`reason` 支援查詢
3. 區分 message 與 structured fields 的責任
4. 避免重複記錄同一個錯誤
5. 避免把敏感資料寫進 log

---

## 【觀察】自由文字 log 很難查詢

Log 設計的核心問題是事故發生時需要快速查詢。若所有資訊都在 message 裡，查詢只能依賴模糊字串。

不穩定 log：

```go
logger.Info("event accepted for user 123 request abc")
```

這行給人看可以，但系統很難穩定查 `request_id=abc` 或 `user_id=123`。不同工程師改字句後，查詢就可能失效。

結構化 log：

```go
logger.Info("event accepted",
    "layer", "http",
    "request_id", requestID,
    "user_id", userID,
    "event_type", event.Type,
)
```

Message 描述發生什麼事，欄位提供可查詢資料。這是 log schema 的基本分工。

## 【判讀】log schema 是查詢合約

Log schema 的核心規則是欄位名稱與值集合要穩定。`request_id`、`requestID`、`rid` 混用會讓查詢與儀表板變得困難。

常用欄位：

| 欄位         | 用途                     |
| ------------ | ------------------------ |
| `layer`      | 問題發生在哪個系統層     |
| `request_id` | 串起單次 HTTP request    |
| `event_id`   | 串起事件處理流程         |
| `event_type` | 聚合某類 domain event    |
| `client_id`  | 查 WebSocket client 行為 |
| `topic`      | 查訂閱或推送範圍         |
| `reason`     | 聚合失敗原因             |
| `error`      | 保存錯誤文字             |

欄位不需要很多，但要一致。穩定欄位能讓除錯從「讀一堆文字」變成「查一組條件」。

## 【執行】layer 表示發生位置

`layer` 的核心用途是標示 log 來自哪個系統層，協助工程師快速縮小問題範圍。

```go
logger.Warn("queue full",
    "layer", "worker",
    "queue", "events",
    "reason", "buffer_full",
)
```

常見 layer：

- `http`
- `websocket`
- `worker`
- `repository`
- `runtime`
- `diagnostics`

名稱不需要多，但應穩定。若 `worker`、`background`、`job_runner` 混用，查詢就會變麻煩。

## 【策略】correlation ID 串起一次流程

Correlation ID 的核心目標是把同一次請求或同一個事件流串起來。HTTP request 常用 `request_id`，背景事件可以用 `event_id` 或 `trace_id`。

```go
func WithRequestLog(r *http.Request, logger *slog.Logger) *slog.Logger {
    requestID := r.Header.Get("X-Request-ID")
    if requestID == "" {
        requestID = uuid.NewString()
    }

    return logger.With("request_id", requestID)
}
```

後續 handler、service、repository 都使用帶有 `request_id` 的 logger。查詢單次流程時，不需要靠時間範圍猜哪些 log 相關。

Correlation ID 不應包含敏感資料。它是追蹤用識別碼，不是使用者資料容器。

## 【執行】reason 欄位讓失敗可統計

`reason` 的核心用途是把錯誤原因變成可聚合分類。Message 可以給人讀，reason 給查詢與統計使用。

```go
logger.Warn("reject event",
    "layer", "http",
    "reason", "invalid_payload",
    "event_type", event.Type,
)
```

穩定 reason 可以回答「最近一小時最多的拒絕原因是什麼」。如果原因只寫在 message 中，查詢會依賴模糊字串比對。

Reason 值應像 enum 一樣維持小集合，例如：

- `invalid_payload`
- `queue_full`
- `permission_denied`
- `timeout`
- `client_disconnected`
- `dependency_unavailable`

`reason` 應維持小集合分類，完整錯誤應放在 `error` 欄位。這樣監控可以穩定聚合原因，工程師仍能從錯誤欄位取得診斷細節。

## 【判讀】錯誤只在負責處理的邊界記一次

錯誤日誌的核心風險是同一個錯誤被每一層都記一次。這會放大噪音，讓事故時很難看出真正的失敗點。

反模式：

```go
logger.Error("repository failed", "error", err)
return fmt.Errorf("save notification: %w", err)
```

上層又記一次：

```go
logger.Error("request failed", "error", err)
```

較清楚的做法是底層 wrap error，上層在決定 response 或重試策略的邊界記錄一次：

```go
if err := service.Create(ctx, cmd); err != nil {
    logger.Warn("create notification failed",
        "layer", "http",
        "reason", reasonOf(err),
        "error", err,
    )
    writeError(w, err)
    return
}
```

底層若有必要補充脈絡，優先透過 error wrapping 或 structured error，而不是每層都 `Error` log。

## 【策略】敏感資料不進 log

Log 欄位設計的核心安全邊界是只記錄診斷必要資料。token、密碼、完整 cookie、完整個資與機密 payload 都屬於應排除資料；結構化 log 很容易被集中保存與搜尋，敏感資料一旦進入 log，清理成本很高。

可以記錄：

```go
logger.Info("user login",
    "user_id", user.ID,
)
```

應排除：

```go
logger.Info("user login",
    "password", password,
    "token", token,
)
```

若需要診斷 payload，可記錄長度、hash、欄位是否存在，而不是完整內容。

```go
logger.Debug("payload received",
    "payload_bytes", len(body),
    "payload_sha256", checksum(body),
)
```

所有會被收集或保存的 log 都應遵守同一套資料保護規則。Debug log 也會進入檔案、集中式 log 或診斷封包，因此不能把它當成敏感資料的例外通道。

## 【測試】log 欄位可以用 handler 驗證

Log schema 的測試核心是確認重要欄位存在，避免未來重構時消失。

```go
func TestLogAttrsForEvent(t *testing.T) {
    event := DomainEvent{
        ID:        "evt_1",
        Type:      "notification.created",
        SubjectID: "notification_1",
    }

    attrs := LogAttrsForEvent(event)

    if !hasAttr(attrs, "event_id", "evt_1") {
        t.Fatalf("event_id attr missing")
    }
    if !hasAttr(attrs, "event_type", "notification.created") {
        t.Fatalf("event_type attr missing")
    }
}
```

不需要測整行 log 字串。測穩定欄位即可，message 文字可以保留一定調整空間。

## 本章不處理

本章不討論完整 log aggregation 平台、OpenTelemetry 欄位標準或隱私法規細節。這些會影響部署與治理；本章先建立 Go 服務內部的 structured log schema 思路。後續可接 [Observability pipeline、metrics 與 tracing](../07-distributed-operations/observability-pipeline/)。

如果你還不熟悉 `slog` 的基本 API，先回到 [Go 入門：log/slog](../../go/03-stdlib/slog/)；如果你正在判斷資料應放進 structured log、domain event log 還是 state repository，先讀 [Go 入門：如何新增結構化記錄欄位](../../go/06-practical/structured-recording/)。

## 小結

結構化日誌的價值在於穩定欄位：`layer` 定位層級，`request_id` 串起請求，`event_id` 串起事件，`event_type` 支援聚合，`reason` 支援失敗分類。Message 給人讀，欄位給系統查。好的 log schema 能讓除錯從猜測變成查詢，同時避免敏感資料外洩與錯誤重複記錄。
