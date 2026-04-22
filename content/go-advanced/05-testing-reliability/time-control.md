---
title: "5.1 時間注入與狀態轉移測試"
date: 2026-04-22
description: "讓時間相關邏輯可重現"
weight: 1
---

# 時間注入與狀態轉移測試

時間控制測試的核心原則是把「現在」變成可指定輸入。只要程式邏輯依賴目前時間、deadline、timeout、ticker 或過期判斷，測試就不應依賴真實等待。

## 本章目標

學完本章後，你將能夠：

1. 用 `now time.Time` 測試純狀態轉移
2. 用 `func() time.Time` 注入長生命週期元件的時間來源
3. 用 table-driven test 覆蓋時間邊界
4. 把 ticker 排程與單次工作拆開測
5. 避免 `time.Sleep` 造成慢且不穩定的測試

---

## 【觀察】直接呼叫 time.Now 會讓測試失去控制

時間相關邏輯的核心問題是同一筆資料在不同時間會得到不同結果。若函式內部直接呼叫 `time.Now()`，測試就無法完整控制輸入。

反模式：

```go
func Status(job Job) string {
    if job.FinishedAt != nil {
        return "completed"
    }
    if time.Since(job.StartedAt) > 5*time.Minute {
        return "idle"
    }
    return "active"
}
```

這個函式看起來簡單，但測試無法指定「現在剛好是開始後 4 分鐘」或「現在剛好跨過 5 分鐘」。測試只能依賴真實時間，結果慢且不穩定。

## 【判讀】時間是狀態轉移的輸入

時間測試的核心判讀是：如果時間會影響結果，時間就是輸入。把 `now` 放進函式簽名，會讓狀態轉移規則變得可測。

```go
type Job struct {
    StartedAt  time.Time
    FinishedAt *time.Time
}

func Status(now time.Time, job Job) string {
    if job.FinishedAt != nil {
        return "completed"
    }

    if now.Sub(job.StartedAt) > 5*time.Minute {
        return "idle"
    }

    return "active"
}
```

`now` 是明確輸入，因此測試可以建立任何時間點。這也讓讀者一眼看出 `Status` 不是純粹看 `Job`，而是看 `Job` 與目前時間的關係。

## 【執行】用 table-driven test 描述時間邊界

時間邊界的核心測試方式是列出切換點前後的案例。狀態通常在某個 duration 前後改變，table-driven test 能讓這些情境集中呈現。

```go
func TestStatus(t *testing.T) {
    startedAt := time.Date(2026, 4, 22, 10, 0, 0, 0, time.UTC)

    tests := []struct {
        name string
        now  time.Time
        job  Job
        want string
    }{
        {
            name: "active before idle threshold",
            now:  startedAt.Add(4 * time.Minute),
            job:  Job{StartedAt: startedAt},
            want: "active",
        },
        {
            name: "idle after threshold",
            now:  startedAt.Add(6 * time.Minute),
            job:  Job{StartedAt: startedAt},
            want: "idle",
        },
        {
            name: "completed ignores idle threshold",
            now:  startedAt.Add(30 * time.Minute),
            job: Job{
                StartedAt:  startedAt,
                FinishedAt: ptrTime(startedAt.Add(2 * time.Minute)),
            },
            want: "completed",
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Status(tt.now, tt.job)
            if got != tt.want {
                t.Fatalf("Status() = %q, want %q", got, tt.want)
            }
        })
    }
}
```

這個測試不需要 `time.Sleep`。案例名稱直接描述時間邊界，失敗時能快速定位是哪個規則壞了。

## 【策略】長生命週期元件用 time provider

Time provider 的核心用途是讓元件在多個方法中取得時間，但測試仍能控制時間來源。最輕量的形式是 `func() time.Time`。

