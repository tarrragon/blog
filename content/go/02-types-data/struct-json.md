---
title: "2.1 struct 與 JSON tag"
date: 2026-04-22
description: "理解 Go struct 如何表達資料形狀，並透過 JSON tag 對應外部格式"
weight: 1
---

Go 的 struct 用來描述資料形狀：有哪些欄位、欄位是什麼型別、哪些資料應該放在一起。當資料需要存成 JSON 或透過 API 傳輸時，JSON tag 會把 Go 的欄位命名對應到外部格式。

## 本章目標

學完本章後，你將能夠：

1. 定義可序列化成 JSON 的 struct
2. 理解 `omitempty` 的 API 語義
3. 分辨內部欄位命名與外部 JSON 命名
4. 看懂設定檔、API request 與事件資料模型

---

## 【觀察】struct 用欄位集合定義資料形狀

struct 的核心規則是：每個欄位都用名稱和型別描述一部分資料。以下範例用 struct 定義一份應用設定：

```go
type Config struct {
    AppName string `json:"appName"`
    Port    int    `json:"port"`
    Debug   bool   `json:"debug"`
}
```

這段程式同時回答兩個問題：Go 程式內用哪些欄位處理設定，以及 JSON 檔案裡的欄位名稱是什麼。

## 【判讀】JSON tag 是外部資料格式 contract

JSON tag 的核心規則是：Go 欄位名稱服務程式碼可見性，JSON 欄位名稱服務外部資料格式。`AppName` 對應 `appName` 是兩個命名慣例的交界：

| 層次           | 命名      | 原因                       |
| -------------- | --------- | -------------------------- |
| Go struct 欄位 | `AppName` | exported 欄位必須大寫開頭  |
| JSON payload   | `appName` | JSON 與 API 常用 camelCase |

`omitempty` 宣告「這個欄位在某些資料情境中不是必要資料」。它是可選欄位的語義標記；欄位為零值時，JSON 序列化會跳過輸出。

## 【策略】先用資料語意決定欄位是否必要

設計 JSON 資料時，先分辨欄位角色：

| 欄位角色              | tag 策略               |
| --------------------- | ---------------------- |
| 每筆資料都需要        | 不加 `omitempty`       |
| 只有部分情境需要      | 加 `omitempty`         |
| 內部使用，不輸出 JSON | 使用 `json:"-"`        |
| 外部名稱需要穩定      | 明確寫 tag，不依賴預設 |

這樣資料 contract 會比「把 struct 全部輸出」更清楚。

## 【執行】事件資料建模

事件資料模型的核心規則是：事件本身必備欄位不使用 `omitempty`，事件內容可依類型使用可選欄位。`UserEvent` 表示一筆使用者行為事件，可以來自檔案、HTTP API 或 message [queue](/backend/knowledge-cards/queue/)：

```go
type UserEvent struct {
    UserID    string    `json:"userId"`
    Type      string    `json:"type"`
    Timestamp time.Time `json:"timestamp"`
    Source    string    `json:"source"`
    Payload   Payload   `json:"payload"`
}
```

這個 struct 的欄位都沒有 `omitempty`，表示它是事件流中的完整資料單位。相比之下，`Payload` 可以依事件類型使用 `omitempty`，因為不同事件只會填入部分欄位。

## 巢狀 struct

巢狀 struct 的核心規則是：資料本身有層次時，Go 型別也應保留同樣層次。以下設定把 server 相關欄位集中到 `ServerConfig`：

```go
type ServerConfig struct {
    Host string `json:"host"`
    Port int    `json:"port"`
}

type Config struct {
    AppName string       `json:"appName"`
    Debug   bool         `json:"debug"`
    Server  ServerConfig `json:"server"`
}
```

對應 JSON：

```json
{
  "appName": "notify",
  "debug": true,
  "server": {
    "host": "localhost",
    "port": 8080
  }
}
```

這樣的設計讓資料層次在 Go 程式中也看得見。

## 小結

struct 是 Go 程式的資料骨架，JSON tag 是對外 contract。讀 model 時應同時看欄位型別與 tag，因為 tag 會揭露 API 或檔案格式的必要性、可選性與命名邊界。
