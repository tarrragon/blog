---
title: "3.4 encoding/json：資料交換"
date: 2026-04-22
description: "用 encoding/json 在 struct、檔案與 HTTP 之間交換資料"
weight: 4
---

# encoding/json：資料交換

`encoding/json` 是 Go 標準庫中負責 JSON 編碼與解碼的 package。它的核心用途是把 Go struct 轉成 JSON，或把 JSON 轉回 Go struct，讓程式能和設定檔、HTTP API、message queue 等外部格式交換資料。

## 本章目標

學完本章後，你將能夠：

1. 用 `json.Unmarshal` 解析 JSON bytes
2. 用 `json.Marshal` 輸出 JSON bytes
3. 用 `json.NewDecoder` 解析 stream
4. 用 `json.NewEncoder` 寫出 response
5. 正確處理 JSON 解析錯誤

---

## 【觀察】JSON 解碼是外部資料進入 Go 型別的邊界

JSON 解碼的核心規則是：外部資料必須先進入明確的 Go struct，後續程式才應依賴型別欄位。以下範例把設定檔 JSON 解析成 `Config`：

```go
type Config struct {
    AppName string `json:"appName"`
    Port    int    `json:"port"`
    Debug   bool   `json:"debug"`
}

func LoadConfig(data []byte) (Config, error) {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return Config{}, fmt.Errorf("parse config JSON: %w", err)
    }
    return cfg, nil
}
```

`json.Unmarshal` 需要接收 pointer，因為它要把解析結果寫入 `cfg`。若傳入 `cfg` 而不是 `&cfg`，解碼結果無法寫回呼叫端變數。

## 【判讀】JSON tag 是解碼與編碼的欄位對照表

JSON tag 的核心規則是：Go 欄位名稱和 JSON 欄位名稱可以不同，但必須在 struct tag 中明確對應。

```go
type User struct {
    ID        string `json:"id"`
    Name      string `json:"name"`
    CreatedAt string `json:"createdAt"`
}
```

這個 struct 對應的 JSON 是：

```json
{
  "id": "u_1",
  "name": "Alice",
  "createdAt": "2026-04-22T10:00:00Z"
}
```

Go 欄位必須 exported，`encoding/json` 才能讀寫。小寫開頭欄位是 unexported，JSON package 不會填入。

## 【策略】bytes 用 Marshal/Unmarshal，stream 用 Encoder/Decoder

JSON API 選擇的核心規則是：資料已經在記憶體中用 `Marshal` / `Unmarshal`，資料來自 stream 用 `Encoder` / `Decoder`。

| 情境 | 適合 API |
|------|----------|
| `[]byte` 解析成 struct | `json.Unmarshal` |
| struct 轉成 `[]byte` | `json.Marshal` |
| 從 `io.Reader` 讀 JSON | `json.NewDecoder` |
| 寫 JSON 到 `io.Writer` | `json.NewEncoder` |

HTTP request body 是 stream，適合用 decoder：

```go
func decodeCreateUser(r *http.Request) (CreateUserRequest, error) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        return CreateUserRequest{}, fmt.Errorf("decode request JSON: %w", err)
    }
    return req, nil
}
```

HTTP response writer 也是 stream，適合用 encoder：

```go
func writeJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(data)
}
```

## 【執行】在 HTTP handler 中處理 JSON

HTTP JSON handler 的核心規則是：解析錯誤屬於 client input 問題，通常回 400；內部處理錯誤屬於 server 問題，通常回 500。

```go
type CreateUserRequest struct {
    Name string `json:"name"`
}

type CreateUserResponse struct {
    ID   string `json:"id"`
    Name string `json:"name"`
}

func handleCreateUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeJSON(w, http.StatusBadRequest, map[string]string{
            "error": "invalid JSON",
        })
        return
    }

    if req.Name == "" {
        writeJSON(w, http.StatusBadRequest, map[string]string{
            "error": "name is required",
        })
        return
    }

    resp := CreateUserResponse{
        ID:   "u_1",
        Name: req.Name,
    }
    writeJSON(w, http.StatusCreated, resp)
}
```

這個 handler 把 JSON 邊界處理清楚：先解碼，再驗證，再執行核心邏輯，最後輸出 JSON。

## 常見錯誤

### 忘記傳 pointer 給 Unmarshal

`json.Unmarshal` 必須把結果寫進目標值，所以目標要傳 pointer：

```go
var cfg Config
err := json.Unmarshal(data, &cfg)
```

### 忽略 Decode 錯誤

JSON 來自外部輸入，解析錯誤是正常情境。忽略錯誤會讓後續程式拿到零值 struct，造成更難追蹤的 bug。

### 把內部錯誤直接回給外部

對外 response 應該穩定且安全；內部錯誤細節留在 log 或 error chain 裡，不直接暴露給使用者。

## 小結

`encoding/json` 是 Go struct 和外部 JSON 格式之間的轉換層。bytes 用 `Marshal` / `Unmarshal`，stream 用 `Encoder` / `Decoder`；所有外部 JSON 都應先進入明確 struct，再進入後續業務邏輯。
