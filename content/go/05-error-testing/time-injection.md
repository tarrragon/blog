---
title: "5.5 時間注入與 deterministic test"
date: 2026-04-22
description: "用 time provider 避免測試依賴真實時間"
weight: 5
---

時間注入的核心目標是讓測試可以控制「現在時間」。只要函式內部直接呼叫 `time.Now()`，測試結果就可能受執行時間影響；把時間來源改成參數或小介面後，測試就能重現固定情境。

## 真實時間會讓測試不穩定

測試不穩定的核心原因是輸入不完全由測試控制。時間是最常見的隱性輸入，因為 `time.Now()` 每次呼叫都會得到不同結果。

```go
func IsExpired(deadline time.Time) bool {
    return time.Now().After(deadline)
}
```

這個函式看起來只有一個參數，但實際上還依賴目前時間。測試如果用 `time.Now().Add(...)` 組 deadline，可能因為執行延遲、時區或邊界條件而變得脆弱。

更好的做法是把現在時間傳進去。

```go
func IsExpired(now time.Time, deadline time.Time) bool {
    return now.After(deadline)
}
```

函式的所有重要輸入都變成參數後，測試可以完全控制情境。

## 參數注入適合純邏輯

參數注入的核心用途是處理單次計算。當函式只是判斷過期、計算剩餘時間或產生 timestamp，直接把 `now time.Time` 傳入通常最簡單。

```go
func Remaining(now time.Time, deadline time.Time) time.Duration {
    if now.After(deadline) {
        return 0
    }
    return deadline.Sub(now)
}
```

測試可以建立固定時間點。

```go
func TestRemaining(t *testing.T) {
    now := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
    deadline := time.Date(2026, 4, 22, 10, 5, 0, 0, time.UTC)

    got := Remaining(now, deadline)
    want := 5 * time.Minute

    if got != want {
        t.Fatalf("Remaining() = %v, want %v", got, want)
    }
}
```

這個測試不會因為今天是哪一天、測試跑得快或慢而改變結果。參數注入也讓函式更容易理解，因為時間依賴直接出現在函式簽名中。

## provider 函式適合需要多次取時間的元件

時間 provider 的核心用途是讓長生命週期元件可以取得目前時間，但測試仍能替換時間來源。最簡單的 provider 是 `func() time.Time`。

```go
type TokenGenerator struct {
    now func() time.Time
}

func NewTokenGenerator(now func() time.Time) TokenGenerator {
    return TokenGenerator{now: now}
}

func (g TokenGenerator) NewToken(userID string) Token {
    return Token{
        UserID:    userID,
        CreatedAt: g.now(),
    }
}
```

正式環境可以傳入 `time.Now`。

```go
generator := NewTokenGenerator(time.Now)
```

測試可以傳入固定時間。

```go
func TestTokenGenerator(t *testing.T) {
    fixedNow := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
    generator := NewTokenGenerator(func() time.Time {
        return fixedNow
    })

    token := generator.NewToken("user_123")
    if !token.CreatedAt.Equal(fixedNow) {
        t.Fatalf("CreatedAt = %v, want %v", token.CreatedAt, fixedNow)
    }
}
```

`func() time.Time` 比完整介面更輕量，適合只需要目前時間的情境。若元件還需要 timer、ticker 或 sleep，才需要更完整的 clock abstraction。

## duration 測試不要真的等待

測試 timeout 的核心原則是驗證邏輯，不是讓測試真的睡很久。`time.Sleep` 會讓測試慢，也會讓測試受排程影響。

```go
func RetryDelay(attempt int) time.Duration {
    if attempt <= 0 {
        return 0
    }

    return time.Duration(attempt) * 100 * time.Millisecond
}
```

這種邏輯應該直接測回傳的 duration。

```go
func TestRetryDelay(t *testing.T) {
    got := RetryDelay(3)
    want := 300 * time.Millisecond

    if got != want {
        t.Fatalf("RetryDelay() = %v, want %v", got, want)
    }
}
```

若真的要測等待行為，應把等待機制包成可替換依賴，讓測試使用 fake sleeper，而不是呼叫真實 `time.Sleep`。

```go
type Sleeper interface {
    Sleep(time.Duration)
}

type realSleeper struct{}

func (realSleeper) Sleep(d time.Duration) {
    time.Sleep(d)
}
```

這種抽象只有在等待行為本身需要測試時才值得加入。不要為了形式而把所有 `time` API 都包起來。

## 時區要明確

時間測試的核心規則是使用明確時區。測試資料若依賴本機時區，可能在不同開發機或 CI 環境得到不同結果。

```go
createdAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)
```

使用 `time.UTC` 能讓測試在不同環境保持一致。若功能本來就和特定時區有關，應用 `time.LoadLocation` 明確載入。

```go
loc, err := time.LoadLocation("Asia/Taipei")
if err != nil {
    t.Fatalf("load location: %v", err)
}

localTime := time.Date(2026, 4, 22, 18, 0, 0, 0, loc)
```

不要讓測試默默依賴 `time.Local`，除非測試目的就是驗證本機時區設定。

## 小結

時間注入讓測試從「依賴現在」改成「指定現在」。純邏輯函式可以直接傳入 `now time.Time`，長生命週期元件可以接收 `func() time.Time`，timeout 與 retry 應優先測 duration 與狀態轉移，而不是讓測試真的等待。

下一章會進入並發行為測試，說明如何驗證 goroutine、channel 與共享狀態。

## 延伸閱讀

本章處理入門測試中的時間依賴。若要測長時間 worker、ticker 排程、WebSocket cleanup 或 deadline，可以接著閱讀 [Go 進階：時間注入與狀態轉移測試](../../go-advanced/05-testing-reliability/time-control/)；若 timeout 來自部署平台或 load balancer，則閱讀 [Go 進階：Kubernetes、systemd 與 load balancer 合約](../../go-advanced/07-distributed-operations/deployment-contracts/)。
