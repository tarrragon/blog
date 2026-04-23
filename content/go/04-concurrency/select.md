---
title: "4.3 select：同時等待多種事件"
date: 2026-04-22
description: "用 select 建立事件迴圈"
weight: 3
---

`select` 是 Go 用來同時等待多個 channel 操作的控制結構。它的核心用途是讓一個 goroutine 同時處理資料輸入、取消訊號、timer/ticker 與 [fallback](../../backend/knowledge-cards/fallback) 行為。

## 本章目標

學完本章後，你將能夠：

1. 理解 `select` 的基本語法
2. 同時等待多個 channel
3. 用 `ctx.Done()` 停止事件迴圈
4. 用 ticker 建立定時工作
5. 理解 `default` 的 non-blocking 行為

---

## 【觀察】select 同時等待多個 channel

`select` 的核心規則是：多個 case 中哪個 channel 先 ready，就執行哪個 case。以下範例同時等待 job 和取消訊號：

```go
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case <-ctx.Done():
            return
        case job := <-jobs:
            handle(job)
        }
    }
}
```

這個 worker 不需要先固定等待 jobs，也不需要用輪詢檢查 context。`select` 會同時等待兩者。

## 【判讀】select loop 是長期 goroutine 的生命週期中心

長期 goroutine 的核心規則是：事件迴圈必須同時處理工作來源與退出訊號。只讀工作 channel 而不讀 `ctx.Done()`，goroutine 可能無法按上層要求停止。

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

`ok == false` 表示 channel 已關閉。這讓 worker 在「上層取消」和「工作來源結束」兩種情境都能退出。

## 【策略】ticker case 要有 Stop

ticker 的核心規則是：建立 ticker 後要呼叫 `Stop()`，避免不再使用時仍保留 runtime 資源。

```go
func cleanupLoop(ctx context.Context) {
    ticker := time.NewTicker(time.Minute)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            cleanup()
        }
    }
}
```

這種模式常用於定期清理、同步、掃描或報表輸出。

## 【執行】default 建立 non-blocking select

`default` 的核心規則是：沒有任何 channel ready 時，立即執行 default。這會讓 `select` 不阻塞。

```go
select {
case jobs <- job:
    return nil
default:
    return ErrQueueFull
}
```

這段程式嘗試把 job 放進 channel；如果 channel 不能立即接收，就回傳 `ErrQueueFull`。這適合保護呼叫端不要被背景佇列卡住。

不適合用 default 的情境是你其實需要等待結果：

```go
select {
case result := <-results:
    return result
default:
    return Result{} // 可能過早返回
}
```

若結果是必要的，應該等待或設定 [timeout](../../backend/knowledge-cards/timeout)，而不是直接 default。

## timeout pattern

timeout 的核心規則是：需要等待但不能無限等待時，用 `time.After` 或 context timeout。

```go
select {
case result := <-results:
    return result, nil
case <-time.After(2 * time.Second):
    return Result{}, errors.New("timeout")
}
```

在較大的系統中，通常更偏好 `context.WithTimeout`，讓 timeout 可以沿呼叫鏈傳遞。

## 小結

`select` 是 Go 並發程式的事件路由器。長期 goroutine 用它同時等待工作、取消、定時器與 fallback；`default` 代表不等待，ticker 要記得 Stop，必要結果不要用 default 過早跳出。
