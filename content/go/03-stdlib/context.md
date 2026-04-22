---
title: "3.7 context：取消、逾時與生命週期"
date: 2026-04-22
description: "用 context 傳遞取消、逾時與請求生命週期"
weight: 7
---

`context.Context` 是 Go 用來傳遞取消訊號、逾時與 request-scoped 資訊的標準機制。它的核心用途不是保存任意資料，而是讓一串呼叫知道「這件工作是否應該停止」。

## 本章目標

學完本章後，你將能夠：

1. 理解 context 的取消語義
2. 使用 `context.WithCancel`
3. 使用 `context.WithTimeout`
4. 在 goroutine 和函式呼叫鏈中傳遞 context
5. 避免把 context 當成一般資料容器

---

## 【觀察】context 表示工作生命週期

context 的核心規則是：被取消的 context 代表這件工作不應繼續進行。長時間工作應定期檢查 `ctx.Done()`：

```go
func Run(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            doOneStep()
        }
    }
}
```

`ctx.Done()` 是一個 channel。當 context 被取消或逾時，這個 channel 會被關閉。

## 【判讀】取消是由上層傳給下層

context 的方向規則是：上層建立 context，下層接收 context；下層不應保存 context，也不應自行決定整個系統的生命週期。

```go
func main() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    go worker(ctx)

    waitForSignal()
    cancel()
}
```

`context.Background()` 是根 context。`context.WithCancel` 回傳子 context 和 cancel 函式。當 `cancel()` 被呼叫，所有使用該 context 的下層工作都會收到停止訊號。

## 【策略】逾時用 WithTimeout，主動停止用 WithCancel

context 建立方式的核心規則是：不知道何時停止但需要手動停止，用 `WithCancel`；有明確時間限制，用 `WithTimeout`。

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := fetchData(ctx); err != nil {
    return err
}
```

下層函式應該接收 context：

```go
func fetchData(ctx context.Context) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://example.com", nil)
    if err != nil {
        return err
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    return nil
}
```

當 timeout 到達，HTTP request 會被取消。

## 【執行】讓背景 goroutine 有序退出

背景 goroutine 的核心規則是：啟動時接收 context，迴圈中用 `select` 同時等待工作與取消訊號。

```go
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-jobs:
            if !ok {
                return
            }
            handleJob(job)
        }
    }
}
```

這個 worker 有兩種退出路徑：

| 退出原因         | 對應 case      |
| ---------------- | -------------- |
| 上層取消         | `<-ctx.Done()` |
| job channel 關閉 | `ok == false`  |

這比讓 goroutine 無限跑更安全，也比較容易測試。

## 常見錯誤

### 把 context 存進 struct

context 的生命週期屬於單次操作，不應長期存在 struct 裡。通常把 context 作為函式第一個參數：

```go
func (s *Service) Do(ctx context.Context, input Input) error
```

### 忘記呼叫 cancel

`WithCancel`、`WithTimeout`、`WithDeadline` 回傳的 cancel 應該被呼叫，釋放相關資源：

```go
ctx, cancel := context.WithTimeout(parent, time.Second)
defer cancel()
```

### 用 context 傳一般參數

context value 適合 request-scoped metadata，例如 request ID。一般業務參數應放在函式參數或 struct 裡。

## 小結

`context.Context` 是工作生命週期的傳遞工具。上層建立與取消 context，下層接收並尊重取消訊號；逾時用 `WithTimeout`，主動停止用 `WithCancel`，背景 goroutine 必須有清楚退出路徑。
