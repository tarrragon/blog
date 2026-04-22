---
title: "4.5 高併發控制與背壓"
date: 2026-04-23
description: "用 bounded concurrency、backpressure 與 cancellation 控制 goroutine 的成長"
weight: 5
---

這一章處理的是一個比「會不會開 goroutine」更重要的問題：當系統真的進入高併發狀態時，怎麼讓工作量保持可控。Go 很容易啟動大量並發工作，但如果沒有邊界，goroutine、channel、下游連線與記憶體都會一起膨脹。

## 本章目標

學完本章後，你將能夠：

1. 理解 bounded concurrency 的用途
2. 用 semaphore 或 worker pool 限制同時工作數
3. 看懂 backpressure 為什麼能保護下游
4. 在併發流程中保留 cancellation 與 timeout
5. 辨認什麼時候該拒絕新工作

---

## 【觀察】高併發不是無限開 goroutine

goroutine 很便宜，但不是免費。當你把所有工作都直接丟進 `go func()`，真正被放大的通常不是速度，而是：

- 連線數
- 記憶體
- 排隊延遲
- 下游壓力
- 故障面積

高併發設計的第一原則不是「多」，而是「可控」。

## 【判讀】bounded concurrency 是基本保護

bounded concurrency 的核心規則是：同一時間只允許有限數量的工作進行。這可以用 worker pool、semaphore 或排隊系統達成。

```go
sem := make(chan struct{}, 16)

for _, job := range jobs {
    sem <- struct{}{}

    go func(job Job) {
        defer func() { <-sem }()
        process(job)
    }(job)
}
```

這段程式限制同時只有 16 個工作在執行。當工作量暴增時，新的工作會自然排隊，而不是把整台機器一次推爆。

## 【策略】backpressure 保護的是下游

backpressure 的核心規則是：當系統處理不過來時，不要無限累積工作。這可以表現成：

- channel 滿了就阻塞
- queue 有上限
- goroutine pool 有上限
- 佇列滿時直接拒絕請求

例如 WebSocket、event consumer 或 background worker 如果沒有背壓，輸入端一快，下游就會被放大成連鎖問題。

```go
select {
case jobs <- job:
    // accepted
default:
    return ErrQueueFull
}
```

這種寫法的重點不是丟資料，而是明確表達：系統在某些壓力下會拒絕新工作，因為保護整體健康比接住所有請求更重要。

## 【執行】cancellation 與 timeout 不能少

bounded concurrency 只控制數量，不能解決卡死工作。每個工作都應該保留取消訊號與 timeout，否則即使數量受限，資源也會被慢工作一直占著。

```go
ctx, cancel := context.WithTimeout(parent, 3*time.Second)
defer cancel()

if err := doWork(ctx, job); err != nil {
    return err
}
```

這樣可以讓每一筆工作都有自己的時間邊界，避免整體系統因單一慢點而拖垮。

## 【判讀】什麼時候應該拒絕工作

不是所有併發都值得接。當以下條件成立時，拒絕新工作通常比勉強接受更合理：

- queue 已滿
- 下游連線池耗盡
- timeout 已明顯增加
- 系統已進入明顯積壓

這時候回傳 `429`、`503` 或 domain-level rejection，往往比讓請求默默堆積更健康。

## 小結

高併發控制不是 Go 的附加題，而是 Go 在服務場景裡真正需要掌握的能力。goroutine 讓你能放大並發，但 bounded concurrency、backpressure 與 cancellation 才是讓系統能長時間穩定運行的關鍵。
