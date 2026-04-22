---
title: "5.4 table-driven test 的設計邊界"
date: 2026-04-22
description: "避免測試資料混雜太多概念"
weight: 4
---

# table-driven test 的設計邊界

Table-driven test 的核心邊界是每張表只描述一個行為維度。它能降低重複並清楚列出案例，但不適合把多種 setup、多種執行方式與多種斷言硬塞進同一個測試。

## 本章目標

學完本章後，你將能夠：

1. 判斷什麼行為適合 table-driven test
2. 設計欄位少、意圖清楚的測試表
3. 發現 table test 膨脹成迷你框架的訊號
4. 拆分 validation、repository error、integration flow
5. 寫出能定位失敗情境的子測試名稱

---

## 【觀察】table-driven test 很容易被濫用

Table-driven test 的核心風險是「減少重複」被誤解成「所有案例都塞進一張表」。當表格開始同時控制 HTTP method、request body、repository 狀態、WebSocket client、expected log、expected event，測試就會變成難懂的迷你框架。

失控表格示意：

```go
tests := []struct {
    name          string
    method        string
    body          string
    setupRepo     bool
    setupClient   bool
    queueFull     bool
    wantStatus    int
    wantMessage   string
    wantEvent     bool
    wantLog       bool
}{
    // many unrelated cases
}
```

這種表格看似統一，實際上混合了 HTTP validation、repository error、client queue full、event emission、log assertion。讀者必須同時理解多個系統層，才能看懂單一案例。

## 【判讀】好表格描述同一個行為維度

好的 table-driven test 的核心特徵是所有案例共享相同 setup、相同執行方式、相同斷言方式。表格只改變資料，不改變測試流程。

```go
func TestNormalizeTopic(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  string
    }{
        {name: "trim spaces", input: " alerts ", want: "alerts"},
        {name: "lowercase", input: "ALERTS", want: "alerts"},
        {name: "empty", input: "", want: ""},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := NormalizeTopic(tt.input)
            if got != tt.want {
                t.Fatalf("NormalizeTopic(%q) = %q, want %q", tt.input, got, tt.want)
            }
        })
    }
}
```

這張表只測 topic normalization。每個案例都只有 input 和 want，失敗時也能立刻看出是哪個 normalization 規則壞了。

## 【策略】表格欄位越多，越要懷疑測試邊界

Table 欄位的核心警訊是大量欄位只被少數案例使用。這通常表示不同測試目的被合併在一起。

拆分判斷：

| 現象 | 問題 | 建議 |
|------|------|------|
| 很多 `setupX bool` | setup 不一致 | 拆成不同測試 |
| 很多 `wantX bool` | 斷言目標不一致 | 拆成不同測試 |
| loop 內大量 `if tt...` | 測試流程不一致 | 拆表或改成具名測試 |
| 案例名稱很長仍說不清 | 行為維度太多 | 回到單一行為 |
| helper 隱藏主要斷言 | 可讀性下降 | 讓斷言留在測試本文 |

表格不是越通用越好。測試的第一責任是讓失敗可定位，不是消除所有重複。

## 【執行】validation 適合 table test

Validation 的核心特徵是輸入和輸出形狀一致，因此很適合 table-driven test。

```go
func TestValidateSubscribeRequest(t *testing.T) {
    tests := []struct {
        name    string
        request SubscribeTopicRequest
        wantErr bool
    }{
        {
            name:    "valid topic",
            request: SubscribeTopicRequest{Topic: "alerts"},
            wantErr: false,
        },
        {
            name:    "empty topic",
            request: SubscribeTopicRequest{Topic: ""},
            wantErr: true,
        },
        {
            name:    "blank topic",
            request: SubscribeTopicRequest{Topic: "   "},
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateSubscribeRequest(tt.request)
            if (err != nil) != tt.wantErr {
                t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
            }
        })
    }
}
```

這張表只問一件事：request 是否有效。它不測 WebSocket connection、不測 hub、不測 repository，因此案例可以保持簡潔。

## 【執行】狀態轉移也適合 table test

狀態轉移的核心特徵是輸入狀態、事件、期待輸出狀態。只要流程一致，就適合 table-driven test。

