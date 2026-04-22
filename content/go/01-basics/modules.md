---
title: "1.1 Go 專案結構與 module"
date: 2026-04-22
description: "理解 go.mod、module path 與 Go 專案的依賴邊界"
weight: 1
---

Go 專案的邊界通常從 `go.mod` 開始。它定義目前程式碼屬於哪個 module、使用哪個 Go 版本，以及依賴哪些外部套件。

## 本章目標

學完本章後，你將能夠：

1. 看懂 `go.mod` 的三個核心欄位
2. 理解 module path 與 import path 的關係
3. 知道為什麼 Go 指令要在 module 根目錄執行
4. 分辨標準庫與第三方依賴

---

## 【觀察】`go.mod` 定義 module

`go.mod` 的核心用途是宣告目前 module 的身份、Go 版本與外部依賴。一個 Go 專案通常會在 module 根目錄放 `go.mod`：

```go
module example.com/notify-service

go 1.25.1

require (
    github.com/gorilla/websocket v1.5.3
)
```

這份檔案表達三件事：module 名稱、Go 語言版本、外部依賴。

## 【判讀】module 是 Go 編譯與依賴解析的單位

module 的核心規則是：Go 工具鏈以 `go.mod` 所在目錄作為依賴解析與 package 掃描的根。Go 工具鏈需要知道「目前這批程式碼」的根在哪裡；`go.mod` 就是這個根。

當你在 module 根目錄執行：

```bash
go test ./...
```

`./...` 的意思是測試目前 module 底下所有 package。實務上要先找到 `go.mod` 所在目錄，再從那裡執行 Go 指令。

## 【策略】先分辨三種 import

閱讀 import 的核心規則是：先分辨能力來源，再決定去哪裡查。讀 Go 檔案時，先把 import 分成三類：

| 類型            | 例子                                   | 意義                         |
| --------------- | -------------------------------------- | ---------------------------- |
| 標準庫          | `net/http`, `context`, `encoding/json` | Go 內建能力                  |
| 第三方套件      | `github.com/gorilla/websocket`         | 由 `go.mod` 管理             |
| module 內部套件 | `example.com/notify-service/messages`  | 同一個 module 的其他 package |

這個分類會告訴你：問題應該去查標準庫文件、第三方套件文件，還是目前 module 的其他目錄。

## 【執行】用 module 模型閱讀 `main.go`

閱讀入口程式 import 的核心方法是：先把 import 依來源分群，再判斷程式依賴哪些能力。`main.go` 的 import 可以整理成這樣：

```go
import (
    "context"
    "fmt"
    "log/slog"
    "net/http"
    "os"
    "time"

    "example.com/notify-service/messages"
)
```

前面是標準庫，最後一個是專案內部 package。這表示入口程式主要依賴 Go 標準庫，只有日誌訊息常數被拆到內部 `messages` package。

## 小結

`go.mod` 是閱讀 Go 專案的第一個定位點。先找到 module 根，再看 import 分類，可以快速建立「哪些能力來自標準庫、哪些能力來自外部、哪些能力由專案自己定義」的地圖。
