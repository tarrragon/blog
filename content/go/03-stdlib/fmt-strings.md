---
title: "3.1 fmt、strings 與基本文字處理"
date: 2026-04-22
description: "處理格式化輸出、字串清理、切割與組合"
weight: 1
---

文字處理的核心規則是：格式化輸出交給 `fmt`，字串查找、裁切、替換與組合交給 `strings`。本章將用 CLI 輸出、設定值清理與簡單 parser 建立標準庫文字處理基礎。

## `fmt` 負責格式化

`fmt` 的核心責任是把資料轉成可閱讀的文字。它可以輸出到標準輸出，也可以把格式化結果組成字串，常用於 CLI 訊息、錯誤訊息與簡單除錯。

```go
name := "worker"
count := 3

fmt.Printf("%s handled %d jobs\n", name, count)
message := fmt.Sprintf("%s handled %d jobs", name, count)

fmt.Println(message)
```

`Printf` 會直接輸出，`Sprintf` 會回傳字串。這個差異很重要：函式內部如果只是要建立訊息，通常應該用 `Sprintf` 回傳字串，而不是直接印出。

## 格式動詞描述輸出形狀

格式動詞的核心作用是告訴 `fmt` 如何呈現資料。常見動詞包括 `%s` 表示字串，`%d` 表示十進位整數，`%v` 表示一般值，`%+v` 顯示 struct 欄位名稱，`%#v` 顯示更接近 Go 語法的表示。

```go
type User struct {
    ID   int
    Name string
}

user := User{ID: 7, Name: "alice"}

fmt.Printf("%v\n", user)  // {7 alice}
fmt.Printf("%+v\n", user) // {ID:7 Name:alice}
fmt.Printf("%#v\n", user) // main.User{ID:7, Name:"alice"}
```

`%v` 適合一般輸出，`%+v` 適合快速檢查 struct 欄位，`%#v` 適合除錯或理解實際型別。正式 [log](/backend/knowledge-cards/log/) 通常應該使用結構化 log，而不是把所有資料塞進格式化字串。

## 錯誤訊息要包含可行動資訊

錯誤訊息的核心原則是描述失敗的操作與關鍵資料。`fmt.Errorf` 可以建立帶格式的 error，也可以用 `%w` 包裝原始錯誤，保留錯誤鏈。

```go
func loadUser(id string) error {
    if id == "" {
        return fmt.Errorf("load user: id is required")
    }

    return nil
}
```

錯誤訊息不是給機器看的代碼，而是給工程師定位問題的線索。像 `"failed"` 這類訊息太籠統，讀者無法知道是哪個操作失敗。

```go
if err := saveConfig(path, config); err != nil {
    return fmt.Errorf("save config %q: %w", path, err)
}
```

這裡的訊息包含操作 `save config`、目標 `path` 與原始錯誤。呼叫端可以顯示完整錯誤，也可以用 `errors.Is` 或 `errors.As` 檢查被包裝的錯誤。

## `strings` 負責字串操作

`strings` 的核心責任是提供不需要正規表示式的常見字串操作。裁切空白、檢查前後綴、切割、替換、大小寫轉換，都應該先考慮 `strings`。

```go
raw := "  api,worker,admin  "
raw = strings.TrimSpace(raw)

parts := strings.Split(raw, ",")
for _, part := range parts {
    fmt.Println(strings.TrimSpace(part))
}
```

這段程式先移除整體前後空白，再用逗號切割，最後清理每個片段。這種處理很常見於環境變數、設定檔與簡單文字輸入。

## 查找與判斷應該直接表達意圖

字串判斷的核心原則是使用最貼近意圖的函式。檢查包含關係用 `Contains`，檢查開頭用 `HasPrefix`，檢查結尾用 `HasSuffix`。

```go
path := "/api/users"

if strings.HasPrefix(path, "/api/") {
    fmt.Println("api route")
}

if strings.Contains(path, "users") {
    fmt.Println("user resource")
}
```

用 `Index` 判斷是否存在也是可行的，但意圖比較間接。

```go
if strings.Index(path, "/api/") == 0 {
    fmt.Println("api route")
}
```

這段程式需要讀者理解 `Index` 回傳 `0` 表示出現在開頭；`HasPrefix` 則直接說出規則。入門階段應優先選擇語意清楚的 API。

## 組合字串要看資料量

組合少量字串時，`+` 與 `fmt.Sprintf` 通常足夠；大量或迴圈內組合字串時，`strings.Builder` 更適合。核心判斷是：資料量小時重視可讀性，資料量大時避免反覆建立中間字串。

```go
name := "alice"
message := "hello, " + name
fmt.Println(message)
```

少量字串串接很直覺，不需要過度設計。當你在迴圈中累積文字，`strings.Builder` 能更明確地表達「正在逐步建構一段文字」。

```go
var builder strings.Builder

for _, name := range []string{"alice", "bob", "carol"} {
    builder.WriteString("- ")
    builder.WriteString(name)
    builder.WriteString("\n")
}

fmt.Print(builder.String())
```

`strings.Builder` 不是每次組字串都必須使用。若資料量小、流程簡單，普通串接往往更好讀。

## 簡單 parser 可以先用標準庫

簡單文字解析的核心策略是先用清楚的步驟切割資料，再逐步驗證格式。只有當格式本身複雜到難以維護時，才需要引入 parser 或正規表示式。

```go
func parsePair(input string) (string, string, error) {
    parts := strings.SplitN(input, "=", 2)
    if len(parts) != 2 {
        return "", "", fmt.Errorf("parse pair %q: missing =", input)
    }

    key := strings.TrimSpace(parts[0])
    value := strings.TrimSpace(parts[1])
    if key == "" {
        return "", "", fmt.Errorf("parse pair %q: empty key", input)
    }

    return key, value, nil
}
```

`SplitN` 限制最多切成兩段，避免 value 裡再次出現 `=` 時被過度切割。這個例子也先處理格式錯誤，再回傳正常結果，讓流程保持清楚。

## 小結

`fmt` 解決資料如何呈現成文字，`strings` 解決文字如何被查找、裁切、切割與組合。入門階段應先熟悉這兩個 package，因為它們會出現在 CLI、設定處理、錯誤訊息、HTTP handler 與測試輸出中。

下一章會進入 `time`，說明時間點、時間長度與 [timeout](/backend/knowledge-cards/timeout/) 的標準表示方式。
