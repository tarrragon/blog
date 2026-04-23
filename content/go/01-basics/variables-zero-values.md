---
title: "1.2 變數、零值與短變數宣告"
date: 2026-04-22
description: "理解 Go 如何宣告、初始化與使用零值"
weight: 2
---

Go 變數宣告的核心規則是：每個變數都有明確型別，未指定初始值時會得到該型別的零值。本章將說明 `var`、`:=`、型別推斷與零值如何讓 Go 程式保持可預測。

## 變數一定有型別

Go 的變數一定屬於某個明確型別。這個型別可以由程式直接寫出，也可以由編譯器根據右側的初始值推斷出來；但推斷完成後，變數的型別就固定了。

```go
var name string = "api"
var port int = 8080

enabled := true
timeout := 30
```

`name` 的型別是 `string`，`port` 的型別是 `int`，`enabled` 與 `timeout` 則由右側初始值推斷型別。Go 允許省略重複資訊，但不允許變數在執行期間任意改變型別。

```go
count := 10
count = 20      // 可以，仍然是 int
// count = "20" // 編譯錯誤：string 不能指派給 int
```

這個規則讓 Go 程式在閱讀時更穩定：看到一個變數後，讀者可以相信它的型別不會在後面突然變成另一種資料。

## 零值讓變數可立即使用

零值是 Go 對「尚未明確指定初始值」的標準答案。每個型別都有自己的零值：數字是 `0`，字串是空字串，布林是 `false`，指標、slice、map、function、interface 與 channel 是 `nil`。

```go
var retryCount int
var title string
var debug bool
var tags []string

fmt.Println(retryCount) // 0
fmt.Println(title)      // ""
fmt.Println(debug)      // false
fmt.Println(tags == nil) // true
```

零值不是錯誤狀態，而是型別的預設狀態。這是 Go 設計中很重要的精神：讓資料結構在最少初始化下仍然有合理行為。

```go
type Counter struct {
    value int
}

func (c *Counter) Add(n int) {
    c.value += n
}

func (c Counter) Value() int {
    return c.value
}

var counter Counter
counter.Add(3)
fmt.Println(counter.Value()) // 3
```

`Counter` 沒有建構函式也能使用，因為 `value` 的零值是 `0`。當型別可以靠零值進入可用狀態時，使用者需要記住的初始化規則就會少很多。

## `var` 適合宣告意圖

`var` 的主要用途是清楚宣告變數的存在、型別或零值意義。當你需要讓讀者知道「這個變數稍後才會被賦值」或「零值本身有意義」時，`var` 比 `:=` 更清楚。

```go
var userID string

if fromHeader != "" {
    userID = fromHeader
} else {
    userID = fromCookie
}
```

這裡的 `userID` 需要經過條件判斷才會得到值，因此先用 `var` 宣告變數，再在不同分支指派。讀者看到 `var userID string`，可以理解這是一個稍後會被填入的字串。

`var` 也適合用在 package 層級，因為 package 層級不能使用 `:=`。

```go
var defaultPort = 8080
var serviceName = "worker"
```

package 層級變數會增加全域狀態，使用前要先確認它是否真的代表整個 package 的共同狀態；如果只是函式內部暫存資料，應該放回函式裡。

## `:=` 適合區域初始化

短變數宣告 `:=` 的主要用途是在函式內同時宣告與初始化變數。當右側初始值已經清楚表達型別時，`:=` 可以讓程式更精簡。

```go
func greeting(name string) string {
    message := "hello, " + name
    return message
}
```

`message` 的型別可以從字串串接結果推斷，所以不需要寫成 `var message string = ...`。這種省略不是模糊化型別，而是移除讀者已經能從右側看懂的重複資訊。

短變數宣告只能用在函式內。以下寫法不能放在 package 層級：

```go
// package 層級不允許：
// port := 8080
```

`:=` 也要求左側至少有一個新變數。這個規則會影響常見的錯誤處理寫法。

```go
data, err := loadFile("config.json")
if err != nil {
    return err
}

config, err := parseConfig(data) // config 是新變數，err 是重新指派
if err != nil {
    return err
}
```

第二次使用 `:=` 是合法的，因為 `config` 是新變數；同時 `err` 會被重新指派。這種寫法在 Go 很常見，但要留意不要在內層區塊意外宣告出新的同名變數。

## 型別推斷不等於放棄型別

型別推斷的核心作用是減少重複，不是讓變數變成動態型別。Go 只在編譯期根據右側表達式推斷型別，推斷後仍然遵守靜態型別規則。

```go
limit := 100       // int
ratio := 0.75      // float64
label := "active"  // string
```

當右側型別不夠明確，或你需要指定更精確的型別時，就應該直接寫出型別。

```go
var timeoutSeconds int64 = 30
var threshold float32 = 0.8
```

這裡如果只寫 `timeoutSeconds := 30`，通常會得到 `int`；如果 API、資料庫欄位或二進位格式需要 `int64`，明確宣告型別會比事後轉型更好讀。

## 指標、slice 與 map 的零值差異

零值的共同規則是「未初始化時有定義好的狀態」，但不同型別的零值可用程度不同。指標的零值是 `nil`，使用前需要確認是否指向有效資料；slice 的零值可以安全讀長度與 append；map 的零值可以讀取但不能寫入。

```go
var names []string
names = append(names, "alice")
fmt.Println(len(names)) // 1

var scores map[string]int
fmt.Println(scores["alice"]) // 0
// scores["alice"] = 10      // panic: assignment to entry in nil map
```

slice 的零值能直接 `append`，所以很多函式可以回傳 `nil` slice 表示沒有資料；呼叫端仍然可以用 `len` 與 `range` 處理。map 要寫入前必須先用 `make` 初始化。

```go
scores := make(map[string]int)
scores["alice"] = 10
```

這個差異是零值判讀的核心陷阱：`nil` slice 通常容易處理，`nil` map 則需要先初始化才能寫入。

## 命名要服務讀者

變數名稱的核心責任是說明資料在當前範圍內的角色。範圍越小，名稱可以越短；範圍越大，名稱就應該越具體。

```go
for i, item := range items {
    fmt.Println(i, item)
}
```

`i` 在很短的迴圈內代表 index，讀者可以立即理解。相反地，跨越多個段落使用的變數應該使用更完整的名稱。

```go
requestTimeout := 5 * time.Second
maxRetryCount := 3
```

Go 程式常使用短名稱，但短名稱不是目標本身。好的名稱應該讓讀者不必回頭搜尋變數來源，就能理解這個值現在代表什麼。

## 小結

Go 變數系統的重點不是語法花樣，而是穩定、明確、可預測。`var` 用來表達型別、零值與稍後賦值的意圖；`:=` 用來在函式內快速宣告已經有初始值的區域變數；零值則讓許多型別不用額外初始化也能進入合理狀態。

下一章會進入控制流程，說明 Go 如何用少量語法表達條件、迴圈與多分支判斷。
