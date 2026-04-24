---
title: "2.4 常數與 typed string"
date: 2026-04-22
description: "管理狀態值、事件類型與協定字串"
weight: 4
---

常數讓程式中的固定值有名稱。typed string 則讓一組字串值形成語意邊界，避免任意字串到處流動。

## 本章目標

學完本章後，你將能夠：

1. 用 `const` 定義固定值
2. 理解 untyped constant 與 typed constant 的差異
3. 用 typed string 表達狀態與事件類型
4. 集中管理協定字串與 [log](/backend/knowledge-cards/log/) message

---

## 【觀察】字串散落會增加維護成本

協定字串的核心問題是：同一個語意若以裸字串散落在程式中，拼字、修改與合法值判斷都會變成隱性成本。以下是裸字串散落的典型樣子：

```go
if status == "active" {
    // ...
}

if eventType == "user.created" {
    // ...
}

log.Println("user created")
```

短期看起來很直接，但問題是：

- 拼字錯誤不容易被發現
- 修改字串時要全專案搜尋
- 無法從型別看出哪些值是合法的
- 不同概念可能共用同一種 `string`

常數可以先解決命名與集中管理問題。

## 【判讀】const 是把意圖寫進名稱

`const` 的核心用途是把固定值的意圖寫進名稱。Go 的常數宣告如下：

```go
const DefaultPort = 8080
const EventUserCreated = "user.created"
```

使用常數後，呼叫端讀到的是語意：

```go
if eventType == EventUserCreated {
    // ...
}
```

這比直接看到 `"user.created"` 更清楚，因為名稱說明了這個字串在系統中的角色。

## 【策略】用 typed string 區分概念

typed string 的核心用途是用型別區分不同語意的字串。當多組資料底層都是字串，但語意不同，可以定義不同型別：

```go
type TaskStatus string

const (
    TaskStatusPending TaskStatus = "pending"
    TaskStatusRunning TaskStatus = "running"
    TaskStatusDone    TaskStatus = "done"
    TaskStatusFailed  TaskStatus = "failed"
)
```

函式簽名可以明確要求 `TaskStatus`：

```go
func CanRetry(status TaskStatus) bool {
    return status == TaskStatusFailed
}
```

這不會讓 Go 變成 enum 語言，但能讓 API 更清楚。讀者看到 `TaskStatus`，就知道這不是任意字串。

## 【執行】事件類型與 action 常數

事件類型的核心規則是：同一組事件值應集中在同一個 typed string 型別下。事件驅動程式常需要管理事件類型：

```go
type EventType string

const (
    EventUserCreated EventType = "user.created"
    EventUserUpdated EventType = "user.updated"
    EventUserDeleted EventType = "user.deleted"
)
```

API action 也可以用同樣方式：

```go
type Action string

const (
    ActionSubscribe   Action = "subscribe"
    ActionUnsubscribe Action = "unsubscribe"
    ActionPing        Action = "ping"
)
```

處理時，switch 會變得可讀：

```go
func HandleAction(action Action) error {
    switch action {
    case ActionSubscribe:
        return nil
    case ActionUnsubscribe:
        return nil
    case ActionPing:
        return nil
    default:
        return fmt.Errorf("unknown action: %s", action)
    }
}
```

## log message 也適合集中

log message 的核心規則是：會被 grep、監控或文件引用的訊息應保持穩定。這類 message 可以用常數集中：

```go
const (
    LogServerStarted = "server started"
    LogEventDropped  = "event dropped"
    LogInvalidAction = "invalid action"
)
```

這樣做的價值不是省打字，而是讓 log 訊號穩定。當 log 是除錯入口時，穩定字串就是系統 contract 的一部分。

## 常見取捨

### 不必把所有字串都變常數

只出現一次、沒有協定意義、不需要搜尋的文字，可以直接寫在原處。過度常數化會讓讀者一直跳檔案。

### 常數名稱要說明清楚概念

如果常數名稱只是重複值本身，幫助不大：

```go
const StringActive = "active" // 不佳
```

比較好的名稱要說明概念：

```go
const TaskStatusActive TaskStatus = "active"
```

## 小結

常數讓固定值有名稱，typed string 讓一組固定字串有語意邊界。當字串代表狀態、事件、action 或 log 訊號時，集中命名能降低拼錯、誤用與搜尋成本。