```go
func TestJobTransition(t *testing.T) {
    tests := []struct {
        name    string
        current JobStatus
        event   EventType
        want    JobStatus
        wantErr bool
    }{
        {
            name:    "pending starts",
            current: JobPending,
            event:   EventJobStarted,
            want:    JobRunning,
        },
        {
            name:    "running finishes",
            current: JobRunning,
            event:   EventJobFinished,
            want:    JobSucceeded,
        },
        {
            name:    "finished cannot start again",
            current: JobSucceeded,
            event:   EventJobStarted,
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Transition(tt.current, tt.event)
            if (err != nil) != tt.wantErr {
                t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
            }
            if err == nil && got != tt.want {
                t.Fatalf("status = %s, want %s", got, tt.want)
            }
        })
    }
}
```

這張表的欄位都服務同一個行為：job status transition。若未來要測 repository 寫入失敗，應另開測試，不要塞進這張表。

## 【判讀】不同 setup 應拆成不同測試

測試拆分的核心原則是 setup 不同，通常就不是同一張表。HTTP validation、repository error、client queue full 都需要不同環境。

較清楚的拆法：

```go
func TestSubscribeValidation(t *testing.T) {
    // 只測 request validation
}

func TestSubscribeAddsTopic(t *testing.T) {
    // 只測成功訂閱後 client state
}

func TestSubscribeReturnsErrorWhenClientQueueFull(t *testing.T) {
    // 只測 send buffer 滿載時的錯誤語意
}
```

這些測試可能有少量重複，但每個測試的失敗原因更清楚。測試重複一點可以接受；測試意圖混在一起會讓維護成本更高。

## 【策略】helper 只包樣板，不包判斷

Test helper 的核心責任是降低重複 setup，不應隱藏主要斷言。讀者應能在測試本文看到這個測試到底在驗證什麼。

可以包的樣板：

```go
func mustJSON(t *testing.T, value any) json.RawMessage {
    t.Helper()
    data, err := json.Marshal(value)
    if err != nil {
        t.Fatalf("marshal json: %v", err)
    }
    return data
}
```

不建議包成這樣：

```go
func assertSubscribeScenario(t *testing.T, tt subscribeScenario) {
    // setup HTTP, setup WebSocket, setup repository,
    // execute action, check response, check logs, check events
}
```

後者把測試主要邏輯藏進 helper。表格看起來短，但讀者必須跳到 helper 才知道每個欄位如何影響流程。

## 【執行】子測試名稱要描述情境

子測試名稱的核心作用是讓失敗輸出可定位。名稱應描述情境，不應只寫編號或重複函式名稱。

```go
tests := []struct {
    name string
    // ...
}{
    {name: "missing topic"},
    {name: "unknown action"},
    {name: "queue full returns unavailable"},
}
```

`go test` 輸出會包含 `TestValidateSubscribeRequest/missing_topic` 這類資訊。當 CI 失敗時，讀者能先知道哪個情境壞了，再看 got/want 差異。

命名應該描述輸入情境或規則，不需要寫成完整句子，也不要只寫 `case 1`。

## 【測試】table test 本身也要保持可讀

Table-driven test 的核心完成標準是讀者能掃過表格就理解規則。若必須讀整個 loop 才懂欄位意義，表格設計就不夠清楚。

自檢問題：

- 這張表是否只測一個行為？
- 每個欄位是否幾乎每個案例都用得到？
- 測試 loop 裡是否有大量條件分支？
- 子測試名稱是否能定位失敗情境？
- got/want 斷言是否直接留在測試本文？

任一題答否，先考慮拆測試，而不是加更多欄位。

## 本章不處理

本章不討論 property-based testing、fuzzing 或 snapshot testing。這些工具各有價值，但 table-driven test 是 Go 專案最常見的測試組織方式；先把它的邊界用好，能避免大量測試退化成不可讀的資料表。後續可接 [CI、fuzz、load test 與 chaos testing](../07-distributed-operations/reliability-pipeline/)。

## 小結

Table-driven test 適合同一個行為的多組資料，不適合混合多種 setup 與斷言。欄位膨脹、loop 裡大量 `if tt...`、helper 隱藏主要判斷，都是拆表訊號。好的測試表讓案例更清楚，而不是把測試變成迷你框架。
