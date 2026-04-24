---
title: "4.2 channel：資料傳遞與 backpressure "
date: 2026-04-22
description: "理解 channel 如何在 goroutine 之間傳遞資料並形成 backpressure "
weight: 2
---

channel 是 Go 用來在 goroutine 之間傳遞資料的同步工具。它的核心意義是建立資料流邊界：誰送出資料、誰接收資料、當接收端跟不上時送出端如何被阻擋或丟棄。

## 本章目標

學完本章後，你將能夠：

1. 建立與使用 channel
2. 看懂 channel 的方向與資料型別
3. 理解 buffered channel 的 [backpressure](../../../backend/knowledge-cards/backpressure/) 意義
4. 分辨 blocking send 與 non-blocking send
5. 用 channel 畫出資料流

---

## 【觀察】channel 連接送出端與接收端

channel 的核心規則是：送出端用 `<-` 把值放入 channel，接收端用 `<-` 從 channel 取出值。以下範例建立一個傳遞 `string` 的 channel：

```go
messages := make(chan string)

go func() {
    messages <- "hello"
}()

msg := <-messages
fmt.Println(msg)
```

`make(chan string)` 建立只能傳 `string` 的 channel。`messages <- "hello"` 是送出，`msg := <-messages` 是接收。

## 【判讀】channel 是同步點，不只是佇列

unbuffered channel 的核心規則是：送出和接收必須同時準備好，資料才會通過。這表示 channel 也是同步點。

```go
ch := make(chan int)

go func() {
    ch <- 1 // 等到有人接收才會繼續
}()

value := <-ch
fmt.Println(value)
```

buffered channel 的核心規則是：[buffer](../../../backend/knowledge-cards/buffer/) 未滿時送出不會阻塞，buffer 滿時送出會阻塞。

```go
jobs := make(chan Job, 10)
jobs <- Job{ID: "1"}
```

buffer 大小不是隨便的數字。它代表系統允許累積多少尚未處理的工作；接收端處理速度跟不上時，buffer 會逐漸填滿，最後形成 backpressure 。

## 【策略】用方向限制表達所有權

channel direction 的核心規則是：函式簽名應限制自己只需要的能力。Go 可以用 channel direction 表達函式只讀或只寫：

```go
func producer(out chan<- Job) {
    out <- Job{ID: "1"}
}

func consumer(in <-chan Job) {
    job := <-in
    handle(job)
}
```

`chan<- Job` 表示只能送出，`<-chan Job` 表示只能接收。這是 API 層的保護：[producer](../../../backend/knowledge-cards/producer/) 不能讀取 channel，[consumer](../../../backend/knowledge-cards/consumer/) 不能寫入 channel。

## 【執行】non-blocking send 的取捨

non-blocking send 的核心規則是：送不出去時立即走 [fallback](../../../backend/knowledge-cards/fallback/)，不等待接收端。它適合「寧可丟棄或記錄，也不要卡住呼叫端」的情境。

```go
select {
case jobs <- job:
    logger.Info("job queued", "id", job.ID)
default:
    logger.Warn("job queue full", "id", job.ID)
}
```

這個策略的代價是資料可能被丟棄，所以必須記錄 [log](../../../backend/knowledge-cards/log/) 或回傳明確錯誤。若資料不能丟，就不要用 default；讓送出端阻塞或回傳「系統忙碌」會更誠實。

## 關閉 channel

關閉 channel 的核心規則是：由送出端關閉，表示不會再有新資料。接收端可以用 `range` 讀到 channel 關閉：

```go
func producer(out chan<- int) {
    defer close(out)
    for i := 0; i < 3; i++ {
        out <- i
    }
}

func consumer(in <-chan int) {
    for value := range in {
        fmt.Println(value)
    }
}
```

接收端不應關閉自己沒有所有權的 channel；否則送出端可能在送資料時遇到 panic。

## 小結

channel 的重點是資料流、同步點與所有權邊界。buffer 大小、方向限制、blocking 或 non-blocking send 都是設計決策，會直接影響程式在壓力下的行為。
