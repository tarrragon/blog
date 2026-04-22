---
title: "1.4 package、檔案與可見性"
date: 2026-04-22
description: "看懂 package main、檔案切分與大小寫可見性"
weight: 4
---

# package、檔案與可見性

Go 用 package 組織程式碼。package 不只是資料夾名稱，而是 API 邊界：哪些名稱能被其他 package 使用，哪些名稱只在內部可見，都由 package 與命名共同決定。

## 本章目標

學完本章後，你將能夠：

1. 理解 `package main` 和一般 package 的差異
2. 看懂同一個 package 如何拆成多個檔案
3. 用大小寫判斷 exported 與 unexported 名稱
4. 設計不暴露過多細節的 package API

---

## 【觀察】每個 Go 檔案都從 package 開始

package 宣告的核心規則是：每個 Go 檔案都必須先宣告自己屬於哪個 package。可執行程式使用 `package main`，例如：

```go
package main

import "fmt"

func main() {
    fmt.Println("hello")
}
```

第一行 `package main` 表示這個檔案屬於 `main` package。Go 編譯器會尋找 `main` package 裡的 `main()` 函式，將它編譯成可執行程式。

一般 package 的核心規則是：它不負責啟動程式，而是提供型別、函式或方法給其他 package 使用。可被其他程式引用的工具 package 通常會使用自己的 package 名稱：

```go
package config

type Config struct {
    Port int
}
```

這個 package 不會自己啟動程式，而是提供型別、函式或方法給其他 package 使用。

## 【判讀】package 是一組共同編譯的檔案

package 的編譯單位是一組同 package 檔案。同一個資料夾中的 Go 檔案通常必須宣告同一個 package；這些檔案會被一起編譯，也可以直接互相使用彼此的 unexported 名稱。

例如：

```text
config/
├── config.go
├── defaults.go
└── validate.go
```

三個檔案都可以是：

```go
package config
```

這表示 `config.go` 裡的函式可以直接呼叫 `validate.go` 裡的小工具函式，即使那個工具函式沒有 exported。

## 【策略】用大小寫控制 API 邊界

Go 可見性的核心規則是：大寫開頭 exported，小寫開頭 unexported。Go 沒有 `public`、`private` 關鍵字，而是用命名大小寫決定可見性：

| 名稱 | 可見性 | 意義 |
|------|--------|------|
| `Config` | exported | 其他 package 可使用 |
| `Load` | exported | 其他 package 可呼叫 |
| `defaultPort` | unexported | 只在目前 package 內可用 |
| `validatePath` | unexported | 內部實作細節 |

範例：

```go
package config

type Config struct {
    Port int
}

const defaultPort = 8080

func Load(path string) (Config, error) {
    if path == "" {
        return Config{Port: defaultPort}, nil
    }
    return readConfig(path)
}

func readConfig(path string) (Config, error) {
    // 內部解析邏輯
    return Config{Port: defaultPort}, nil
}
```

其他 package 可以使用 `config.Config` 和 `config.Load`，但不能直接使用 `config.defaultPort` 或 `config.readConfig`。

## 【執行】把檔案切分成認知單位

檔案切分的核心規則是：依照讀者理解程式的方式分組，而不是機械地一個型別一個檔案。Go 不要求「一個型別一個檔案」。

例如設定讀取 package 可以這樣切：

```text
config/
├── config.go       # Config 型別與 Load 入口
├── defaults.go     # 預設值
├── validate.go     # 驗證規則
└── config_test.go  # 測試
```

這樣切分的好處是：

- `config.go` 作為 package 入口，讀者先看這裡
- `defaults.go` 集中預設值，不和解析流程混在一起
- `validate.go` 集中驗證規則，方便測試
- unexported helper 留在 package 內，不污染外部 API

## 常見錯誤

### 錯誤一：把所有東西都 exported

如果你把所有型別、函式、常數都用大寫開頭，其他 package 就會開始依賴你的內部細節。未來你想重構時，會發現很多名稱都不能改。

### 錯誤二：package 名稱太抽象

`utils`、`common`、`helpers` 這類名稱常讓 package 變成雜物間。Go 更偏好用資料或能力命名，例如 `config`、`auth`、`metrics`、`parser`。

### 錯誤三：檔案切太細

過度切分會讓讀者一直跳檔案。Go 的檔案可以稍微長一點，只要同一個檔案仍然圍繞同一組概念。

## 小結

package 是 Go 的基本組織單位，也是 API 邊界。用 exported 名稱提供穩定能力，用 unexported 名稱保留實作彈性，再用檔案切分降低閱讀成本。
