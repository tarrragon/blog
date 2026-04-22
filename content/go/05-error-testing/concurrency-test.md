---
title: "5.6 並發行為測試"
date: 2026-04-22
description: "測試 channel、goroutine 與狀態更新"
weight: 6
---

# 並發行為測試

並發測試的核心目標是驗證可觀察的同步行為，而不是猜測 goroutine 的執行順序。Go 的 goroutine 由 scheduler 安排，測試應該用 channel、context、WaitGroup 與 timeout 表達「什麼結果必須發生」。

## 不要依賴 goroutine 執行順序

並發程式的核心限制是執行順序不穩定。測試如果假設某個 goroutine 一定先跑，通常會變成偶發失敗。

```go
func sendAsync(ch chan<- string) {
	go func() {
		ch <- "ready"
	}()
}
```

測試不應該在呼叫後立刻假設資料已經送出，而應該等待明確訊號。

```go
func TestSendAsync(t *testing.T) {
	ch := make(chan string, 1)

	sendAsync(ch)

	select {
	case got := <-ch:
		if got != "ready" {
			t.Fatalf("message = %q, want %q", got, "ready")
		}
	case <-time.After(time.Second):
		t.Fatalf("timeout waiting for message")
	}
}
```

`select` 加 timeout 可以避免測試永久卡住。timeout 不應該用來證明程式正確，只是測試失敗時的保護機制。

## channel 測試要驗證傳遞結果

channel 測試的核心問題是資料是否被送到預期位置。測試應該觀察 channel 收到的值，或觀察 channel 關閉後的狀態。

```go
func Produce(ids []string) <-chan string {
	out := make(chan string)

	go func() {
		defer close(out)
		for _, id := range ids {
			out <- id
		}
	}()

	return out
}
```

這個函式回傳只讀 channel，呼叫端可以 range 讀取直到 channel 關閉。

```go
func TestProduce(t *testing.T) {
	out := Produce([]string{"a", "b"})

	var got []string
	for id := range out {
		got = append(got, id)
	}

	want := []string{"a", "b"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("Produce() = %#v, want %#v", got, want)
	}
}
```

這個測試沒有使用 sleep。channel 關閉就是明確完成訊號，測試可以自然結束。

## context 用來測試退出

goroutine 退出測試的核心做法是提供可取消的 `context.Context`，再等待函式發出完成訊號。沒有退出訊號的 goroutine 很難可靠測試。

```go
func RunWorker(ctx context.Context, jobs <-chan string, done chan<- struct{}) {
	defer close(done)

	for {
		select {
		case <-ctx.Done():
			return
		case <-jobs:
			// process job
		}
	}
}
```

測試可以取消 context，然後確認 `done` 被關閉。

```go
func TestRunWorkerStops(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	jobs := make(chan string)
	done := make(chan struct{})

	go RunWorker(ctx, jobs, done)
	cancel()

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatalf("worker did not stop")
	}
}
```

`done` channel 是測試與 goroutine 之間的完成協定。若程式沒有這種協定，測試只能猜測 goroutine 是否已經退出。

## `sync.WaitGroup` 適合等待一組工作完成

`WaitGroup` 的核心用途是等待已知數量的 goroutine 完成。它適合 fan-out 工作、批次處理與測試中需要等多個背景任務結束的情境。

```go
func ProcessAll(items []string, process func(string)) {
	var wg sync.WaitGroup

	for _, item := range items {
		item := item
		wg.Add(1)
		go func() {
			defer wg.Done()
			process(item)
		}()
	}

	wg.Wait()
}
```

測試可以用 mutex 保護共享 slice，並在函式回傳後檢查結果。

```go
func TestProcessAll(t *testing.T) {
	var mu sync.Mutex
	var got []string

	ProcessAll([]string{"a", "b"}, func(item string) {
		mu.Lock()
		defer mu.Unlock()
		got = append(got, item)
	})

	sort.Strings(got)
	want := []string{"a", "b"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("processed = %#v, want %#v", got, want)
	}
}
```

因為 goroutine 執行順序不固定，測試先排序再比較。這表示測試關心「所有項目都有被處理」，不關心處理順序。

## race detector 檢查共享狀態

共享狀態測試的核心風險是 data race。Go 提供 race detector，可以在測試時檢查多個 goroutine 是否未同步讀寫同一份資料。

```bash
go test -race ./...
```

`-race` 會讓測試變慢，但能抓出許多一般斷言看不見的並發錯誤。只要程式有 goroutine 與共享資料，定期跑 race test 就很有價值。

race detector 不是邏輯正確性的完整證明。它能檢查資料競爭，但不能保證事件順序、buffer 策略或 timeout 行為都符合需求；這些仍然要靠明確測試案例。

## 小結

並發測試應該觀察同步訊號，而不是等待運氣。channel 可以驗證資料傳遞與完成，context 可以控制退出，WaitGroup 可以等待一組工作，race detector 可以檢查共享狀態的資料競爭。好的並發測試會讓 goroutine 的生命週期可見，讓失敗可以被穩定重現。
