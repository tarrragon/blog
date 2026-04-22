---
title: "1.6 函式、方法與 receiver"
date: 2026-04-22
description: "區分普通函式、建構函式與帶 receiver 的方法"
weight: 6
---

Go 沒有 class，但有函式、struct 與方法。方法只是帶有 receiver 的函式；receiver 讓函式和某個型別形成關聯，進而表達「這個行為屬於這個資料」。

## 本章目標

學完本章後，你將能夠：

1. 區分普通函式與方法
2. 理解 receiver 的語法與語義
3. 判斷何時使用 pointer receiver
4. 用建構函式集中初始化規則

---

## 【觀察】普通函式不屬於特定值

普通函式的核心規則是：它不綁定特定型別，只接收參數並回傳結果。以下函式只負責把名稱正規化：

```go
func NormalizeName(name string) string {
    return strings.TrimSpace(strings.ToLower(name))
}
```

呼叫方式：

```go
name := NormalizeName(" Alice ")
```

這種函式適合描述純粹轉換：輸入什麼，輸出什麼，不需要修改某個物件的內部狀態。

## 【判讀】方法是帶 receiver 的函式

方法的核心規則是：函式若需要以某個型別作為操作對象，就用 receiver 綁到該型別。行為和某個型別密切相關時，可以寫成方法：

```go
type Counter struct {
    value int
}

func (c *Counter) Inc() {
    c.value++
}

func (c Counter) Value() int {
    return c.value
}
```

`(c *Counter)` 和 `(c Counter)` 就是 receiver。它放在 `func` 和方法名稱之間，表示這個函式是 `Counter` 的方法。

呼叫方式：

```go
var c Counter
c.Inc()
fmt.Println(c.Value())
```

Go 會讓方法呼叫看起來像物件操作，但本質仍然是函式呼叫。

## 【策略】用是否修改狀態選擇 receiver

receiver 選擇的核心規則是：要修改原值用 pointer receiver，不修改且型別小可以用 value receiver。receiver 有兩種常見形式：

| receiver         | 適用情境                           |
| ---------------- | ---------------------------------- |
| value receiver   | 不修改原值，型別小，複製成本低     |
| pointer receiver | 需要修改原值，或型別較大，避免複製 |

例如 `Value()` 不修改 `Counter`，可以用 value receiver：

```go
func (c Counter) Value() int {
    return c.value
}
```

`Inc()` 需要修改原本的 counter，所以使用 pointer receiver：

```go
func (c *Counter) Inc() {
    c.value++
}
```

如果你不確定，先問一個問題：這個方法是否要改變 receiver 的狀態？答案是 yes，通常就用 pointer receiver。

## 【執行】用建構函式集中初始化

建構函式的核心用途是集中初始化規則。Go 沒有 constructor 關鍵字，但慣例會用 `NewTypeName` 建立需要初始化的型別：

```go
type Cache struct {
    items map[string]string
}

func NewCache() *Cache {
    return &Cache{
        items: make(map[string]string),
    }
}

func (c *Cache) Set(key, value string) {
    c.items[key] = value
}

func (c *Cache) Get(key string) (string, bool) {
    value, ok := c.items[key]
    return value, ok
}
```

使用方式：

```go
cache := NewCache()
cache.Set("theme", "dark")
value, ok := cache.Get("theme")
```

這裡 `NewCache()` 的價值不是語法必要，而是保證 `items` 一定被初始化。呼叫者不需要知道 `Cache` 內部有 map，也不需要記得手動 `make`。

## 函式還是方法？

函式與方法的選擇規則是：純轉換用函式，依賴型別狀態用方法，需要初始化保證用 `NewTypeName`。可以用這張表判斷：

| 問題                     | 選擇                   |
| ------------------------ | ---------------------- |
| 只是轉換資料？           | 普通函式               |
| 行為依賴某個型別的狀態？ | 方法                   |
| 需要保證初始化規則？     | `NewTypeName` 建構函式 |
| 需要符合 interface？     | 方法                   |

範例：

```go
func ParsePort(raw string) (int, error) {
    // 純資料轉換，適合普通函式
}

func (s *Server) Start() error {
    // 啟動 Server，適合方法
}
```

## 小結

Go 用函式處理一般邏輯，用方法把行為綁到資料型別上。receiver 不代表繼承，只代表「這個函式以這個型別作為操作對象」。理解這一點，Go 的物件模型就會變得很直接。
