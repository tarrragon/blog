---
title: "1.1 channel ownership 與關閉責任"
date: 2026-04-22
description: "判斷誰能送出、接收與關閉 channel"
weight: 1
---

Channel ownership 的核心規則是：能保證不再送出資料的一方，才有資格關閉 channel。建立 channel 的程式碼不一定是 owner；真正的 owner 是掌握 send lifecycle 的元件。

## 本章目標

學完本章後，你將能夠：

1. 用 send lifecycle 判斷誰能 close channel
2. 分辨 sender、receiver、coordinator 的責任
3. 用 channel direction 表達能力限制
4. 設計多 sender 的安全關閉流程
5. 用 context 表達接收端提早停止，而不是關閉不屬於自己的 channel

---

## 【觀察】close channel 的核心風險是責任不清

Channel 關閉錯誤的核心問題不是語法，而是 ownership 沒定義清楚。接收端想停止讀取時關閉輸入 channel，多個 sender 中任一個 sender 自行 close，共用 channel 被外部任意 close，這些都可能造成 panic 或資料遺失。

責任不清的示例：

```go
func Consume(input chan Event) {
    defer close(input)

    for event := range input {
        handle(event)
    }
}
```

這段程式的問題是 `Consume` 只是 receiver，卻關閉了 sender 還可能使用的 channel。只要上游晚一點送資料，就會出現 `send on closed channel`。

## 【判讀】close 的語意是不再有新值

`close(ch)` 的核心語意是「這個 channel 不會再收到新值」。它不是取消 goroutine 的通用手段，也不是釋放記憶體的必要動作。

單一 sender 可以安全 close：

```go
func Produce(items []string) <-chan string {
    out := make(chan string)

    go func() {
        defer close(out)
        for _, item := range items {
            out <- item
        }
    }()

    return out
}
```

這個 goroutine 是唯一 sender，因此它能保證迴圈結束後不再送出。receiver 可以用 `range` 讀到 channel 關閉為止：

```go
for item := range Produce([]string{"a", "b"}) {
    fmt.Println(item)
}
```

receiver 不需要 close `out`。接收完資料是 receiver 的狀態，不代表 sender 的生命週期已經結束。

## 【策略】先畫出 sender 和 receiver

Channel 設計的核心動作是先列出誰會 send、誰會 receive、誰知道所有 sender 已經結束。這比先決定 buffer 大小更重要。

| 角色            | 能力                                    | close 責任            |
| --------------- | --------------------------------------- | --------------------- |
| single sender   | 送出資料，知道自己何時結束              | 擁有 close 責任       |
| receiver        | 接收資料，可能提早停止                  | 透過 context 通知停止 |
| coordinator     | 等待所有 sender 結束                    | 擁有 close 責任       |
| external caller | 持有 channel reference 但不了解生命週期 | 不參與 close 決策     |

如果無法回答「誰知道所有 sender 都結束」，就不應該 close 這個 channel。沒有 close 不一定是 bug；錯誤 close 才是更嚴重的問題。

## 【執行】多 sender 需要 coordinator 關閉

多個 goroutine 送往同一個 channel 時，關閉責任必須交給 coordinator。任一 sender 都不能單方面 close，因為其他 sender 可能還在送。

```go
func Merge(inputs ...<-chan Event) <-chan Event {
    out := make(chan Event)
    var wg sync.WaitGroup

    wg.Add(len(inputs))
    for _, input := range inputs {
        input := input
        go func() {
            defer wg.Done()
            for event := range input {
                out <- event
            }
        }()
    }

    go func() {
        wg.Wait()
        close(out)
    }()

    return out
}
```

轉送 goroutine 只負責送資料。另一個 goroutine 等所有 sender 結束後才 close `out`。這把「送資料」和「宣告所有資料送完」分成兩個責任。

## 【執行】接收端提早停止要用 context

Receiver 提早停止的核心做法是通知上游停止，而不是關閉輸入 channel。`context.Context` 是 Go 服務中最常見的停止訊號。

```go
func Consume(ctx context.Context, input <-chan Event) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case event, ok := <-input:
            if !ok {
                return nil
            }
            handle(event)
        }
    }
}
```