```go
type Monitor struct {
    now func() time.Time
}

func NewMonitor(now func() time.Time) Monitor {
    if now == nil {
        now = time.Now
    }
    return Monitor{now: now}
}

func (m Monitor) Snapshot(job Job) string {
    return Status(m.now(), job)
}
```

測試提供固定時間：

```go
func TestMonitorSnapshot(t *testing.T) {
    fixedNow := time.Date(2026, 4, 22, 10, 10, 0, 0, time.UTC)
    monitor := NewMonitor(func() time.Time {
        return fixedNow
    })

    got := monitor.Snapshot(Job{
        StartedAt: fixedNow.Add(-10 * time.Minute),
    })
    if got != "idle" {
        t.Fatalf("snapshot = %q, want idle", got)
    }
}
```

這比導入大型 clock framework 更輕量，也比在測試裡等待真實時間更可靠。若整個專案有大量時間需求，再考慮統一 clock interface。

## 【判讀】Ticker 測試要拆排程與工作

Ticker 的核心問題是它同時包含「何時觸發」與「觸發時做什麼」。測試時應把單次工作抽出來，避免為了測狀態規則而等待 ticker。

```go
type Worker struct {
    syncOnce func(context.Context) error
}

func (w Worker) Run(ctx context.Context, interval time.Duration) error {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            if err := w.SyncOnce(ctx); err != nil {
                return err
            }
        }
    }
}

func (w Worker) SyncOnce(ctx context.Context) error {
    return w.syncOnce(ctx)
}
```

`SyncOnce` 可以單獨測規則，`Run` 只需要少數測試確認 context 取消與 ticker 排程。不要讓每個狀態測試都真的啟動 ticker。

## 【測試】Run 測試應用 context 控制退出

長生命週期 worker 的測試核心是讓退出條件可控。若只想測 context 取消，先取消 context 再呼叫 `Run`。

```go
func TestRunStopsWhenContextCanceled(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    cancel()

    worker := Worker{
        syncOnce: func(context.Context) error {
            t.Fatalf("syncOnce should not be called")
            return nil
        },
    }

    err := worker.Run(ctx, time.Hour)
    if !errors.Is(err, context.Canceled) {
        t.Fatalf("Run() error = %v, want context canceled", err)
    }
}
```

這個測試不需要等待一小時。`time.Hour` 只是確保 ticker 不會在測試中自然觸發，真正的退出由 context 控制。

## 【判讀】sleep-based test 應該是例外

Sleep-based test 的核心問題是慢、不穩定、難以定位。排程、CI 負載與機器速度都可能讓測試偶發失敗。

反模式：

```go
func TestStatusWithSleep(t *testing.T) {
    start := time.Now()
    time.Sleep(6 * time.Minute)
    got := Status(time.Now(), Job{StartedAt: start})
    _ = got
}
```

這種測試不應存在。它拖慢測試套件，仍然不能保證結果穩定。正確做法是直接建構 `now` 與 `StartedAt`。

若真的要等待非同步事件，應使用 deadline 與條件重試，而不是固定 sleep；下一章的 integration test 會使用這個原則。

## 本章不處理

本章不討論完整 fake clock library、模擬 runtime timer 或時間旅行測試框架。這些工具可以在大型系統中使用，但多數 Go 服務先用 `now time.Time` 與 `func() time.Time` 就能解決主要問題。

如果時間問題來自 heartbeat、read deadline 或 shutdown timeout，應回到對應服務設計章節：[heartbeat、deadline 與連線清理](../02-networking-websocket/heartbeat-deadline/)、[graceful shutdown 與 signal handling](../06-production-operations/graceful-shutdown/) 與 [Kubernetes、systemd 與 load balancer 合約](../07-distributed-operations/deployment-contracts/)。

## 小結

時間控制測試的重點是把時間變成可指定輸入。純邏輯用 `now time.Time`，長生命週期元件用 `func() time.Time`，ticker 排程和單次工作分開測。避免 `time.Sleep`，測試才會快速、穩定且可重現。
