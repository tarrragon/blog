---
title: "2.2 slice 與 map"
date: 2026-04-22
description: "掌握 Go 最常用的集合型別：slice 與 map"
weight: 2
---

# slice 與 map

slice 和 map 是 Go 最常用的集合型別。slice 表達有順序的資料列表，map 表達 key-value 查詢表。理解它們的行為，是寫出可靠 Go 程式的基本功。

## 本章目標

學完本章後，你將能夠：

1. 建立與操作 slice
2. 理解 slice 的長度、容量與 append
3. 建立與操作 map
4. 判斷何時使用 slice，何時使用 map
5. 避免 nil slice、nil map 與共享底層資料的常見問題

---

## 【觀察】slice 表達有順序的資料

slice 是 Go 中用來表示有順序元素列表的集合型別。以下範例建立一個 `[]string`，並依照索引順序走訪：

```go
names := []string{"Alice", "Bob", "Carol"}

for i, name := range names {
    fmt.Println(i, name)
}
```

slice 的常見操作是讀取元素、取得長度、用 `append` 增加元素：

```go
names = append(names, "Dave")
first := names[0]
count := len(names)
```

`append` 的核心規則是：它會回傳 append 後的 slice，呼叫端必須接回結果。`len(names)` 取得元素數量；`append` 可能重用原底層 array，也可能配置新底層 array：

```go
names = append(names, "Eve")
```

## 【判讀】slice 是對底層 array 的視窗

slice 的核心模型是「指向底層 array 的視窗」，不是 array 本身。它比較像一個描述底層 array 區段的 header，包含：

```text
pointer -> 底層 array
len     -> 目前看得到幾個元素
cap     -> 從起點到底層 array 結尾還有多少容量
```

長度與容量分別描述「目前元素數」與「不重新配置時還能擴張多少」。以下範例可以觀察 `len` 和 `cap` 的變化：

```go
items := make([]int, 0, 3)
fmt.Println(len(items), cap(items)) // 0 3

items = append(items, 10)
fmt.Println(len(items), cap(items)) // 1 3
```

`append` 超過容量時，Go 可能會配置新的底層 array：

```go
items = append(items, 20, 30, 40)
fmt.Println(len(items), cap(items))
```

這就是 `append` 必須接回原變數的原因：append 後的 slice 可能已經指向新的底層資料。

## 【策略】用 slice 保存順序，用 map 做查詢

選擇集合型別的核心規則是：在意順序用 slice，需要 key-value 查詢用 map。如果你在意資料順序，用 slice：

```go
tasks := []string{"read", "write", "test"}
```

如果你要用 key 快速查資料，用 map：

```go
scores := map[string]int{
    "Alice": 90,
    "Bob":   85,
}
```

讀取 map：

```go
score, ok := scores["Alice"]
if ok {
    fmt.Println(score)
}
```

map 讀取的核心規則是：需要分辨「不存在」和「零值」時，必須使用 `value, ok`。key 不存在時，map 會回傳 value type 的零值：

```go
score := scores["Unknown"] // 0
```

如果不檢查 `ok`，你無法分辨「不存在」和「存在但分數是 0」。

## 【執行】nil slice 與 nil map 的差異

nil slice 和 nil map 的核心差異是：nil slice 可以 append，nil map 不能寫入。nil slice 可以 append：

```go
var names []string
names = append(names, "Alice")
```

nil map 不能直接寫入：

```go
var scores map[string]int
scores["Alice"] = 90 // panic
```

map 寫入前必須先初始化：

```go
scores := make(map[string]int)
scores["Alice"] = 90
```

或用 literal：

```go
scores := map[string]int{
    "Alice": 90,
}
```

## slice 和 map 的常見組合

### 用 slice 保存輸出順序

map 的迭代順序不保證穩定；如果輸出順序重要，必須額外用 slice 保存或排序 key：

```go
for name, score := range scores {
    fmt.Println(name, score)
}
```

先整理 key：

```go
names := make([]string, 0, len(scores))
for name := range scores {
    names = append(names, name)
}
sort.Strings(names)

for _, name := range names {
    fmt.Println(name, scores[name])
}
```

### 用 map 當 set

Go 沒有內建 set；需要集合語義時，常用 `map[string]struct{}` 表示「某個 key 是否存在」：

```go
seen := make(map[string]struct{})
seen["Alice"] = struct{}{}

if _, ok := seen["Alice"]; ok {
    fmt.Println("already seen")
}
```

如果想更直觀，也可以用 `map[string]bool`：

```go
seen := map[string]bool{
    "Alice": true,
}
```

## 常見錯誤

### 錯誤一：忽略 append 回傳值

```go
append(names, "Alice") // 編譯錯誤：append 結果未使用
```

正確做法：

```go
names = append(names, "Alice")
```

### 錯誤二：寫入 nil map

```go
var m map[string]int
m["x"] = 1 // panic
```

正確做法：

```go
m := make(map[string]int)
m["x"] = 1
```

### 錯誤三：假設 map 迭代順序穩定

map 的順序不能拿來做穩定輸出、測試 snapshot 或 UI 排序。需要順序就額外維護 slice。

## 小結

slice 適合有順序的資料，map 適合 key-value 查詢。slice 的重點是 append、len、cap 與底層 array；map 的重點是初始化、`value, ok` 讀取與不保證迭代順序。