`Consume` 可以因為 context 取消而退出，也可以因為 input 關閉而退出。它沒有 close `input`，因為 input 的 send lifecycle 不屬於它。

這個邊界在服務中很重要。HTTP handler、background worker、connection writer 都可能提早退出，但不能任意 close 上游仍可能使用的 channel。

## 【策略】channel direction 把能力寫進型別

Channel direction 的核心價值是限制函式能做的事。`chan<- T` 只能 send，`<-chan T` 只能 receive；這讓 ownership 更容易被讀者看見。

```go
func StartWorker(ctx context.Context, jobs <-chan Job, results chan<- Result) {
    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-jobs:
            if !ok {
                return
            }
            results <- Process(job)
        }
    }
}
```

`StartWorker` 只能從 `jobs` 收資料，只能往 `results` 送資料。它不能 close `jobs`，因為型別上就不是 sender；它是否能 close `results` 則要看它是不是唯一 sender。

方向限制不會自動解決所有權，但它能減少誤用，也讓 API 比註解更可靠。

## 【判讀】done channel 和 data channel 分開表達不同語意

停止訊號的核心語意應該和資料流分開。資料 channel 傳遞值；done channel 或 context 表示停止。把兩者混在一起會讓 close 的語意變模糊。

較清楚的設計：

```go
type Worker struct {
    jobs <-chan Job
}

func (w Worker) Run(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-w.jobs:
            if !ok {
                return
            }
            process(job)
        }
    }
}
```

`jobs` 關閉代表沒有更多 job。`ctx.Done()` 代表上層要求停止。這兩種退出原因不同，分開處理才能在 log、metric 或測試中看清楚。

## 【測試】測試 close 行為要避免靠 sleep

Channel ownership 的測試目標是確認 sender 結束後會 close、receiver 取消時不會 panic、多 sender 等全部完成才 close。這類測試應使用 channel 同步，不應依賴任意 sleep。

```go
func TestProduceClosesOutput(t *testing.T) {
    output := Produce([]string{"a"})

    if got := <-output; got != "a" {
        t.Fatalf("first value = %q, want %q", got, "a")
    }

    _, ok := <-output
    if ok {
        t.Fatalf("output should be closed after producer finishes")
    }
}
```

多 sender 測試可以讀到輸出 channel 關閉為止，確認所有值都收到：

```go
func TestMergeClosesAfterAllInputsClose(t *testing.T) {
    a := make(chan Event, 1)
    b := make(chan Event, 1)
    a <- Event{ID: "a"}
    b <- Event{ID: "b"}
    close(a)
    close(b)

    output := Merge(a, b)
    got := map[string]bool{}
    for event := range output {
        got[event.ID] = true
    }

    if !got["a"] || !got["b"] {
        t.Fatalf("merge should forward all events before closing")
    }
}
```

這個測試沒有固定等待時間。它把 channel close 本身當成同步訊號，結果更穩定。

## 本章不處理

本章先聚焦單一 Go process 內的 channel close 與 goroutine lifecycle；跨 process 的 ack、consumer group 與分散式訊號，會在下列章節再往外延伸：

- [Backend：訊息佇列與事件傳遞](../../backend/03-message-queue/)
- [Backend：可靠性驗證流程](../../backend/06-reliability/)

## 和 Go 教材的關係

這一章承接的是 channel、goroutine 與 select 的協作；如果你要先回看語言教材，可以讀：

- [Go：goroutine：輕量並發工作](../../go/04-concurrency/goroutine/)
- [Go：channel：資料傳遞與背壓](../../go/04-concurrency/channel/)
- [Go：select：同時等待多種事件](../../go/04-concurrency/select/)
- [Go：bounded worker pool](worker-pool/)

## 小結

Channel ownership 的核心是 send lifecycle。唯一 sender 可以在送完後 close；多 sender 需要 coordinator 統一 close；receiver 想停止時應使用 context，而不是關閉輸入 channel。把 sender、receiver、coordinator 分清楚，才能避免 `send on closed channel`、goroutine leak 與資料流混亂。
