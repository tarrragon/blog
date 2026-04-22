---
title: "1.5 從單檔到多檔案"
date: 2026-04-22
description: "理解 Go 程式如何從 main.go 長成多檔案與多 package"
weight: 5
---

Go 程式變大的第一個拆分單位通常是檔案，不是架構。初學者常從一個 `main.go` 開始，等到入口程式太長，再把相關函式拆到同一個 package 的其他檔案；只有當某組概念需要形成獨立 API 邊界時，才搬到新的資料夾成為新的 package。

## 本章目標

學完本章後，你將能夠：

1. 判斷何時保留單一 `main.go`
2. 理解同 package 多檔案如何互相呼叫
3. 分辨「拆檔案」和「拆 package」的差異
4. 看懂跨 package 呼叫、exported 名稱與 import path 的關係
5. 避免過早把小程式拆成複雜架構

---

## 【觀察】單檔是合理起點

單一 `main.go` 的核心價值是降低初期理解成本。程式還小的時候，把入口、設定、簡單函式放在同一個檔案，通常比一開始拆成多個資料夾更容易閱讀。

```text
notify/
├── go.mod
└── main.go
```

一個最小 HTTP 服務可以先長這樣：

```go
package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/health", healthHandler)

    if err := http.ListenAndServe(":8080", nil); err != nil {
        panic(err)
    }
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintln(w, "ok")
}
```

這個階段不需要急著建立 `handler`、`service` 或 `domain` 資料夾。讀者一眼能看懂程式如何啟動，比形式上的分層更重要。

## 【判讀】main.go 膨脹時，先拆同 package 多檔案

同 package 多檔案的核心規則是：同一個資料夾、同一個 package 名稱的 Go 檔案會被一起編譯，彼此可以直接呼叫，不需要 import。

當 `main.go` 開始同時包含設定、handler、資料型別與啟動流程，可以先拆成這樣：

```text
notify/
├── go.mod
├── main.go
├── config.go
├── server.go
└── message.go
```

每個檔案仍然使用：

```go
package main
```

因此 `main.go` 可以直接呼叫 `loadConfig()`：

```go
func main() {
    cfg := loadConfig()
    server := newServer(cfg)

    if err := server.ListenAndServe(); err != nil {
        panic(err)
    }
}
```

`config.go` 可以提供這個函式：

```go
package main

type config struct {
    Port string
}

func loadConfig() config {
    return config{Port: ":8080"}
}
```

這不是跨 package 呼叫，而是同 package 內的檔案切分。`loadConfig` 即使用小寫開頭，`main.go` 也可以呼叫，因為它們都屬於 `package main`。

## 【策略】先拆檔案，再拆 package

拆分的核心判斷是：檔案用來降低閱讀負擔，package 用來建立 API 邊界。這兩者成本不同，不應混在一起。

| 拆分方式          | 使用時機                            | 呼叫方式                    | 成本                    |
| ----------------- | ----------------------------------- | --------------------------- | ----------------------- |
| 同 package 多檔案 | 檔案太長、概念需要分段              | 直接呼叫                    | 成本低，沒有新 API 邊界 |
| 新 package        | 概念可獨立、需要被其他 package 使用 | import 後呼叫 exported 名稱 | 成本較高，需要設計 API  |

例如 `message.go` 只是放一些內部型別時，可以留在 `package main`：

```go
package main

type message struct {
    Title string
    Body  string
}
```

如果 notification 概念開始有自己的建構規則、驗證規則與測試需求，就可以搬成獨立 package：

```text
notify/
├── go.mod
├── main.go
└── notification/
    ├── notification.go
    └── validate.go
```

此時 `notification` package 要明確決定哪些名稱是對外 API。

## 【執行】跨 package 呼叫需要 import 與 exported 名稱

跨 package 呼叫的核心規則是：其他 package 只能使用大寫開頭的 exported 名稱，並且必須透過 import path 引入。

假設 module path 是：

```go
module example.com/notify
```

`notification/notification.go` 可以這樣寫：

```go
package notification

import "strings"

type Notification struct {
    Title string
    Body  string
}

func New(title, body string) Notification {
    return Notification{
        Title: strings.TrimSpace(title),
        Body:  strings.TrimSpace(body),
    }
}

func isEmpty(n Notification) bool {
    return n.Title == "" && n.Body == ""
}
```

`main.go` 要使用這個 package，必須 import：

```go
package main

import (
    "fmt"

    "example.com/notify/notification"
)

func main() {
    n := notification.New("Deploy finished", "Version 1.2.0 is live")
    fmt.Println(n.Title)
}
```

`notification.New` 和 `notification.Notification` 可以被外部使用，因為它們是大寫開頭。`isEmpty` 不能被 `main.go` 呼叫，因為它是 package 內部實作細節。

## 【判讀】import cycle 是依賴方向錯了

import cycle 的核心意義是兩個 package 互相依賴，Go 會直接拒絕編譯。這不是 Go 不方便，而是工具鏈強迫你把依賴方向想清楚。

例如這種結構容易出問題：

```text
notify/
├── main.go
├── handler/
│   └── handler.go
└── notification/
    └── notification.go
```

如果 `handler` import `notification`，同時 `notification` 又 import `handler`，就會形成循環依賴。

```text
handler -> notification -> handler
```

修正的核心做法是讓低層概念不要依賴高層協定。`notification` 應該描述通知資料與規則，不應知道 HTTP handler；handler 可以把 HTTP request 轉成 notification command 或 value。

```text
handler -> notification
```

這個方向比「互相知道」更容易測試，也更容易重構。

## 常見拆分路線

Go 服務常見的成長路線是漸進式的。每一步都應該解決當下的閱讀、測試或依賴問題，而不是為了看起來正式。

### 階段一：單一檔案

```text
notify/
├── go.mod
└── main.go
```

適合小工具、實驗程式、剛開始的服務雛形。

### 階段二：同 package 多檔案

```text
notify/
├── go.mod
├── main.go
├── config.go
├── server.go
└── notification.go
```

適合 `main.go` 開始太長，但概念還沒有明確 API 邊界的階段。

### 階段三：多 package

```text
notify/
├── go.mod
├── main.go
├── config/
│   └── config.go
├── notification/
│   ├── notification.go
│   └── validate.go
└── transport/
    └── http.go
```

適合設定、通知規則、HTTP transport 已經能清楚分成不同責任的階段。

### 階段四：服務邊界更清楚

```text
notify/
├── go.mod
├── cmd/
│   └── notify-server/
│       └── main.go
└── internal/
    ├── notification/
    ├── transport/
    └── storage/
```

適合服務已經有明確部署入口、內部 package 不想被外部 module 引用的階段。這不是入門預設，而是程式長大後的選擇。

## 常見錯誤

### 錯誤一：把檔案當成 class

Go 的檔案不是 class。把每個 struct 都拆成一個檔案，通常只會增加跳轉成本，不會讓設計更清楚。

### 錯誤二：太早建立多層資料夾

程式還小時就建立 `domain`、`application`、`infrastructure`，會讓讀者先學資料夾，再學行為本身。Go 更適合先讓程式跑起來，再根據壓力拆邊界。

### 錯誤三：為了重用而 exported 太多名稱

exported 名稱就是 package 對外承諾。還不確定會被外部使用的型別與函式，先保持 unexported，等 API 真的穩定再開放。

## 小結

Go 程式的成長路線通常是單檔、同 package 多檔案、多 package，最後才是更明確的服務邊界。拆分的目的不是讓目錄看起來正式，而是降低閱讀成本、控制 API、整理依賴方向，並讓測試更容易寫。
