---
title: "3.6 log/slog：結構化日誌"
date: 2026-04-22
description: "用 key-value log 設計可查詢、可過濾的程式訊號"
weight: 6
---

`log/slog` 是 Go 標準庫提供的結構化日誌 package。它的核心用途是把 log 寫成「訊息 + key-value 欄位」，讓人類能讀，也讓工具能搜尋、過濾與聚合。

## 本章目標

學完本章後，你將能夠：

1. 建立 text 或 JSON logger
2. 使用 log level 區分訊號重要性
3. 用 key-value 欄位保存可查詢資訊
4. 設計穩定的 log 欄位名稱
5. 避免把所有資訊塞進自由文字

---

## 【觀察】結構化日誌把資訊放進欄位

結構化日誌的核心規則是：穩定資訊放欄位，敘述文字只描述事件。以下範例記錄一筆 user 建立事件：

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

logger.Info(
    "user created",
    "userID", "u_1",
    "email", "alice@example.com",
)
```

JSON handler 會輸出類似：

```json
{
  "time": "2026-04-22T10:00:00Z",
  "level": "INFO",
  "msg": "user created",
  "userID": "u_1",
  "email": "alice@example.com"
}
```

這比 `fmt.Printf("user u_1 alice@example.com created")` 更容易被查詢。

## 【判讀】level 表示事件嚴重度

log level 的核心規則是：level 表示事件需要多少注意力，不表示程式碼所在位置。

| level | 適用情境                 |
| ----- | ------------------------ |
| Debug | 開發或診斷細節           |
| Info  | 正常但重要的狀態變化     |
| Warn  | 可恢復但需要注意的異常   |
| Error | 操作失敗或需要處理的錯誤 |

範例：

```go
logger.Debug("cache miss", "key", key)
logger.Info("server started", "addr", addr)
logger.Warn("queue full", "dropped", count)
logger.Error("write file failed", "path", path, "error", err)
```

`Error` log 應該包含 error 欄位，讓讀者知道失敗原因。

## 【策略】欄位名稱要穩定

log 欄位設計的核心規則是：同一個概念使用同一個欄位名稱，不要在不同地方混用別名。

| 概念       | 建議欄位    |
| ---------- | ----------- |
| 使用者 ID  | `userID`    |
| request ID | `requestID` |
| 工作 ID    | `jobID`     |
| 元件名稱   | `component` |
| 錯誤       | `error`     |

不要這樣混用：

```go
logger.Info("job queued", "id", job.ID)
logger.Info("job started", "job_id", job.ID)
logger.Info("job done", "jobID", job.ID)
```

應該統一：

```go
logger.Info("job queued", "jobID", job.ID)
logger.Info("job started", "jobID", job.ID)
logger.Info("job done", "jobID", job.ID)
```

欄位穩定後，grep、log query、dashboard 才能可靠。

## 【執行】建立帶預設欄位的 logger

預設欄位的核心規則是：每筆 log 都需要的上下文，應該掛在 logger 上，而不是每次手動重複。

```go
base := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))

logger := base.With(
    "component", "worker",
    "version", "1.0.0",
)

logger.Info("job started", "jobID", "j_1")
logger.Info("job finished", "jobID", "j_1")
```

`With` 會回傳帶有固定欄位的新 logger。這適合 component、version、requestID 這類上下文。

## 常見錯誤

### 把所有資訊塞進 msg

不佳：

```go
logger.Info("job j_1 for user u_1 started")
```

較佳：

```go
logger.Info("job started", "jobID", "j_1", "userID", "u_1")
```

第二種寫法可以直接查 `jobID=j_1` 或 `userID=u_1`。

### 欄位名稱不穩定

欄位名稱不穩定會讓查詢失效。選定 `userID` 就一路使用 `userID`，不要混用 `uid`、`user_id`、`user`。

### 忽略敏感資訊

log 會被保存與轉發。密碼、token、完整信用卡號等敏感資訊不應寫入 log。

## 小結

`slog` 的價值是把 log 變成可查詢資料。訊息描述事件，欄位保存穩定上下文；level 表示嚴重度，欄位名稱要一致，敏感資訊不要進 log。

## 延伸閱讀

本章只介紹標準庫 `log/slog` 的基本用法。服務開始有 domain event、state repository 或查詢需求時，可以接著閱讀 [如何新增結構化記錄欄位](../06-practical/structured-recording/)；進入生產操作後，再閱讀 [Go 進階：結構化日誌欄位設計](../../go-advanced/06-production-operations/log-fields/) 與 [Observability pipeline、metrics 與 tracing](../../go-advanced/07-distributed-operations/observability-pipeline/)。
