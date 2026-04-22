---
title: "4.1 goroutine：輕量並發工作"
date: 2026-04-22
description: "用 goroutine 啟動並發工作，並設計清楚的退出條件"
weight: 1
---

# goroutine：輕量並發工作

goroutine 是 Go 執行並發工作的基本單位。它的核心用途是讓一段函式和目前流程同時進行，但每個 goroutine 都必須有明確的退出條件，否則長時間程式會累積無法回收的背景工作。

## 本章目標

學完本章後，你將能夠：

1. 用 `go` 啟動 goroutine
2. 理解 goroutine 和一般函式呼叫的差異
3. 判斷哪些工作適合放進 goroutine
4. 為 goroutine 設計退出條件
5. 避免 goroutine leak

---

## 【觀察】go 關鍵字啟動並發工作

`go` 的核心規則是：在函式呼叫前加上 `go`，該函式會在新的 goroutine 中執行，呼叫端不會等待它完成。

```go
func say(message string) {
    fmt.Println(message)
}

func main() {
    go say("background")
    say("foreground")
}
```

這段程式啟動一個背景 goroutine 執行 `say("background")`，主 goroutine 會繼續執行 `say("foreground")`。

## 【判讀】goroutine 不是自動完成保證

goroutine 的生命週期規則是：程式不會因為你啟動了 goroutine 就自動等待它完成。`main()` 結束時，整個 process 會結束，尚未完成的 goroutine 也會停止。

因此，這段程式可能看不到背景輸出：

```go
func main() {
    go fmt.Println("background")
}
```

主程式太快結束時，背景 goroutine 可能還沒得到執行機會。

需要等待結果時，應該使用 channel、`sync.WaitGroup` 或其他同步機制。

## 【策略】goroutine 適合等待型或獨立型工作

goroutine 使用的核心規則是：只有當工作能和目前流程並發進行，且生命週期可被管理時，才啟動 goroutine。

適合 goroutine 的工作：

| 工作類型 | 原因 |
|----------|------|
| 等待 I/O | 等檔案、網路、外部程序時不阻塞主流程 |
| 背景 worker | 從 channel 收 job 並處理 |
| 定時任務 | 定期清理、同步或掃描 |
| 多個獨立請求 | 可同時發出、再收集結果 |

不適合 goroutine 的情境：

- 只是想讓程式「看起來比較快」
- 沒有任何退出條件
- 呼叫端需要結果但沒有同步機制
- 多個 goroutine 會同時修改共享資料但沒有保護

## 【執行】用 WaitGroup 等待一組工作

`sync.WaitGroup` 的核心用途是等待一組 goroutine 完成。

```go
func main() {
    var wg sync.WaitGroup

    for i := 0; i < 3; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            fmt.Println("worker", id)
        }(i)
    }

    wg.Wait()
}
```

這段程式有三個關鍵：

| 動作 | 意義 |
|------|------|
| `wg.Add(1)` | 增加一個待完成工作 |
| `defer wg.Done()` | goroutine 結束時標記完成 |
| `wg.Wait()` | 等待所有工作完成 |

`id` 作為參數傳入 goroutine，可以避免 loop 變數捕捉造成混淆。

## 長時間 goroutine 要能停止

長時間 goroutine 的核心規則是：迴圈中必須等待取消訊號或輸入 channel 關閉。

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
            handle(job)
        }
    }
}
```

這個 worker 不會無限卡住；上層取消 context 或關閉 jobs channel，它都會退出。

## 常見錯誤

### 啟動後不等待

需要結果或完成保證時，不要只寫 `go doWork()`。要用 channel 或 `WaitGroup` 等待。

### goroutine 裡吞掉錯誤

goroutine 裡的錯誤不會自動回到呼叫端。需要錯誤結果時，用 channel 傳回：

```go
errCh := make(chan error, 1)
go func() {
    errCh <- doWork()
}()

if err := <-errCh; err != nil {
    return err
}
```

### 沒有退出條件

永遠 `for {}` 的 goroutine 會造成 leak。長時間 worker 至少要監聽 context 或 channel close。

## 小結

goroutine 讓函式可以並發執行，但它不會自動解決等待、錯誤回傳或資源釋放問題。每個 goroutine 都要有明確生命週期：誰啟動、誰等待、誰取消、如何回報錯誤。
