---
title: "3.3 os/io：檔案與輸入輸出"
date: 2026-04-22
description: "讀寫檔案，理解 io.Reader 與 io.Writer"
weight: 3
---

Go I/O 的核心規則是：資料來源抽象成 `io.Reader`，資料目的地抽象成 `io.Writer`。本章將從檔案讀寫開始，建立 `os`、`io` 與 streaming API 的基本模型。

## 檔案操作從 `os` 開始

`os` package 的核心責任是處理作業系統層級的資源，例如檔案、目錄、環境變數與 process 相關資訊。入門階段最常用的是讀檔、寫檔與建立檔案。

```go
data, err := os.ReadFile("config.json")
if err != nil {
    return err
}

fmt.Println(string(data))
```

`os.ReadFile` 會一次把整個檔案讀進記憶體，適合設定檔、小型文字檔與測試資料。若檔案可能很大，就應改用 streaming 方式逐步讀取。

寫入小檔案也可以使用 `os.WriteFile`。

```go
data := []byte("name=demo\n")

if err := os.WriteFile("app.env", data, 0644); err != nil {
    return err
}
```

最後的 `0644` 是檔案權限。它表示檔案擁有者可讀寫，其他人可讀。權限不是 Go 特有語法，而是 Unix 檔案權限慣例。

## 開啟檔案後要關閉

檔案是作業系統資源，開啟後應在不使用時關閉。Go 常用 `defer file.Close()` 放在成功開啟檔案後，確保函式結束時釋放資源。

```go
file, err := os.Open("data.txt")
if err != nil {
    return err
}
defer file.Close()

data, err := io.ReadAll(file)
if err != nil {
    return err
}

fmt.Println(string(data))
```

`defer` 應該放在確認 `err == nil` 之後，因為開啟失敗時 `file` 可能是 `nil`。這是 Go I/O 程式很重要的基本順序：先檢查錯誤，再使用資源。

## `io.Reader` 表示可讀來源

`io.Reader` 的核心意義是「可以讀出 bytes 的來源」。檔案、網路連線、HTTP request body、字串 reader 都可以是 reader。

```go
func countBytes(r io.Reader) (int, error) {
    data, err := io.ReadAll(r)
    if err != nil {
        return 0, err
    }

    return len(data), nil
}
```

這個函式不關心資料來自檔案、記憶體或網路，只要求呼叫端提供一個 `io.Reader`。這就是 Go 介面設計的典型風格：用小介面描述能力，而不是描述具體來源。

```go
count, err := countBytes(strings.NewReader("hello"))
if err != nil {
    return err
}

fmt.Println(count)
```

`strings.NewReader` 可以把字串包成 reader，常用於測試與範例。因為函式依賴 `io.Reader`，測試時不需要真的建立檔案。

## `io.Writer` 表示可寫目的地

`io.Writer` 的核心意義是「可以接收 bytes 的目的地」。檔案、網路連線、HTTP response、記憶體 [buffer](../../backend/knowledge-cards/buffer) 都可以是 writer。

```go
func writeGreeting(w io.Writer, name string) error {
    _, err := fmt.Fprintf(w, "hello, %s\n", name)
    return err
}
```

這個函式不決定輸出位置，只決定輸出內容。呼叫端可以把內容寫到標準輸出、檔案或 buffer。

```go
var buffer bytes.Buffer

if err := writeGreeting(&buffer, "alice"); err != nil {
    return err
}

fmt.Println(buffer.String())
```

`bytes.Buffer` 同時實作 reader 與 writer，適合用來累積輸出或測試寫入結果。

## streaming 適合大資料或長連線

streaming 的核心策略是分段處理資料，而不是一次把全部資料載入記憶體。當檔案很大、資料來自網路，或你只需要逐步轉送資料時，streaming 會比 `ReadAll` 更適合。

```go
func copyFile(dstPath string, srcPath string) error {
    src, err := os.Open(srcPath)
    if err != nil {
        return err
    }
    defer src.Close()

    dst, err := os.Create(dstPath)
    if err != nil {
        return err
    }
    defer dst.Close()

    _, err = io.Copy(dst, src)
    return err
}
```

`io.Copy` 從 reader 讀資料並寫到 writer。這段程式沒有手動配置完整檔案大小的 byte slice，因此可以處理比記憶體更大的檔案。

## `bufio.Scanner` 適合逐行讀取

逐行處理文字的核心工具是 `bufio.Scanner`。它會把 reader 切成一個個 token，預設 token 是一行文字。

```go
func printLines(r io.Reader) error {
    scanner := bufio.NewScanner(r)
    for scanner.Scan() {
        fmt.Println(scanner.Text())
    }

    return scanner.Err()
}
```

`scanner.Scan()` 每次成功讀到一行就回傳 `true`，讀完或遇到錯誤時回傳 `false`。迴圈結束後要檢查 `scanner.Err()`，因為讀取錯誤不會在迴圈內直接回傳。

`Scanner` 適合一般文字行，但它有預設 token 大小限制。若要處理非常長的行或大型二進位資料，應改用 `bufio.Reader` 或其他 streaming API。

## 小結

Go 的 I/O 設計以 `io.Reader` 與 `io.Writer` 為中心。小檔案可以用 `os.ReadFile` 與 `os.WriteFile` 快速處理；需要控制資源生命週期時使用 `os.Open`、`defer Close`；資料量大或來源不固定時，改用 reader/writer 與 streaming。

下一章會進入 JSON，說明 Go 如何把 struct 與外部資料格式互相轉換。
