---
title: "5.3 table-driven test"
date: 2026-04-22
description: "用表格整理多組輸入、預期輸出與錯誤情境"
weight: 3
---

table-driven test 的核心規則是：同一個行為的多組案例放進表格，測試流程只寫一次。本章將說明如何設計案例欄位、命名子測試，並避免把太多不同行為塞進同一張表。

## table-driven test 解決重複案例

table-driven test 的核心目標是把「案例資料」和「測試流程」分開。當同一個函式需要測多組輸入與預期結果時，表格能讓案例集中呈現，測試流程只保留一次。

```go
func NormalizeName(input string) string {
    input = strings.TrimSpace(input)
    return strings.ToLower(input)
}
```

這個函式有多個值得驗證的案例：一般字串、前後空白、已經是小寫、空字串。若每個案例都寫一個完整測試，程式會很快重複。

```go
func TestNormalizeName(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  string
    }{
        {name: "lowercase", input: "alice", want: "alice"},
        {name: "trim spaces", input: "  Alice  ", want: "alice"},
        {name: "empty", input: "", want: ""},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := NormalizeName(tt.input)
            if got != tt.want {
                t.Fatalf("NormalizeName(%q) = %q, want %q", tt.input, got, tt.want)
            }
        })
    }
}
```

表格中的每一列是一個案例，迴圈中的程式是共同驗證流程。新增案例時，只要新增一列，不必複製整個測試函式。

## 案例欄位要對應行為

測試表格欄位的核心原則是只放描述案例所需的資料。常見欄位包括 `name`、輸入值、預期輸出與是否預期錯誤。

```go
tests := []struct {
    name    string
    input   string
    want    int
    wantErr bool
}{
    {name: "valid", input: "8080", want: 8080},
    {name: "not number", input: "abc", wantErr: true},
    {name: "zero", input: "0", wantErr: true},
}
```

`wantErr` 表示這個案例預期出錯。它比把錯誤訊息塞進 `want` 更清楚，因為成功結果與錯誤結果是兩種不同觀察。

```go
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got, err := ParsePort(tt.input)
        if tt.wantErr {
            if err == nil {
                t.Fatalf("ParsePort(%q) error = nil, want error", tt.input)
            }
            return
        }

        if err != nil {
            t.Fatalf("ParsePort(%q) error = %v", tt.input, err)
        }

        if got != tt.want {
            t.Fatalf("ParsePort(%q) = %d, want %d", tt.input, got, tt.want)
        }
    })
}
```

錯誤案例先處理並 `return`，成功案例再繼續檢查輸出。這讓測試流程和函式行為一樣清楚：失敗時不應再比較正常結果。

## `t.Run` 讓案例有名字

`t.Run` 的核心作用是建立子測試，讓每個案例在測試輸出中有獨立名稱。當某個案例失敗時，工程師可以直接看到是哪一列資料出問題。

```go
t.Run(tt.name, func(t *testing.T) {
    // case assertion
})
```

案例名稱應該描述情境，而不是描述編號。`"empty input"`、`"negative port"`、`"trim spaces"` 比 `"case 1"` 更有定位價值。

```go
tests := []struct {
    name  string
    input string
    want  string
}{
    {name: "trim spaces", input: "  Alice  ", want: "alice"},
    {name: "preserve hyphen", input: "Mary-Jane", want: "mary-jane"},
}
```

當測試失敗時，名稱會出現在 `go test` 輸出中。好的案例名稱能讓讀者先理解失敗情境，再去看 got/want 差異。

## 表格應集中在單一行為

table-driven test 的邊界是「同一個測試流程是否能自然描述所有案例」。如果某些案例需要完全不同的準備、執行或驗證方式，通常應該拆成不同測試。

```go
func TestParsePort(t *testing.T) {
    // 測 ParsePort 的輸入輸出規則
}

func TestLoadConfig(t *testing.T) {
    // 測 LoadConfig 的檔案讀取與解析流程
}
```

把不同行為硬塞進同一張表，會讓欄位越來越多，最後出現大量只在少數案例使用的欄位。這種表格看起來少了重複，實際上讓讀者更難理解每個案例。

好的表格應該短而集中。若你需要在測試迴圈裡寫很多 `if tt.someMode`，這通常是拆分測試的訊號。

## 比較複雜資料時使用合適工具

比較結果的核心原則是選擇能清楚表達差異的方式。基本型別可以直接用 `!=`，slice、map、struct 則常用 `reflect.DeepEqual` 或專門的比較工具。

```go
func SplitCSV(input string) []string {
    if input == "" {
        return nil
    }

    parts := strings.Split(input, ",")
    for i := range parts {
        parts[i] = strings.TrimSpace(parts[i])
    }

    return parts
}
```

測試 slice 時，不能直接用 `got != want`。

```go
func TestSplitCSV(t *testing.T) {
    tests := []struct {
        name  string
        input string
        want  []string
    }{
        {name: "empty", input: "", want: nil},
        {name: "two values", input: "a, b", want: []string{"a", "b"}},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := SplitCSV(tt.input)
            if !reflect.DeepEqual(got, tt.want) {
                t.Fatalf("SplitCSV(%q) = %#v, want %#v", tt.input, got, tt.want)
            }
        })
    }
}
```

`reflect.DeepEqual` 適合入門與標準庫範例。大型專案可能使用第三方比較工具產生更好的 diff，但核心原則不變：失敗訊息要讓差異容易看懂。

## 小結

table-driven test 把多個案例整理成資料表，讓測試流程保持一致。它適合同一個行為的多組輸入輸出，不適合把不同功能硬塞在一起。案例名稱、欄位設計與失敗訊息決定了這種測試是否真的好讀。

下一章會把測試方法套到 HTTP handler，說明如何不用啟動真實 server 也能驗證請求與回應。
