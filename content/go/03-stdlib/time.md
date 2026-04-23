---
title: "3.2 time：時間與 duration"
date: 2026-04-22
description: "表達時間點、時間差、timer、ticker 與 timeout"
weight: 2
---

時間處理的核心規則是：時間點使用 `time.Time`，時間長度使用 `time.Duration`。本章將說明 now、parse、format、duration、timer 與 ticker 的基本用法。

## `time.Time` 表示時間點

`time.Time` 的核心意義是一個具體時間點。它可以代表現在、某個解析出來的時間、資料庫中的時間戳，或 API 回傳的建立時間。

```go
now := time.Now()
fmt.Println(now)
```

`time.Now()` 會取得目前時間。它很方便，但也會讓測試變得不穩定；需要可測試的邏輯時，通常會把時間來源包成參數或介面。

```go
func isExpired(now time.Time, deadline time.Time) bool {
    return now.After(deadline)
}
```

這個函式不自己呼叫 `time.Now()`，而是由呼叫端傳入現在時間。測試時就能提供固定時間點，避免測試結果受執行時間影響。

## `time.Duration` 表示時間長度

`time.Duration` 的核心意義是一段時間長度，不是某個時間點。它常用於 timeout、interval、重試等待與效能測量。

```go
timeout := 5 * time.Second
interval := 200 * time.Millisecond

fmt.Println(timeout)
fmt.Println(interval)
```

`time.Second`、`time.Millisecond` 這些常數本身是 `Duration`，可以用乘法組出可讀的時間長度。這比直接寫奈秒數清楚很多。

```go
// 可讀性差：
timeout := time.Duration(5000000000)

// 可讀性好：
timeout := 5 * time.Second
```

直接寫數字會讓讀者無法立即看出單位。Go 的時間 API 以奈秒為底層單位，但程式碼應該使用明確單位表達意圖。

## 時間加減要區分時間點與長度

時間運算的核心規則是：時間點加上 duration 會得到另一個時間點，兩個時間點相減會得到 duration。

```go
start := time.Now()
deadline := start.Add(30 * time.Second)
elapsed := time.Since(start)

fmt.Println(deadline)
fmt.Println(elapsed)
```

`Add` 適合計算截止時間，`Since` 適合計算從某個時間點到現在經過多久。`time.Until(deadline)` 則可以計算距離某個未來時間還有多久。

```go
remaining := time.Until(deadline)
if remaining <= 0 {
    fmt.Println("expired")
}
```

這些 API 讓程式直接表達時間語意，而不是把時間轉成數字後自行相減。

## parse 與 format 使用 layout

Go 時間格式化的核心規則是使用固定參考時間 `2006-01-02 15:04:05` 作為 layout。layout 不是任意符號，而是用這個參考時間的各個部分代表輸出形狀。

```go
now := time.Date(2026, 4, 22, 9, 30, 0, 0, time.UTC)

fmt.Println(now.Format("2006-01-02"))
fmt.Println(now.Format("2006-01-02 15:04:05"))
```

如果你想輸出年月日，就在 layout 裡寫 `2006-01-02`；如果想輸出 24 小時制時間，就寫 `15:04:05`。這和許多語言使用 `YYYY-MM-DD` 的方式不同，是 Go 時間 API 最容易混淆的地方。

解析時間也使用同一套 layout。

```go
input := "2026-04-22 09:30:00"

createdAt, err := time.Parse("2006-01-02 15:04:05", input)
if err != nil {
    return err
}

fmt.Println(createdAt)
```

`time.Parse` 預設會以 UTC 解讀不含時區的時間。若資料代表某個本地時區，應使用 `time.ParseInLocation`。

## timer 表示一次性的未來事件

`time.Timer` 的核心用途是在一段時間後發出一次訊號。它常用於 timeout、延遲執行與 select 控制。

```go
timer := time.NewTimer(2 * time.Second)
defer timer.Stop()

select {
case <-timer.C:
    fmt.Println("timeout")
}
```

`timer.C` 是一個 channel，到時間後會收到一個時間值。若 timer 可能提前不再使用，應呼叫 `Stop` 釋放資源。

在很多簡單情境中，`time.After` 更短。

```go
select {
case <-time.After(2 * time.Second):
    fmt.Println("timeout")
}
```

`time.After` 適合一次性的簡單 timeout；在高頻迴圈或需要取消、重設的情境中，`time.NewTimer` 通常比較適合。

## ticker 表示週期性事件

`time.Ticker` 的核心用途是固定間隔發出訊號。它常用於定期清理、輪詢、健康檢查與背景工作。

```go
ticker := time.NewTicker(1 * time.Second)
defer ticker.Stop()

for i := 0; i < 3; i++ {
    <-ticker.C
    fmt.Println("tick")
}
```

`ticker.C` 每隔指定 duration 會收到一次訊號。只要不再使用 ticker，就應呼叫 `Stop`，避免背景資源持續運作。

週期性工作要有明確的退出條件。實務上常搭配 `context.Context`。

```go
func run(ctx context.Context) {
    ticker := time.NewTicker(1 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            fmt.Println("work")
        }
    }
}
```

這段程式每秒執行一次工作，直到 context 被取消。時間控制與生命週期控制分開後，程式會比較容易測試與關閉。

## 小結

Go 的時間模型分成兩個核心型別：`time.Time` 表示時間點，`time.Duration` 表示時間長度。時間格式化使用固定參考時間作為 layout，timer 用於一次性等待，ticker 用於週期性事件。

下一章會進入 `os` 與 `io`，說明檔案、輸入輸出與 streaming API 的共同抽象。
