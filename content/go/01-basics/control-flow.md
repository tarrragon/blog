---
title: "1.3 控制流程：if、for、switch"
date: 2026-04-22
description: "掌握 Go 的條件判斷、迴圈與分支控制"
weight: 3
---

# 控制流程：if、for、switch

Go 控制流程的核心規則是：語法少但語意明確；`if` 處理條件分支，`for` 是唯一迴圈語法，`switch` 用於多分支判斷。本章將建立閱讀 Go 流程控制的基本模型。

## `if` 表達條件與提前返回

`if` 的核心責任是根據條件決定程式是否進入某段邏輯。Go 的 `if` 條件不需要小括號，但區塊大括號是必要語法。

```go
if age >= 18 {
	fmt.Println("adult")
}
```

Go 不會把數字、字串或指標自動當成布林值。條件必須是明確的 `bool` 表達式。

```go
count := 3

if count > 0 {
	fmt.Println("has items")
}

// if count {
// 	fmt.Println("invalid")
// }
```

這個規則讓條件判斷更直接：讀者不需要猜某個非布林值在條件中會被如何轉換。

## `if` 可以包含短宣告

`if` 的短宣告用來把只屬於這個判斷的暫存變數限制在區塊內。這讓錯誤處理與查找結果的作用範圍更清楚。

```go
if value, ok := cache["user:1"]; ok {
	fmt.Println("cache hit:", value)
}
```

`value` 與 `ok` 只存在於 `if` 與對應的 `else` 區塊內。這種寫法適合處理 map 查找、型別轉換、函式呼叫錯誤等短生命週期資料。

```go
if err := saveProfile(profile); err != nil {
	return err
}
```

這裡的 `err` 只用來判斷 `saveProfile` 是否失敗，離開 `if` 後就不再需要。短宣告可以降低變數留在外層範圍造成的干擾。

## 提前返回讓主流程靠左

Go 常用提前返回處理失敗或特殊情況。核心原則是先處理不能繼續的狀態，讓正常流程留在較少縮排的位置。

```go
func normalizeEmail(input string) (string, error) {
	input = strings.TrimSpace(input)
	if input == "" {
		return "", fmt.Errorf("email is required")
	}

	if !strings.Contains(input, "@") {
		return "", fmt.Errorf("invalid email")
	}

	return strings.ToLower(input), nil
}
```

這段程式先排除空字串與格式錯誤，最後才回傳正常結果。讀者可以依序看到「不能接受什麼」以及「通過檢查後會得到什麼」。

提前返回不是要求每個條件都拆開。當兩個條件代表同一個規則時，可以合併成一個判斷；當條件代表不同失敗原因時，拆開通常比較清楚。

## `for` 是唯一迴圈語法

Go 的迴圈只有 `for`。它可以表達傳統計數迴圈、條件迴圈、無限迴圈與 range 迴圈。

```go
for i := 0; i < 3; i++ {
	fmt.Println(i)
}
```

這是傳統的三段式迴圈：初始化、條件、迭代後處理。它適合需要 index、固定次數或精準控制遞增方式的場景。

```go
remaining := 3
for remaining > 0 {
	fmt.Println(remaining)
	remaining--
}
```

省略初始化與後處理後，`for` 就是其他語言常見的 while 迴圈。Go 不另外提供 `while`，因為 `for 條件` 已經能表達同一件事。

```go
for {
	fmt.Println("polling")
	break
}
```

沒有條件的 `for` 是無限迴圈，通常會搭配 `break`、`return`、`context` 或 channel 退出。無限迴圈要讓退出條件清楚可見，否則很容易讓讀者無法判斷生命週期。

## `range` 用來走訪集合

`range` 的核心用途是逐一走訪陣列、slice、map、字串與 channel。它會依資料型別產生不同的索引或值。

```go
names := []string{"alice", "bob"}

for i, name := range names {
	fmt.Println(i, name)
}
```

走訪 slice 時，第一個值是 index，第二個值是元素副本。若不需要 index，可以用 `_` 忽略。

```go
for _, name := range names {
	fmt.Println(name)
}
```

走訪 map 時，順序沒有保證。這是語言刻意設計的結果，避免程式誤以為 map 有穩定順序。

```go
scores := map[string]int{
	"alice": 90,
	"bob":   80,
}

for name, score := range scores {
	fmt.Println(name, score)
}
```

如果輸出順序重要，應該先取出 key、排序，再依序讀取 map。

## `break` 與 `continue` 控制迴圈節奏

`break` 的核心作用是結束目前迴圈，`continue` 的核心作用是跳過本次迭代並進入下一輪。它們應該用來表達清楚的流程轉折，而不是補救過度複雜的迴圈。

```go
for _, line := range lines {
	if line == "" {
		continue
	}

	if line == "STOP" {
		break
	}

	fmt.Println(line)
}
```

這段程式忽略空行，遇到 `STOP` 停止，其他行則輸出。條件都放在處理邏輯前方，讀者可以先理解哪些資料不進入主流程。

當迴圈內的 `break`、`continue`、巢狀條件太多時，通常代表應該把部分邏輯抽成函式，讓每個函式只負責一層判斷。

## `switch` 表達多分支判斷

`switch` 的核心責任是把同一個概念的多種可能集中呈現。Go 的 `switch` 預設不會自動落入下一個 `case`，所以大多數情況不需要寫 `break`。

```go
switch method {
case "GET":
	fmt.Println("read")
case "POST":
	fmt.Println("create")
case "DELETE":
	fmt.Println("delete")
default:
	fmt.Println("unsupported")
}
```

每個 `case` 預設只執行自己的區塊。若真的需要落入下一個 case，Go 提供 `fallthrough`，但日常程式很少需要它。

`switch` 也可以不帶目標值，用來取代一長串 `if else`。

```go
switch {
case score >= 90:
	fmt.Println("A")
case score >= 80:
	fmt.Println("B")
case score >= 70:
	fmt.Println("C")
default:
	fmt.Println("D")
}
```

這種寫法適合條件都在描述同一個分類規則時使用。若每個條件都在處理不同概念，拆成多個 `if` 或不同函式通常更清楚。

## 小結

Go 的控制流程刻意維持少量語法：`if` 處理條件，`for` 處理所有迴圈，`switch` 處理多分支。這些語法的共同精神是讓流程清楚可讀，而不是提供大量縮寫形式。

下一章會回到 package 與檔案組織，說明 Go 如何用 package 建立程式邊界。
