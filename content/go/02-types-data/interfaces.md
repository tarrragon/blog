---
title: "2.3 interface：用行為定義依賴"
date: 2026-04-22
description: "用小介面描述元件需要的能力"
weight: 3
---

Go 的 interface 描述的是行為，不是繼承關係。你不需要在 concrete type 上宣告「我實作了某個 interface」；只要方法集合符合，Go 就視為實作。

## 本章目標

學完本章後，你將能夠：

1. 理解 implicit interface 的設計精神
2. 寫出小而精準的 interface
3. 避免把 concrete type 暴露給不需要的呼叫者
4. 用 interface 改善測試與依賴邊界

---

## 【觀察】interface 只描述需要的行為

interface 的核心規則是：只描述呼叫者需要的行為，不描述實作者的完整身份。假設有一個函式要把訊息寫到某個目的地；它不需要知道目的地是檔案、記憶體 buffer，還是網路連線，只需要知道對方能 `Write`。

```go
type Writer interface {
    Write(p []byte) (n int, err error)
}

func WriteMessage(w Writer, message string) error {
    _, err := w.Write([]byte(message))
    return err
}
```

這個 interface 很小，只描述一個行為：寫入 bytes。

## 【判讀】Go interface 是由使用者定義的需求

在 Go 裡，interface 常由「使用者」定義，而不是由「實作者」定義。

這和很多語言不同。你不需要在某個型別上寫：

```go
// Go 不需要這種宣告
type File implements Writer
```

implicit interface 的核心規則是：只要型別有相同方法，就符合 interface，不需要顯式宣告實作關係。

```go
type MemoryWriter struct {
    data []byte
}

func (m *MemoryWriter) Write(p []byte) (int, error) {
    m.data = append(m.data, p...)
    return len(p), nil
}
```

`MemoryWriter` 沒有提到 `Writer`，但它已經符合 `Writer`。

## 【策略】interface 越小，依賴越清楚

小 interface 的核心規則是：interface 應由使用端需要的最小行為組成。Go 常見的好 interface 很小：

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
}
```

小 interface 的好處是：

- 呼叫者只依賴自己真正需要的行為
- 測試替身容易寫
- concrete type 可以在不同情境中被重用
- 未來改內部結構時，外部影響較小

反例是把太多方法塞進一個 interface：

```go
type UserService interface {
    CreateUser(User) error
    UpdateUser(User) error
    DeleteUser(string) error
    FindUser(string) (User, error)
    ListUsers() ([]User, error)
    ExportUsers() ([]byte, error)
}
```

如果某個函式只需要查詢 user，卻依賴整個 `UserService`，它就知道太多了。

## 【執行】為查詢需求設計小介面

依賴邊界的核心規則是：使用端只依賴自己需要的方法。假設一個 HTTP handler 只需要查詢使用者名稱：

```go
type UserLookup interface {
    FindName(userID string) (string, bool)
}

type Handler struct {
    users UserLookup
}

func NewHandler(users UserLookup) *Handler {
    return &Handler{users: users}
}
```

這個 handler 不知道 user 是存在 map、資料庫、檔案，還是測試假物件裡。它只知道自己需要 `FindName`。

測試時可以寫一個很小的 fake：

```go
type fakeUsers map[string]string

func (f fakeUsers) FindName(userID string) (string, bool) {
    name, ok := f[userID]
    return name, ok
}
```

這就是 Go interface 最實用的地方：它讓依賴變小，讓測試變簡單。

## 何時先保留 concrete type

interface 的使用邊界是：替換需求或測試替身需求清楚時，再抽出小介面。以下情境通常適合先保留 concrete type：

- 只有一個 concrete type，而且沒有測試替身需求
- interface 只是完整複製 concrete type 的所有方法
- 你還不確定呼叫者真正需要哪些行為

Go 的常見做法是：先寫 concrete type，等使用端出現明確需求，再抽小 interface。

## 小結

Go interface 的核心是「用行為定義依賴」。好的 interface 通常很小，由使用者端定義，讓程式只依賴自己需要的能力，而不是依賴整個實作物件。
